from typing import Type, Callable
import subprocess
import shutil
import zipfile
import json
import time

try:
    import boto3
    from botocore.exceptions import ClientError
    from botocore.client import BaseClient

    _HAS_BOTO3 = True
except ImportError:
    _HAS_BOTO3 = False

try:
    from jsonschema import validate
    import jsonschema.exceptions

    _HAS_JSONSCHEMA = True
except ImportError:
    _HAS_JSONSCHEMA = False


class BedrockMixin:

    def export_to_bedrock(self, agent_app_config: dict = None) -> dict:
        """
        Export tool as Bedrock Agent tool configuration
        """
        if not _HAS_BOTO3:
            error = "boto3 not installed. Install with `pip install boto3`"
            self.logger.error(error)
            raise RuntimeError(error)

        if not _HAS_JSONSCHEMA:
            error = "jasonschema not installed. Install with `pip install jsonschema`"
            self.logger.error(error)
            raise RuntimeError(error)

        valid_agent_app_config_schema = {
            "type": "object",
            "properties": {
                "app_id": {"type": "string"},
                "agent_session_timeout": {"type": "integer"},
                "instruction": {"type": "string"},
                "agent_description": {"type": "string"},
                "target_model": {"type": "string"},
                "python_runtime_version": {"type": "string"},
                "temp_build_root": {"type": "string"},
            },
            "required": [
                "app_id",
                "agent_session_timeout",
                "instruction",
                "agent_description",
                "target_model",
                "python_runtime_version",
                "temp_build_root",
            ],
        }
        try:
            validate(agent_app_config, valid_agent_app_config_schema)
        except jsonschema.exceptions.ValidationError as err:
            error = f"JSON validation failure on input parameters: {err}"
            self.logger.error(error)
            raise RuntimeError(error)

        self.bedrock_agent_client = boto3.client("bedrock-agent")
        self.app_id = agent_app_config["app_id"]
        self.agent_name = agent_app_config["agent_name"]
        self.agent_session_timeout = agent_app_config["agent_session_timeout"]
        self.agent_instruction = agent_app_config["instruction"]
        self.agent_description = agent_app_config["agent_description"]
        self.agent_target_model = agent_app_config["target_model"]
        self.python_runtime_version = agent_app_config["python_runtime_version"]
        self.temp_build_root = agent_app_config["temp_build_root"]
        try:
            self.aws_account_id = (
                boto3.client("sts").get_caller_identity().get("Account")
            )
        except ClientError as e:
            error = f"Error getting AWS account number. Client error: {e}"
            self.logger.error(error)
            raise RuntimeError(error)
        except Exception as e:
            error = f"Error getting AWS account number. Unexpected error: {e}"
            self.logger.error(error)
            raise RuntimeError(error)

        self.openapi_schema_dict = self._generate_openapi_schema()

        self.logger.info(
            f"Starting build of app {self.app_id}...", self.__class__.__name__
        )
        # Creates:
        # the lambda - a .zip archive that contains all the dependencies and the lambda source.
        #              This lambda will have a resource-based policy attached giving it
        #              permission to be invoked by the agent attached.
        # an IAM role - the lambda execution role with managed attached policy
        #               AWSLambdaBasicExecutionRole allowing the lambda to use CloudWatch

        self.logger.info("\tCreating lambda...", self.__class__.__name__)

        self.lambda_arn = self._create_bedrock_lambda()

        # Creates:
        # the Bedrock agent - The bedrock agent itself
        # an IAM role - The agent execution role
        # An IAM policy - a policy to attach to the role allowing the agent to invoke the
        #               - foundational model
        self.logger.info("\tCreating agent...", self.__class__.__name__)
        self.agent_id = self._create_bedrock_agent()

        # Creates:
        # the Bedrock agent action group - Defined with an API schema
        self.logger.info("\tCreating agent action group...", self.__class__.__name__)
        action_group = self._create_agent_action_group()

        # Finally, prepare the agent
        self.logger.info("\tPreparing agent...", self.__class__.__name__)
        try:
            response = self.bedrock_agent_client.prepare_agent(agentId=self.agent_id)
        except ClientError as e:
            error = f"Error preparing agent. Client error: {e}"
            self.logger.error(error)
            raise RuntimeError(error)
        except Exception as e:
            error = f"Error preparing agent. Unexpected error: {e}"
            self.logger.error(error)
            raise RuntimeError(error)

        output_manifest = {
            "lambdaARN": self.lambda_arn,
            "lambdaRoleName": self.lambda_role_name,
            "agentId": self.agent_id,
            "agentRoleName": self.agent_role_name,
            "agentPolicyARN": self.agent_role_policy_arn,
            "agentActionGroup": self.agent_action_group_id,
        }
        self.logger.info("Done!", self.__class__.__name__)
        return output_manifest

    def _generate_openapi_schema(self) -> dict:
        """Convert Gofannon definition to OpenAPI schema"""
        params = self.definition["function"]["parameters"]
        if not "properties" in params:
            params["properties"] = {}
        openapi_schema = {
            "openapi": "3.0.0",
            "info": {"title": self.name, "version": "1.0.0"},
            "paths": {
                f"/{self.name}": {
                    "get": {
                        "description": self.definition["function"]["description"],
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            param: {
                                                "type": props["type"],
                                                "description": props["description"],
                                            }
                                            for param, props in params[
                                                "properties"
                                            ].items()
                                        },
                                        "required": params.get("required", []),
                                    }
                                }
                            }
                        },
                        "responses": {
                            "200": {
                                "description": "Successful operation",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "result": {"type": "string"}
                                            },
                                        }
                                    }
                                },
                            }
                        },
                    }
                }
            },
        }

        return openapi_schema

    def _create_bedrock_lambda(self) -> str:
        """Create Lambda function for Bedrock integration"""

        lambda_client = boto3.client("lambda")
        self.lambda_role_arn = self._create_bedrock_lambda_role()

        # Build the lambda .zip deployment package here. Package consits of:
        # 1. All the Python dependencies, including Gofannon itself
        # 2. The lambda source code.
        # bash code as comments at the bottom of this file.
        # See: https://docs.aws.amazon.com/lambda/latest/dg/python-package.html

        # TODO: verify the path here
        command = f"""../../scripts/build_lambda.sh {self.temp_build_root} {self.python_runtime_version.replace("python","")} {self.app_id}"""
        try:
            process = subprocess.Popen(
                command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()

            if process.returncode == 0:
                self.built_archive = stdout.decode("utf-8").replace("\n", "")
            else:
                raise RuntimeError(stderr.decode("utf-8"))

        except Exception as e:
            error = f"Error creating .zip archive. {e}"
            self.logger.error(error)
            raise RuntimeError(error)

        # TODO: Skeleton code in the function directory or here?
        lambda_src_string = self._get_lambda_source(
            module_name=self.__class__.__module__, class_name=self.__class__.__name__
        )

        try:
            with open(f"{self.temp_build_root}/lambda_function.py", "w") as text_file:
                text_file.write(lambda_src_string)
        except Exception as e:
            error = f"Error writing lambda Python source file: {e}"
            self.logger.error(error)
            raise RuntimeError(error)

        try:
            with zipfile.ZipFile(
                self.built_archive,
                "a",
                compression=zipfile.ZIP_DEFLATED,
            ) as zipf:
                zipf.write(
                    f"{self.temp_build_root}/lambda_function.py", "lambda_function.py"
                )
        except Exception as e:
            error = f"Error inserting lambda Python source file into zip: {e}"
            self.logger.error(error)
            raise RuntimeError(error)

        with open(self.built_archive, "rb") as f:
            zipped_code = f.read()

        try:
            response = lambda_client.create_function(
                FunctionName=f"{self.app_id}_{self.name}",
                Runtime=self.python_runtime_version,
                Role=self.lambda_role_arn,
                Handler="lambda_function.lambda_handler",
                Code={"ZipFile": zipped_code},
                Description=f"{self.app_id} tool: {self.name}",
                Timeout=30,
                MemorySize=256,
            )
        except ClientError as e:
            error = f"Error creating lambda. Client error: {e}"
            self.logger.error(error)
            raise RuntimeError(error)

        except Exception as e:
            error = f"Error creating lambda. Unexpected error: {e}"
            self.logger.error(error)
            raise RuntimeError(error)

        # Clean up the .zip archive build
        try:
            shutil.rmtree(self.temp_build_root)
        except OSError as e:
            error = (
                f"Error deleting temporary build directory {self.temp_build_root}: {e}"
            )
            self.logger.error(error)
            pass

        # Add the resourced-base policy allowing the lambda to be invoked
        # by the agent.
        try:
            add_permission_response = lambda_client.add_permission(
                StatementId=f"{self.app_id}-bedrock-invoke",
                FunctionName=response["FunctionArn"],
                Action="lambda:InvokeFunction",
                Principal="bedrock.amazonaws.com",
                # TODO: fix this. Remove wildcard
                SourceArn=f"arn:aws:bedrock:us-east-1:{self.aws_account_id}:agent/*",
            )
        except ClientError as e:
            error = f"Error attaching resource policy to lambda execution role. Client error: {e}"
            self.logger.error(error)
            raise RuntimeError(error)
        except Exception as e:
            error = f"Error attaching resource policy to lambda execution role. Unexpected error: {e}"
            self.logger.error(error)
            raise RuntimeError(error)

        return response["FunctionArn"]

    def _create_bedrock_lambda_role(self) -> str:
        """Get or create IAM role for Bedrock integration"""
        iam = boto3.client("iam")

        self.lambda_role_name = f"{self.app_id}_bedrock_lambda_execution_role"
        self.assume_role = self._get_assumed_role(service="lambda.amazonaws.com")

        try:
            iam.create_role(
                RoleName=self.lambda_role_name,
                AssumeRolePolicyDocument=json.dumps(self.assume_role),
            )
        except ClientError as e:
            error = f"Error creating lambda execution role. Client error: {e}"
            self.logger.error(error)
            raise RuntimeError(error)
        except Exception as e:
            error = f"Error creating lambda execution role. Unexpected error: {e}"
            self.logger.error(error)
            raise RuntimeError(error)

        try:
            iam.attach_role_policy(
                RoleName=self.lambda_role_name,
                PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
            )
        except ClientError as e:
            error = f"Error attaching managed policy to lambda execution role. Client error: {e}"
            self.logger.error(error)
            raise RuntimeError(error)

        except Exception as e:
            error = f"Error attaching managed policy to lambda execution role. Unexpected error: {e}"
            self.logger.error(error)
            raise RuntimeError(error)

        return iam.get_role(RoleName=self.lambda_role_name)["Role"]["Arn"]

    def _create_bedrock_agent(self) -> str:
        """Create Bedrock agent"""

        self.agent_role_arn = self._create_agent_role()

        args = {
            "agentName": f"{self.app_id}_{self.agent_name}Agent",
            "agentResourceRoleArn": self.agent_role_arn,
            "foundationModel": self.agent_target_model,
            "idleSessionTTLInSeconds": self.agent_session_timeout,
            "instruction": self.agent_instruction,
            "description": self.agent_description,
        }

        try:
            response = self.bedrock_agent_client.create_agent(**args)
        except ClientError as e:
            error = f"Error creating agent. Client error: {e}"
            self.logger.error(error)
            raise RuntimeError(error)

        except Exception as e:
            error = f"Error creating agent. Unexpected error: {e}"
            self.logger.error(error)
            raise RuntimeError(error)

        return response["agent"]["agentId"]

    def _create_agent_action_group(self):
        """Create Bedrock action group and attach to Bedrock agent"""

        args = {
            "agentId": self.agent_id,
            "actionGroupExecutor": {
                "lambda": self.lambda_arn,
            },
            "actionGroupName": f"{self.app_id}_{self.agent_name}_ag",
            "agentVersion": "DRAFT",
            "apiSchema": {"payload": json.dumps(self.openapi_schema_dict)},
            "description": self.agent_description,
        }

        # Wait until agent status transitions to CREATING before creating the action group.
        counter = 0
        agent_details = self.bedrock_agent_client.get_agent(agentId=self.agent_id)
        agent_status = agent_details["agent"]["agentStatus"]
        while (agent_status == "CREATING") and (counter <= 9):
            counter = counter + 1
            time.sleep(1)
            agent_details = self.bedrock_agent_client.get_agent(agentId=self.agent_id)
            agent_status = agent_details["agent"]["agentStatus"]

        if counter == 10:
            error = f"Error creating agent timeout. Agent created, but status never transitioned out of CREATING"
            self.logger.error(error)
            raise RuntimeError(error)

        try:
            agent_action_group = self.bedrock_agent_client.create_agent_action_group(
                **args
            )
            self.agent_action_group_id = agent_action_group["agentActionGroup"][
                "actionGroupId"
            ]
        except ClientError as e:
            error = f"Error creating agent action group. Client error: {e}"
            self.logger.error(error)
            raise RuntimeError(error)
        except Exception as e:
            error = f"Error creating agent action group. Unexpected error: {e}"
            self.logger.error(error)
            raise RuntimeError(error)

        return agent_action_group

    def _create_agent_role(self) -> str:
        """Create IAM agent role for Bedrock integration"""

        iam = boto3.client("iam")

        self.agent_role_name = f"{self.app_id}_bedrock_agent_execution_role"
        self.agent_policy_name = f"{self.app_id}_bedrock_agent_allow_model"

        assume_role = self._get_assumed_role(service="bedrock.amazonaws.com")

        try:
            iam.create_role(
                RoleName=self.agent_role_name,
                AssumeRolePolicyDocument=json.dumps(assume_role),
            )
        except ClientError as e:
            error = f"Error creating agent role. Client error: {e}"
            self.logger.error(error)
            raise RuntimeError(error)
        except Exception as e:
            error = f"Error creating agent role. Unexpected error: {e}"
            self.logger.error(error)
            raise RuntimeError(error)

        managed_policy_txt = self._get_managed_policy(
            resource=f"foundation-model/{self.agent_target_model}"
        )

        try:
            managed_policy = iam.create_policy(
                PolicyName=self.agent_policy_name,
                PolicyDocument=json.dumps(managed_policy_txt),
            )
        except ClientError as e:
            error = f"Error creating agent policy. Client error: {e}"
            self.logger.error(error)
            raise RuntimeError(error)
        except Exception as e:
            error = f"Error creating agent policy. Unexpected error: {e}"
            self.logger.error(error)
            raise RuntimeError(error)

        self.agent_role_policy_arn = (
            f"arn:aws:iam::{self.aws_account_id}:policy/{self.agent_policy_name}"
        )
        try:
            iam.attach_role_policy(
                RoleName=self.agent_role_name,
                PolicyArn=self.agent_role_policy_arn,
            )
        except ClientError as e:
            error = f"Error creating attaching policy to agent role. Client error: {e}"
            self.logger.error(error)
            raise RuntimeError(error)
        except Exception as e:
            error = (
                f"Error creating attaching policy to agent role. Unexpected error: {e}"
            )
            self.logger.error(error)
            raise RuntimeError(error)

        return iam.get_role(RoleName=self.agent_role_name)["Role"]["Arn"]

    def _get_assumed_role(self, service: str = None) -> str:
        """Skeleton code for creating a role"""
        role = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": f"{service}"},
                    "Action": "sts:AssumeRole",
                }
            ],
        }
        return role

    def _get_managed_policy(self, resource: str = None) -> str:
        """Skeleton code for creating a policy"""
        managed_policy_txt = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "bedrock:InvokeModel",
                    "Resource": f"arn:aws:bedrock:us-east-1::{resource}",
                    "Effect": "Allow",
                }
            ],
        }

        return managed_policy_txt

    def _get_lambda_source(
        self, module_name: str = None, class_name: str = None
    ) -> str:
        """Bedrock wrapped lambda used by the agent"""

        # funky spacing below is required...
        lambda_src = f"""
import json
from {module_name} import {class_name}


def lambda_handler(event, context):
    tool = {class_name}()
    result = tool.fn()
    action_response = {{
        "actionGroup": event["actionGroup"],
        "apiPath": event["apiPath"],
        "httpMethod": event["httpMethod"],
        "httpStatusCode": 200,
        "responseBody": {{"application/json": {{"body": json.dumps(result)}}}},
    }}
    api_response = {{"messageVersion": "1.0", "response": action_response}}

    return api_response"""
        return lambda_src

    def delete_app(self, bedrock_config: dict = None) -> bool:
        """Tear down the boto3 stack created by .export_to_bedrock()"""

        valid_bedrock_config_schema = {
            "type": "object",
            "properties": {
                "lambdaARN": {"type": "string"},
                "lambdaRoleName": {"type": "string"},
                "agentId": {"type": "string"},
                "agentRoleName": {"type": "string"},
                "agentPolicyARN": {"type": "string"},
                "agentActionGroup": {"type": "string"},
            },
            "required": [
                "lambdaARN",
                "lambdaRoleName",
                "agentId",
                "agentRoleName",
                "agentPolicyARN",
                "agentActionGroup",
            ],
        }
        try:
            validate(bedrock_config, valid_bedrock_config_schema)
        except jsonschema.exceptions.ValidationError as err:
            error = f"JSON validation failure on input bedrock_config: {err}"
            self.logger.error(error)
            raise RuntimeError(error)

        self.lambda_client = boto3.client("lambda")
        self.iam_client = boto3.client("iam")
        self.bedrock_agent_client = boto3.client("bedrock-agent")

        # Order is important here...
        try:
            detach_agent_policy = self.iam_client.detach_role_policy(
                RoleName=bedrock_config["agentRoleName"],
                PolicyArn=bedrock_config["agentPolicyARN"],
            )
        except ClientError as e:
            error = f"Error detaching agent policy. Client error: {e}"
            self.logger.error(error)
            pass
        except Exception as e:
            error = f"Error detaching agent policy. Unexpected error: {e}"
            self.logger.error(error)
            pass
        try:
            delete_agent_role = self.iam_client.delete_role(
                RoleName=bedrock_config["agentRoleName"]
            )
        except ClientError as e:
            error = f"Error deleting agent role. Client error: {e}"
            self.logger.error(error)
            pass
        except Exception as e:
            error = f"Error deleting agent role. Unexpected error: {e}"
            self.logger.error(error)
            pass

        try:
            delete_agent_policy = self.iam_client.delete_policy(
                PolicyArn=bedrock_config["agentPolicyARN"]
            )
        except ClientError as e:
            error = f"Error deleting agent policy. Client error: {e}"
            self.logger.error(error)
            pass
        except Exception as e:
            error = f"Error deleting agent policy. Unexpected error: {e}"
            self.logger.error(error)
            pass

        try:
            delete_agent = self.bedrock_agent_client.delete_agent(
                agentId=bedrock_config["agentId"], skipResourceInUseCheck=True
            )
        except ClientError as e:
            error = f"Error deleting agent. Client error: {e}"
            self.logger.error(error)
            pass
        except Exception as e:
            error = f"Error deleting agent. Unexpected error: {e}"
            self.logger.error(error)
            pass

        try:
            detach_lambda_policy = self.iam_client.detach_role_policy(
                RoleName=bedrock_config["lambdaRoleName"],
                PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
            )
        except ClientError as e:
            error = f"Error detaching lambda policy. Client error: {e}"
            self.logger.error(error)
            pass
        except Exception as e:
            error = f"Error detaching lambda policy. Unexpected error: {e}"
            self.logger.error(error)
            pass

        try:
            delete_lambda_role = self.iam_client.delete_role(
                RoleName=bedrock_config["lambdaRoleName"]
            )
        except ClientError as e:
            error = f"Error deleting lambda role. Client error: {e}"
            self.logger.error(error)
            pass
        except Exception as e:
            error = f"Error deleting lambda role. Unexpected error: {e}"
            self.logger.error(error)
            pass

        try:
            delete_lambda = self.lambda_client.delete_function(
                FunctionName=bedrock_config["lambdaARN"]
            )
        except ClientError as e:
            error = f"Error deleting lambda. Client error: {e}"
            self.logger.error(error)
            pass
        except Exception as e:
            error = f"Error deleting lambda. Unexpected error: {e}"
            self.logger.error(error)
            pass
