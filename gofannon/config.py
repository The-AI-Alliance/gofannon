import os
from dotenv import load_dotenv
import logging


class ToolConfig:
    _instance = None

    def __init__(self):
        load_dotenv()
        self.config = {
            'github_api_key': os.getenv('GITHUB_API_KEY'),
            'deepinfra_api_key': os.getenv('DEEPINFRA_API_KEY'),
            'arxiv_api_key': os.getenv('ARXIV_API_KEY'),
            'google_search_api_key': os.getenv('GOOGLE_SEARCH_API_KEY'),
            'google_search_engine_id': os.getenv('GOOGLE_SEARCH_ENGINE_ID')
        }

    @classmethod
    def get(cls, key):
        if not cls._instance:
            cls._instance = ToolConfig()
        return cls._instance.config.get(key)

class FunctionRegistry:
    _tools = {}

    @classmethod
    def register(cls, tool_class):
        cls._tools[tool_class().definition['function']['name']] = tool_class
        return tool_class

    @classmethod
    def get_tools(cls):
        return [cls._tools[name]().definition for name in cls._tools]

def setup_logging():
    """Configure logging for the gofannon package."""
    logger = logging.getLogger('')
    log_level = os.getenv('GOFANNON_LOG_LEVEL', 'WARNING').upper()
    level = getattr(logging, log_level, logging.WARNING)

    # Clear existing handlers if any
    if logger.handlers:
        for handler in logger.handlers:
            logger.removeHandler(handler)

            # Configure new handler
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    logger.setLevel(level)
    logger.propagate = False

# Initialize logging when config is imported
setup_logging()
