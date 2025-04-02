import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable
import json
import logging
from pathlib import Path

import anyio

from ..config import ToolConfig

from .smol_agents import SmolAgentsMixin
from .langchain import LangchainMixin
from .bedrock import BedrockMixin
from .langflow import LangflowMixin
from .mcp import MCPMixin


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
            return ToolResult(success=False, output=None, error=str(e), retryable=True)

    async def execute_async(self, arguments: dict):
        return await anyio.to_thread.run_sync(self.fn, **arguments)
