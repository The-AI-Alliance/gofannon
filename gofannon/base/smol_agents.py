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

        inputs_definition = {
            "example_arg": {
                "type": "string",
                "description": "Example argument recognized by this tool",
            }
        }
        output_type = "string"

        exported_tool = SmolTool()
        exported_tool.name = getattr(self, "name", "exported_base_tool")
        exported_tool.description = getattr(self, "description", "Exported from Tool")
        exported_tool.inputs = inputs_definition
        exported_tool.output_type = output_type
        exported_tool.forward = smol_forward
        exported_tool.is_initialized = True

        return exported_tool
