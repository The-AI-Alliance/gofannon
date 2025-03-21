try:
    from smolagents.tools import Tool as SmolTool
    from smolagents.tools import tool as smol_tool_decorator

    _HAS_SMOLAGENTS = True
except ImportError:
    _HAS_SMOLAGENTS = False


class SmolAgentsMixin:
    def import_from_smolagents(self, smol_tool):
        if not _HAS_SMOLAGENTS:
            raise RuntimeError(
                "smolagents is not installed or could not be imported. "
                "Install it or check your environment."
            )
        self.name = smol_tool.name[0]
        self.description = smol_tool.description

        def adapted_fn(*args, **kwargs):
            return smol_tool.forward(*args, **kwargs)

        self.fn = adapted_fn

    def export_to_smolagents(self):
        if not _HAS_SMOLAGENTS:
            raise RuntimeError(
                "smolagents is not installed or could not be imported. "
                "Install it or check your environment."
            )

        def smol_forward(*args, **kwargs):
            return self.fn(*args, **kwargs)

        # Get the parameters from the Gofannon tool definition
        parameters = self.definition.get("function", {}).get("parameters", {})
        param_properties = parameters.get("properties", {})
        required_params = parameters.get("required", [])

        # Create inputs_definition from the Gofannon tool definition
        inputs_definition = {}
        for param_name, param_def in param_properties.items():
            inputs_definition[param_name] = {
                "type": param_def.get("type", "string"),
                "description": param_def.get("description", ""),
                #"required": param_name in required_params
            }

            # Get the description from the Gofannon tool definition
        description = self.definition.get("function", {}).get("description", "Exported from Gofannon tool")

        exported_tool = SmolTool()
        exported_tool.name = getattr(self, "name", "exported_base_tool")
        exported_tool.description = description
        exported_tool.inputs = inputs_definition
        exported_tool.output_type = "string"
        exported_tool.forward = smol_forward
        exported_tool.is_initialized = True

        return exported_tool