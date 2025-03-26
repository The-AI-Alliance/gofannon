try:
    from langflow.custom import Component
    from langflow.io import MessageTextInput, IntInput, BoolInput, FloatInput, Output
    from langflow.schema import Data

    _HAS_LANGFLOW = True
except ImportError:
    _HAS_LANGFLOW = False


class LangflowMixin:
    def import_from_langflow(self, langflow_component):
        """Adapt a Langflow component to a Gofannon tool"""
        if not _HAS_LANGFLOW:
            raise RuntimeError(
                "langflow is not installed. Install with `pip install langflow`"
            )

        self.name = langflow_component.display_name.replace(" ", "_").lower()
        self.description = langflow_component.description

        # Extract parameters from component inputs
        parameters = {
            "type": "object",
            "properties": {},
            "required": []
        }

        for component_input in langflow_component.inputs:
            if component_input.name in ["self", "context"]:
                continue

            param_type = "string"
            if isinstance(component_input, (IntInput, FloatInput)):
                param_type = "number"
            elif isinstance(component_input, BoolInput):
                param_type = "boolean"

            parameters["properties"][component_input.name] = {
                "type": param_type,
                "description": component_input.info or ""
            }

            if component_input.required:
                parameters["required"].append(component_input.name)

        self.definition = {
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": parameters
            }
        }

        # Create execution wrapper
        def adapted_fn(**kwargs):
            result = langflow_component.build()(**kwargs)
            return result.data if isinstance(result, Data) else result

        self.fn = adapted_fn

    def export_to_langflow(self):
        """Convert Gofannon tool to Langflow component"""
        if not _HAS_LANGFLOW:
            raise RuntimeError(
                "langflow is not installed. Install with `pip install langflow`"
            )

        parameters = self.definition.get("function", {}).get("parameters", {})
        param_properties = parameters.get("properties", {})
        required_params = parameters.get("required", [])

        # Create input fields
        component_inputs = []
        type_map = {
            "string": MessageTextInput,
            "number": FloatInput,
            "integer": IntInput,
            "boolean": BoolInput
        }

        for param_name, param_def in param_properties.items():
            input_type = param_def.get("type", "string")
            InputClass = type_map.get(input_type, MessageTextInput)

            component_inputs.append(
                InputClass(
                    name=param_name,
                    display_name=param_name.replace("_", " ").title(),
                    info=param_def.get("description", ""),
                    required=param_name in required_params,
                    tool_mode=True
                )
            )

            # Define component class
        class ExportedComponent(Component):
            display_name = self.definition["function"]["name"].title()
            description = self.definition["function"]["description"]
            icon = "tool"

            inputs = component_inputs
            outputs = [Output(display_name="Result", name="result", method="run_tool")]

            def run_tool(self, **kwargs):
                result = self.tool.execute(context=None, **kwargs)
                return Data(data=result.output)

                # Attach tool instance to component class
        ExportedComponent.tool = self
        return ExportedComponent