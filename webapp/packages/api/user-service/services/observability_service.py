import abc
import asyncio
import boto3
from botocore.exceptions import ClientError
from datetime import datetime
import json
import os
from typing import Any, Dict, List, Optional
import traceback

from config import settings

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
import time
from fastapi.responses import JSONResponse


# --- Abstract Base Class for Providers ---

class LogProvider(abc.ABC):
    """Abstract base class for a logging provider."""
    @abc.abstractmethod
    async def log(self, payload: Dict[str, Any]):
        raise NotImplementedError

# --- Provider Implementations ---

class GoogleCloudLoggingProvider(LogProvider):
    """Logs to Google Cloud Logging."""
    def __init__(self, project_id: str):
        try:
            from google.cloud import logging
            self.logging_client = logging.Client(project=project_id)
            self.logger = self.logging_client.logger('gofannon-app-logs')
            print("Google Cloud Logging provider initialized.")
        except ImportError:
            raise ImportError("`google-cloud-logging` is not installed. Please install it to use the GCP logging provider.")
        except Exception as e:
            print(f"Failed to initialize Google Cloud Logging: {e}")
            raise

    async def log(self, payload: Dict[str, Any]):
        try:
            # Map our levels to GCP's severity
            level_map = {"INFO": "INFO", "WARN": "WARNING", "ERROR": "ERROR", "DEBUG": "DEBUG"}
            severity = level_map.get(payload.get("level", "INFO").upper(), "DEFAULT")
            self.logger.log_struct(payload, severity=severity)
        except Exception as e:
            print(f"Error logging to Google Cloud: {e}")

class AWSCloudWatchLogsProvider(LogProvider):
    """Logs to AWS CloudWatch Logs."""
    def __init__(self, region_name: str, access_key_id: str, secret_access_key: str, log_group_name: str):
        try:
            self.client = boto3.client(
                'logs',
                region_name=region_name,
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key
            )
            self.log_group_name = log_group_name
            self._ensure_log_group_exists()
            print(f"AWS CloudWatch Logs provider initialized for log group '{log_group_name}'.")
        except ClientError as e:
            print(f"Failed to initialize AWS CloudWatch Logs due to a client error: {e}")
            raise
        except Exception as e:
            print(f"Failed to initialize AWS CloudWatch Logs: {e}")
            raise

    def _ensure_log_group_exists(self):
        try:
            self.client.create_log_group(logGroupName=self.log_group_name)
            print(f"Created CloudWatch log group: {self.log_group_name}")
        except self.client.exceptions.ResourceAlreadyExistsException:
            pass # Group already exists, which is fine.

    async def log(self, payload: Dict[str, Any]):
        log_stream_name = payload.get("service", "general")
        
        # Serialize metadata if it's a dict
        if 'metadata' in payload and isinstance(payload['metadata'], dict):
            payload['metadata'] = json.dumps(payload['metadata'], default=str)

        log_event = {
            'timestamp': int(datetime.utcnow().timestamp() * 1000),
            'message': json.dumps(payload, default=str)
        }

        # NOTE: The standard boto3 client is synchronous. This log call will block
        # the asyncio task that runs it. For high-throughput applications,
        # consider using a library like 'aioboto3' to make this operation
        # fully non-blocking.
        try:
            self.client.put_log_events(
                logGroupName=self.log_group_name,
                logStreamName=log_stream_name,
                logEvents=[log_event]
            )
        except self.client.exceptions.ResourceNotFoundException:
            try:
                self.client.create_log_stream(logGroupName=self.log_group_name, logStreamName=log_stream_name)
                print(f"Created CloudWatch log stream: {log_stream_name}")
                self.client.put_log_events(
                    logGroupName=self.log_group_name,
                    logStreamName=log_stream_name,
                    logEvents=[log_event]
                )
            except Exception as e:
                print(f"Error creating CloudWatch log stream and logging: {e}")
        except Exception as e:
            print(f"Error logging to CloudWatch: {e}")

class ConsoleProvider(LogProvider):
    """Logs to the console. Used for local development."""
    def __init__(self):
        print("Console logging provider initialized.")

    async def log(self, payload: Dict[str, Any]):
        print(f"LOG: {json.dumps(payload, indent=2, default=str)}")

# --- Main Observability Service ---

