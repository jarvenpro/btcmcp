from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from app.config import _load_dotenv


@dataclass(slots=True)
class McpServerConfig:
    base_dir: Path
    host: str
    port: int
    public_base_url: str
    path: str
    include_okx_liquidity: bool


def load_mcp_server_config() -> McpServerConfig:
    base_dir = Path(__file__).resolve().parents[1]
    _load_dotenv(base_dir / ".env")
    resolved_port = int(os.getenv("PORT", os.getenv("MCP_PORT", "8001")))

    return McpServerConfig(
        base_dir=base_dir,
        host=os.getenv("MCP_HOST", "0.0.0.0"),
        port=resolved_port,
        public_base_url=os.getenv("MCP_PUBLIC_BASE_URL", "https://your-public-mcp-domain.example.com"),
        path=os.getenv("MCP_PATH", "/mcp"),
        include_okx_liquidity=os.getenv("MCP_INCLUDE_OKX_LIQUIDITY", "true").strip().lower() in {"1", "true", "yes", "on"},
    )
