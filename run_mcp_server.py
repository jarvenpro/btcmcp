from __future__ import annotations

import uvicorn

from app.mcp_config import load_mcp_server_config


def main() -> None:
    config = load_mcp_server_config()
    uvicorn.run("app.mcp_server:app", host=config.host, port=config.port, reload=False)


if __name__ == "__main__":
    main()