class ObservabilityService:
    def __init__(self):
        self.providers: List[LogProvider] = []
        self._initialize_providers()

    def _initialize_providers(self):
        """Detect and initialize providers based on environment variables."""
        
        # Always add console logger for local/docker visibility
        if settings.APP_ENV == "local":
            self.providers.append(ConsoleProvider())

        # Google Cloud Logging
        if settings.GCP_PROJECT_ID:
            try:
                self.providers.append(GoogleCloudLoggingProvider(project_id=settings.GCP_PROJECT_ID))
            except Exception as e:
                print(f"Skipping Google Cloud Logging provider due to initialization error: {e}")

        # AWS CloudWatch Logs
        if all([settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY, settings.AWS_DEFAULT_REGION, settings.CLOUDWATCH_LOG_GROUP_NAME]):
            try:
                self.providers.append(AWSCloudWatchLogsProvider(
                    region_name=settings.AWS_DEFAULT_REGION,
                    access_key_id=settings.AWS_ACCESS_KEY_ID,
                    secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    log_group_name=settings.CLOUDWATCH_LOG_GROUP_NAME
                ))
            except Exception as e:
                print(f"Skipping AWS CloudWatch Logs provider due to initialization error: {e}")

        if not self.providers:
            print("No observability providers configured. Defaulting to console logging.")
            self.providers.append(ConsoleProvider())


    def _sanitize_for_json(self, value: Any) -> Any:
        """Recursively coerce values into JSON-serializable equivalents.

        This protects logging codepaths that run in environments without
        FastAPI (e.g., Firebase callable functions) where metadata may contain
        awaitables or other non-serializable objects. Anything unknown is
        converted to a string representation so that downstream JSON encoding
        never fails.
        """
        if isinstance(value, dict):
            return {k: self._sanitize_for_json(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._sanitize_for_json(v) for v in value]
        if asyncio.iscoroutine(value):
            return f"<coroutine {value.__name__ if hasattr(value, '__name__') else str(value)}>"
        try:
            json.dumps(value)
            return value
        except (TypeError, ValueError):
            return str(value)

    def log(
        self,
        event_type: str,
        message: str,
        level: str = "INFO",
        service: str = "user-service",
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Creates a log payload and sends it to all configured providers asynchronously.
        This is a fire-and-forget method.
        """
        raw_payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level.upper(),
            "eventType": event_type,
            "service": service,
            "userId": user_id,
            "message": message,
            "metadata": metadata or {},
        }

        payload = self._sanitize_for_json(raw_payload)

        async def _log_async():
            tasks = [provider.log(payload) for provider in self.providers]
            await asyncio.gather(*tasks)

        # Run in the background without blocking the caller
        asyncio.create_task(_log_async())

    def log_exception(self, exc: Exception, user_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        """Logs a Python exception."""
        if metadata is None:
            metadata = {}
        
        metadata['exception_type'] = type(exc).__name__
        metadata['traceback'] = traceback.format_exc()
        
        self.log(
            event_type="error",
            level="ERROR",
            message=str(exc),
            user_id=user_id,
            metadata=metadata
        )

# --- Singleton Factory ---
_observability_instance = None

def get_observability_service() -> ObservabilityService:
    global _observability_instance
    if _observability_instance is None:
        _observability_instance = ObservabilityService()
    return _observability_instance

class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        observability_service = get_observability_service()
        start_time = time.time()

        # Safely get user_id if auth middleware has already run
        user_id = getattr(request.state, 'user', {}).get('uid')

        request_data = {
            "method": request.method,
            "path": request.url.path,
            "headers": {k: v for k, v in request.headers.items() if k.lower() not in ['authorization', 'cookie']},
            "client_host": request.client.host if request.client else "unknown",
        }

        observability_service.log(event_type="api_request_start", message=f"API request started: {request.method} {request.url.path}", metadata=request_data, user_id=user_id)

        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # The user state might be set during call_next, so we get it again
            user_id = getattr(request.state, 'user', {}).get('uid', user_id)

            response_data = {
                **request_data,
                "status_code": response.status_code,
                "process_time": f"{process_time:.4f}s",
            }
            observability_service.log(event_type="api_request_end", message=f"API request finished: {response.status_code}", metadata=response_data, user_id=user_id)
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            user_id = getattr(request.state, 'user', {}).get('uid', user_id)
            
            error_data = {
                **request_data,
                "process_time": f"{process_time:.4f}s",
                "error": str(e),
                "traceback": traceback.format_exc(),
            }
            observability_service.log(
                event_type="uncaught_api_exception", 
                message="An uncaught API exception occurred.", 
                level="ERROR", 
                metadata=error_data,
                user_id=user_id
            )
            
            return JSONResponse(
                status_code=500,
                content={"detail": "An internal server error occurred."}
            )

def get_sanitized_request_data(request: Optional[Request]) -> Dict[str, Any]:
    """Extracts serializable data from a Starlette/FastAPI Request object."""
    if not request:
        return {}
    
    return {
        "method": request.method,
        "path": request.url.path,
        "query_params": str(request.query_params),
        "headers": {k: v for k, v in request.headers.items() if k.lower() not in ['authorization', 'cookie', 'x-api-key']},
        "client_host": request.client.host if request.client else "unknown",
    }