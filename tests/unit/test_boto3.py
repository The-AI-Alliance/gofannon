from gofannon.open_notify_space.iss_locator import IssLocator
import json
import unittest
from unittest.mock import patch, MagicMock
import botocore.exceptions

perfect_agent_app_config = {
    "app_id": "gofannon_demo",
    "agent_name": "ISSLocator",
    "agent_session_timeout": 600,
    "instruction": "You are an agent skilled at tracking and reporting the location of the International Space Station. Your role is to help users understand where the ISS is currently located by providing its geographic coordinates and other relevant location details.",
    "agent_description": "This agent helps to locate the location of the ISS.",
    "target_model": "anthropic.claude-3-sonnet-20240229-v1:0",
    "python_runtime_version": "python3.13",
    "temp_build_root": "/tmp/build",
}
bogus_agent_app_config = {
    "agent_name": "ISSLocator",
    "agent_session_timeout": 600,
    "instruction": "You are an agent skilled at tracking and reporting the location of the International Space Station. Your role is to help users understand where the ISS is currently located by providing its geographic coordinates and other relevant location details.",
    "agent_description": "This agent helps to locate the location of the ISS.",
    "target_model": "anthropic.claude-3-sonnet-20240229-v1:0",
    "python_runtime_version": "python3.13",
    "temp_build_root": "/tmp/build",
}


