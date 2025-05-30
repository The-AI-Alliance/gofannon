# gofannon/base/__init__.py  
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
import json
import logging
from pathlib import Path
import inspect # Kept for potential future use, but not strictly needed for static manifest reading  

import anyio

from .adk_mixin import AdkMixin
from ..config import ToolConfig, FunctionRegistry # FunctionRegistry may not be directly used by create_manifest now  

from .smol_agents import SmolAgentsMixin
from .langchain import LangchainMixin
from .bedrock import BedrockMixin
from .langflow import LangflowMixin
from .mcp import MCPMixin
from .llamastack import LlamaStackMixin


@dataclass
class ToolResult:
    success: bool
    output: Any
    error: str = None
    retryable: bool = False


class WorkflowContext:
    def __init__(self, firebase_config=None):
        self.data = {}
        self.execution_log = []
        self.firebase_config = firebase_config
        self.local_storage = Path.home() / ".llama" / "checkpoints"
        self.local_storage.mkdir(parents=True, exist_ok=True)

    def save_checkpoint(self, name="checkpoint"):
        if self.firebase_config:
            self._save_to_firebase(name)
        else:
            self._save_local(name)

    def _save_local(self, name):
        path = self.local_storage / f"{name}.json"
        with open(path, "w") as f:
            json.dump({"data": self.data, "execution_log": self.execution_log}, f)

    def _save_to_firebase(self, name):
        from firebase_admin import firestore

        db = firestore.client()
        doc_ref = db.collection("checkpoints").document(name)
        doc_ref.set(
            {
                "data": self.data,
                "execution_log": self.execution_log,
                "timestamp": firestore.SERVER_TIMESTAMP,
            }
        )

    def log_execution(self, tool_name, duration, input_data, output_data):
        entry = {
            "tool": tool_name,
            "duration": duration,
            "input": input_data,
            "output": output_data,
        }
        self.execution_log.append(entry)


class BaseTool(SmolAgentsMixin,
               LangchainMixin,
               BedrockMixin,
               LangflowMixin,
               MCPMixin,
               LlamaStackMixin,
               AdkMixin,
               ABC):
    def __init__(self, **kwargs):
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )
        self._load_config()
        self._configure(**kwargs)
        self.logger.debug("Initialized %s tool", self.__class__.__name__)

    def _configure(self, **kwargs):
        """Set instance-specific configurations"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def _load_config(self):
        """Auto-load config based on tool type"""
        if hasattr(self, "API_SERVICE"):
            self.api_key = ToolConfig.get(f"{self.API_SERVICE}_api_key")

    @property
    @abstractmethod
    def definition(self):
        pass

    @property
    def output_schema(self):
        return self.definition.get("function", {}).get("parameters", {})

    @abstractmethod
    def fn(self, *args, **kwargs):
        pass

    def execute(self, context: WorkflowContext, **kwargs) -> ToolResult:
        try:
            start_time = time.time()
            result = self.fn(**kwargs)
            duration = time.time() - start_time

            context.log_execution(
                tool_name=self.__class__.__name__,
                duration=duration,
                input_data=kwargs,
                output_data=result,
            )

            return ToolResult(success=True, output=result)
        except Exception as e:
            self.logger.error(f"Error executing tool {self.__class__.__name__}: {e}", exc_info=True)
            return ToolResult(success=False, output=None, error=str(e), retryable=True)

    async def execute_async(self, arguments: dict):
        return await anyio.to_thread.run_sync(self.fn, **arguments)

    # Manifest Generation Logic
MANIFEST_FILE_NAME = "manifest.json"

def create_manifest() -> Dict[str, Any]:
    """  
    Reads the Gofannon tools manifest from a static JSON file.  
    The manifest file should be located at `gofannon/manifest.json`.  
    """
    manifest_logger = logging.getLogger(f"{__name__}.create_manifest")

    # Determine the path to manifest.json relative to this file's location  
    # Path(__file__) is gofannon/base/__init__.py  
    # Path(__file__).parent is gofannon/base/  
    # Path(__file__).parent.parent is gofannon/  
    manifest_path = Path(__file__).parent.parent / MANIFEST_FILE_NAME

    if not manifest_path.exists():
        manifest_logger.error(f"Manifest file not found at {manifest_path}. Returning empty manifest.")
        return {
            "manifest_version": "1.1",
            "source": "error_file_not_found",
            "description": f"Error: {MANIFEST_FILE_NAME} not found at expected location.",
            "tools": []
        }

    try:
        with open(manifest_path, 'r') as f:
            manifest_data = json.load(f)
        manifest_logger.info(f"Successfully loaded manifest from {manifest_path}")

        # Ensure all tools from FunctionRegistry are represented in the manifest (optional validation step)  
        # This part is a bit more involved if you want to strictly enforce it at runtime.  
        # For now, we trust the manifest.json is kept up-to-date.  
        # If validation is desired:  
        #   registered_tool_names_from_code = {  
        #       tool_class().definition['function']['name']   
        #       for tool_class in FunctionRegistry._tools.values()  
        #       if 'function' in tool_class().definition and 'name' in tool_class().definition['function']  
        #   }  
        #   manifest_tool_names = {tool['name'] for tool in manifest_data.get('tools', [])}  
        #     
        #   missing_in_manifest = registered_tool_names_from_code - manifest_tool_names  
        #   if missing_in_manifest:  
        #       manifest_logger.warning(f"Tools registered in code but missing from manifest.json: {missing_in_manifest}")  
        #     
        #   extra_in_manifest = manifest_tool_names - registered_tool_names_from_code  
        #   if extra_in_manifest:  
        #       manifest_logger.warning(f"Tools in manifest.json but not registered in code: {extra_in_manifest}")  

        return manifest_data
    except json.JSONDecodeError as e:
        manifest_logger.error(f"Error decoding JSON from {manifest_path}: {e}. Returning error manifest.")
        return {
            "manifest_version": "1.1",
            "source": "error_json_decode",
            "description": f"Error: Could not parse {MANIFEST_FILE_NAME}. Invalid JSON: {e}",
            "tools": []
        }
    except Exception as e:
        manifest_logger.error(f"An unexpected error occurred while reading {manifest_path}: {e}. Returning error manifest.")
        return {
            "manifest_version": "1.1",
            "source": "error_unexpected",
            "description": f"Error: Unexpected issue reading {MANIFEST_FILE_NAME}: {e}",
            "tools": []
        }  
  