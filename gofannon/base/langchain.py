from typing import Type, Callable

try:
    from langchain.tools import BaseTool as LangchainBaseTool
    from pydantic.v1 import BaseModel, Field

    _HAS_LANGCHAIN = True
except ImportError:
    _HAS_LANGCHAIN = False


class LangchainMixin:
    def import_from_langchain(self, langchain_tool):
        if not _HAS_LANGCHAIN:
            raise RuntimeError(
                "langchain is not installed. Install with `pip install langchain-core`"
            )

        self.name = getattr(langchain_tool, "name", "exported_langchain_tool")
        self.description = getattr(
            langchain_tool, "description", "No description provided."
        )

        maybe_args_schema = getattr(langchain_tool, "args_schema", None)
        if (
            maybe_args_schema
            and hasattr(maybe_args_schema, "schema")
            and callable(maybe_args_schema.schema)
        ):
            args_schema = maybe_args_schema.schema()
        else:
            args_schema = {}

        self._parameters = args_schema.get("properties", {})
        self._required = args_schema.get("required", [])

        def adapted_fn(*args, **kwargs):
            return langchain_tool._run(*args, **kwargs)

        self.fn = adapted_fn

    def export_to_langchain(self):
        if not _HAS_LANGCHAIN:
            raise RuntimeError(
                "langchain is not installed. Install with `pip install langchain-core`"
            )

        from pydantic import create_model

        type_map = {
            "number": float,
            "string": str,
            "integer": int,
            "boolean": bool,
            "object": dict,
            "array": list,
        }

        parameters = self.definition.get("function", {}).get("parameters", {})
        param_properties = parameters.get("properties", {})

        fields = {}
        for param_name, param_def in param_properties.items():
            param_type = param_def.get("type", "string")
            description = param_def.get("description", "")
            fields[param_name] = (
                type_map.get(param_type, str),
                Field(..., description=description),
            )

        ArgsSchema = create_model("ArgsSchema", **fields)

        class ExportedTool(LangchainBaseTool):
            name: str = self.definition.get("function", {}).get("name", "")
            description: str = self.definition.get("function", {}).get(
                "description", ""
            )
            args_schema: Type[BaseModel] = ArgsSchema
            fn: Callable = self.fn

            def _run(self, *args, **kwargs):
                return self.fn(*args, **kwargs)

        tool = ExportedTool()
        return tool