class TestFailureModule(unittest.TestCase):

    @patch("boto3.client")
    @patch("jsonschema.validate")
    def test_export_to_bedrock_perfect_case(self, mock_validate, mock_boto_client):
        # Mock dependencies
        mock_logger = MagicMock()
        mock_boto_instance = MagicMock()
        mock_boto_client.return_value = mock_boto_instance

        mock_boto_instance.get_caller_identity.return_value = {
            "Account": "123456789012"
        }
        mock_boto_instance.prepare_agent.return_value = {}

        obj = IssLocator()  # Replace with actual class name
        obj.logger = mock_logger
        obj._generate_openapi_schema = MagicMock(return_value={})
        obj._create_bedrock_lambda = MagicMock(return_value="mock_lambda_arn")
        obj.lambda_role_name = "mock_lambda_role_name"
        obj.agent_role_name = "mock_agent_role_name"
        obj.agent_role_policy_arn = "mock_agent_role_policy_arn"
        obj.agent_action_group_id = "mock_action_group_id"
        obj._create_bedrock_agent = MagicMock(return_value="mock_agent_id")
        obj._create_agent_action_group = MagicMock(return_value="mock_action_group_id")

        agent_app_config = {
            "app_id": "test_app",
            "agent_name": "ISSLocator",
            "agent_session_timeout": 3600,
            "instruction": "test instruction",
            "agent_description": "test description",
            "target_model": "test_model",
            "python_runtime_version": "3.9",
            "temp_build_root": "/tmp/test",
        }

        result = obj.export_to_bedrock(agent_app_config)

        self.assertEqual(result["lambdaARN"], "mock_lambda_arn")
        self.assertEqual(result["agentId"], "mock_agent_id")
        self.assertEqual(result["agentActionGroup"], "mock_action_group_id")
        self.assertEqual(result["agentPolicyARN"], "mock_agent_role_policy_arn")
        self.assertEqual(result["agentRoleName"], "mock_agent_role_name")
        self.assertEqual(result["lambdaRoleName"], "mock_lambda_role_name")

    def test_boto3_invalid_agent_app_config(self):
        iss_locator = IssLocator()
        with self.assertRaises(RuntimeError) as context:
            bedrock_config = iss_locator.export_to_bedrock(
                agent_app_config=bogus_agent_app_config
            )
        expected_error = "JSON validation failure on input parameters: 'app_id' is a required property"
        self.assertEqual(expected_error, str(context.exception)[: len(expected_error)])

    @patch("boto3.client")
    def test_boto3_aws_account_client_error(self, mock_boto_client):
        # Simulate a ClientError from boto3
        from botocore.exceptions import ClientError

        mock_boto_client.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "GetCallerIdentity",
        )

        obj = IssLocator()
        with self.assertRaises(ClientError) as context:
            result = obj.export_to_bedrock(agent_app_config=perfect_agent_app_config)

        expected_error = "An error occurred (AccessDenied) when calling the GetCallerIdentity operation: Access Denied"
        self.assertIn(expected_error, str(context.exception))

    @patch("boto3.client")
    def test_export_to_bedrock_unexpected_error(self, mock_boto_client):
        # Simulate a generic exception
        mock_boto_client.side_effect = Exception("Some unexpected error")

        obj = IssLocator()

        with self.assertRaises(Exception) as context:
            obj.export_to_bedrock(agent_app_config=perfect_agent_app_config)

        self.assertIn(
            "Some unexpected error",
            str(context.exception),
        )

    @patch("boto3.client")
    @patch("jsonschema.validate")
    def test_export_to_bedrock_create_lambda_fails(
        self, mock_validate, mock_boto_client
    ):
        # Mock dependencies
        mock_logger = MagicMock()
        mock_boto_instance = MagicMock()
        mock_boto_client.return_value = mock_boto_instance

        mock_boto_instance.get_caller_identity.return_value = {
            "Account": "123456789012"
        }

        obj = IssLocator()  # Replace with actual class name
        obj.logger = mock_logger
        obj._generate_openapi_schema = MagicMock(return_value={})
        obj._create_bedrock_lambda = MagicMock(
            side_effect=RuntimeError("Error creating .zip archive.")
        )

        with self.assertRaises(RuntimeError) as context:
            obj.export_to_bedrock(agent_app_config=perfect_agent_app_config)

        expected_error = "Error creating .zip archive."
        self.assertEqual(expected_error, str(context.exception)[: len(expected_error)])

    @patch("boto3.client")
    @patch("jsonschema.validate")
    def test_export_to_bedrock_create_bedrock_agent_fails(
        self, mock_validate, mock_boto_client
    ):
        # Mock dependencies
        mock_logger = MagicMock()
        mock_boto_instance = MagicMock()
        mock_boto_client.return_value = mock_boto_instance

        mock_boto_instance.get_caller_identity.return_value = {
            "Account": "123456789012"
        }

        obj = IssLocator()
        obj.logger = mock_logger
        obj._generate_openapi_schema = MagicMock(return_value={})
        obj._create_bedrock_lambda = MagicMock(return_value="mock_lambda_arn")
        obj._create_bedrock_agent = MagicMock(
            side_effect=RuntimeError(
                "Error creating agent. Client error: Agent with AgentId already exists."
            )
        )

        with self.assertRaises(RuntimeError) as context:
            obj.export_to_bedrock(agent_app_config=perfect_agent_app_config)

        expected_error = (
            "Error creating agent. Client error: Agent with AgentId already exists."
        )
        self.assertEqual(expected_error, str(context.exception)[: len(expected_error)])

    @patch("boto3.client")
    @patch("jsonschema.validate")
    def test_export_to_bedrock_create_agent_action_group_fails(
        self, mock_validate, mock_boto_client
    ):
        # Mock dependencies
        mock_logger = MagicMock()
        mock_boto_instance = MagicMock()
        mock_boto_client.return_value = mock_boto_instance

        mock_boto_instance.get_caller_identity.return_value = {
            "Account": "123456789012"
        }

        obj = IssLocator()
        obj.logger = mock_logger
        obj._generate_openapi_schema = MagicMock(return_value={})
        obj._create_bedrock_lambda = MagicMock(return_value="mock_lambda_arn")
        obj._create_bedrock_agent = MagicMock(return_value="mock_agent_id")
        obj._create_agent_action_group = MagicMock(
            side_effect=RuntimeError(
                "Error creating agent action group. Client error: AgentId does not exist"
            )
        )

        with self.assertRaises(RuntimeError) as context:
            obj.export_to_bedrock(agent_app_config=perfect_agent_app_config)

        expected_error = (
            "Error creating agent action group. Client error: AgentId does not exist"
        )
        self.assertEqual(expected_error, str(context.exception)[: len(expected_error)])

    @patch("boto3.client")
    @patch("jsonschema.validate")
    def test_export_to_bedrock_preapre_agent_fails(
        self, mock_validate, mock_boto_client
    ):
        # Mock dependencies
        mock_logger = MagicMock()
        mock_boto_instance = MagicMock()
        mock_boto_client.return_value = mock_boto_instance

        mock_boto_instance.get_caller_identity.return_value = {
            "Account": "123456789012"
        }

        obj = IssLocator()
        obj.logger = mock_logger
        obj._generate_openapi_schema = MagicMock(return_value={})
        obj._create_bedrock_lambda = MagicMock(return_value="mock_lambda_arn")
        obj._create_bedrock_agent = MagicMock(return_value="mock_agent_id")
        obj._create_agent_action_group = MagicMock(return_value="mock_action_group_id")
        mock_boto_instance.prepare_agent = MagicMock(
            side_effect=botocore.exceptions.ClientError(
                {"Error": {"Code": "SomeError", "Message": "AgentId does not exist"}},
                "SomeOperation",
            )
        )

        with self.assertRaises(RuntimeError) as context:
            obj.export_to_bedrock(agent_app_config=perfect_agent_app_config)

        expected_error = (
            "Error preparing agent. Client error: An error occurred (SomeError)"
        )
        self.assertEqual(expected_error, str(context.exception)[: len(expected_error)])

    @patch("boto3.client")
    def test_create_bedrock_agent_perfect_case(self, mock_boto_client):
        # Mock dependencies
        mock_logger = MagicMock()

        obj = IssLocator()
        obj.bedrock_agent_client = mock_boto_client
        # self.bedrock_agent_client.create_agent(**args)
        obj.logger = mock_logger
        obj._create_agent_role = MagicMock(return_value={})
        obj.bedrock_agent_client.create_agent = MagicMock(
            return_value={"agent": {"agentId": "mock_agent_id"}}
        )
        obj.app_id = "AppId"
        obj.agent_name = "AgentName"
        obj.agent_target_model = "AgentTargetModel"
        obj.agent_session_timeout = 200
        obj.agent_instruction = "AgentInstructions"
        obj.agent_description = "AgentDescription"
        result = obj._create_bedrock_agent()
        self.assertEqual(result, "mock_agent_id")

    @patch("boto3.client")
    def test_create_bedrock_agent_fails(self, mock_boto_client):
        # Mock dependencies
        mock_logger = MagicMock()

        obj = IssLocator()
        obj.bedrock_agent_client = mock_boto_client
        # self.bedrock_agent_client.create_agent(**args)
        obj.logger = mock_logger
        obj._create_agent_role = MagicMock(return_value={})
        obj.bedrock_agent_client.create_agent = MagicMock(
            side_effect=botocore.exceptions.ClientError(
                {
                    "Error": {
                        "Code": "SomeError",
                        "Message": "Agent Role ARN does not exist",
                    }
                },
                "SomeOperation",
            )
        )
        obj.app_id = "AppId"
        obj.agent_name = "AgentName"
        obj.agent_target_model = "AgentTargetModel"
        obj.agent_session_timeout = 200
        obj.agent_instruction = "AgentInstructions"
        obj.agent_description = "AgentDescription"

        with self.assertRaises(RuntimeError) as context:
            obj._create_bedrock_agent()

        expected_error = (
            "Error creating agent. Client error: An error occurred (SomeError)"
        )

        self.assertEqual(expected_error, str(context.exception)[: len(expected_error)])


if __name__ == "__main__":
    unittest.main()
