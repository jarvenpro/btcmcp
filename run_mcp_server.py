from __future__ import annotations

from app.mcp_config import load_mcp_server_config
from app.mcp_server import mcp


def main() -> None:
    config = load_mcp_server_config()
    mcp.run(
        transport="streamable-http",
        host=config.host,
        port=config.port,
        path=config.path,
        stateless_http=True,
        show_banner=False,
    )


if __name__ == "__main__":
    main()
