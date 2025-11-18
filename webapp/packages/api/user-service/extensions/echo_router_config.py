from config.routes_config import RouterConfig

ROUTER_CONFIG_MODE = "append"
ROUTER_CONFIGS = [
    {
        "router": "extensions.echo_router:router",
        "prefix": "/extensions",  # becomes /extensions/echo
        "tags": ["echo-demo"],
    }
]