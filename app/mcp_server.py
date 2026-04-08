from __future__ import annotations

import atexit
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from fastmcp import FastMCP

from app.gateway.config import GatewayConfig, load_gateway_config
from app.gateway.http import GatewayHttpClient, UpstreamServiceError
from app.gateway.liquidity import LiquidityContextBuilder
from app.gateway.service import GatewayService
from app.mcp_config import McpServerConfig, load_mcp_server_config


class McpRuntime:
    def __init__(self) -> None:
        self.gateway_config: GatewayConfig = load_gateway_config()
        self.server_config: McpServerConfig = load_mcp_server_config()
        self.http_client = GatewayHttpClient(self.gateway_config)
        self.gateway_service = GatewayService(self.gateway_config, self.http_client)
        self.liquidity_builder = LiquidityContextBuilder(self.http_client)

    def close(self) -> None:
        self.http_client.close()


@lru_cache(maxsize=1)
def get_runtime() -> McpRuntime:
    runtime = McpRuntime()
    atexit.register(runtime.close)
    return runtime


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def capture(source_name: str, builder) -> dict[str, Any]:
    try:
        return {"ok": True, "data": builder()}
    except UpstreamServiceError as exc:
        return {"ok": False, "source": exc.source, "reason": exc.detail}
    except Exception as exc:
        return {"ok": False, "source": source_name, "reason": str(exc)}


def parse_csv(raw: str) -> list[str]:
    return [item.strip().upper() for item in raw.split(",") if item.strip()]


mcp = FastMCP(
    name="BTC Context MCP",
    instructions=(
        "Use this server to complement charting apps such as TickerSage. "
        "It is strongest for derivatives context, liquidity context, macro context, "
        "regulatory context, sentiment, and on-chain context. "
        "Do not use it as the primary K-line renderer."
    ),
)


def _build_derivatives_context(symbol: str = "BTCUSDT", period: str = "1h", limit: int = 12) -> dict[str, Any]:
    runtime = get_runtime()
    symbol = symbol.upper()
    return {
        "generated_at": utc_now_iso(),
        "symbol": symbol,
        "period": period,
        "limit": limit,
        "sources": {
            "binance_derivatives": capture(
                "binance",
                lambda: runtime.gateway_service.get_binance_derivatives_structure(symbol=symbol, period=period, limit=limit),
            ),
            "bybit_validation": capture(
                "bybit",
                lambda: runtime.gateway_service.get_bybit_market_structure(symbol=symbol),
            ),
            "cftc_background": capture(
                "cftc",
                lambda: runtime.gateway_service.get_cftc_bitcoin_cot(exchange="cme", limit=4),
            ),
        },
    }


def _build_macro_context(fred_series: str = "FEDFUNDS,DGS10,UNRATE") -> dict[str, Any]:
    runtime = get_runtime()
    series_ids = parse_csv(fred_series)
    return {
        "generated_at": utc_now_iso(),
        "fred_series": series_ids,
        "sources": {
            "macro_overview": capture(
                "macro",
                lambda: runtime.gateway_service.macro_overview(series_ids),
            ),
            "fed": capture(
                "fed",
                lambda: runtime.gateway_service.get_fed_monetary_feed(limit=5),
            ),
            "treasury": capture(
                "treasury",
                runtime.gateway_service.get_treasury_latest_avg_rates,
            ),
            "bls_cpi": capture(
                "bls",
                lambda: runtime.gateway_service.get_bls_series("CUUR0000SA0", limit=12),
            ),
            "bea_gdp": capture(
                "bea",
                lambda: runtime.gateway_service.get_bea_gdp("LAST5"),
            ),
        },
    }


def _build_regulatory_context(entities: str = "IBIT,FBTC,GBTC") -> dict[str, Any]:
    runtime = get_runtime()
    entity_list = parse_csv(entities)
    return {
        "generated_at": utc_now_iso(),
        "entities": entity_list,
        "sources": {
            "regulatory_overview": capture(
                "regulatory",
                lambda: runtime.gateway_service.regulatory_overview(entity_list),
            ),
            "sec_recent_filings": capture(
                "sec",
                lambda: runtime.gateway_service.get_sec_recent_filings_for_entities(entity_list),
            ),
            "cftc_background": capture(
                "cftc",
                lambda: runtime.gateway_service.get_cftc_bitcoin_cot(exchange="cme", limit=4),
            ),
        },
    }


def _build_sentiment_chain_context(symbol: str = "BTCUSDT") -> dict[str, Any]:
    runtime = get_runtime()
    root_symbol = runtime.gateway_service._extract_root_asset(symbol)  # noqa: SLF001
    sources: dict[str, Any] = {
        "fear_greed": capture("fear_greed", runtime.gateway_service.get_fear_greed_latest),
    }
    if root_symbol == "BTC":
        sources["mempool"] = capture("mempool", runtime.gateway_service.get_mempool_recommended_fees)
    else:
        sources["mempool"] = {"ok": False, "source": "mempool", "reason": "Mempool context is only mapped for BTC."}
    return {
        "generated_at": utc_now_iso(),
        "symbol": symbol.upper(),
        "sources": sources,
    }


@mcp.tool
def get_derivatives_context(
    symbol: str = "BTCUSDT",
    period: str = "1h",
    limit: int = 12,
) -> dict[str, Any]:
    """Get BTC derivatives context from Binance, Bybit, and CFTC."""
    return _build_derivatives_context(symbol=symbol, period=period, limit=limit)


@mcp.tool
async def get_liquidity_context(
    symbol: str = "BTCUSDT",
    depth_limit: int = 100,
    liquidation_sample_seconds: int = 4,
    include_okx: bool | None = None,
) -> dict[str, Any]:
    """Get order-book, wall, and liquidation context across major venues."""
    runtime = get_runtime()
    include_okx = runtime.server_config.include_okx_liquidity if include_okx is None else include_okx
    try:
        return await runtime.liquidity_builder.build_context(
            symbol=symbol.upper(),
            depth_limit=depth_limit,
            liquidation_sample_seconds=liquidation_sample_seconds,
            include_okx=include_okx,
        )
    except UpstreamServiceError as exc:
        return {"ok": False, "source": exc.source, "reason": exc.detail}
    except Exception as exc:
        return {"ok": False, "source": "liquidity", "reason": str(exc)}


@mcp.tool
def get_macro_context(fred_series: str = "FEDFUNDS,DGS10,UNRATE") -> dict[str, Any]:
    """Get macro context including Fed, Treasury, BLS, FRED, and BEA."""
    return _build_macro_context(fred_series=fred_series)


@mcp.tool
def get_regulatory_context(entities: str = "IBIT,FBTC,GBTC") -> dict[str, Any]:
    """Get regulatory and ETF context from SEC and CFTC."""
    return _build_regulatory_context(entities=entities)


@mcp.tool
def get_sentiment_chain_context(symbol: str = "BTCUSDT") -> dict[str, Any]:
    """Get sentiment and on-chain context such as Fear & Greed and mempool fees."""
    return _build_sentiment_chain_context(symbol=symbol)


@mcp.tool
async def get_full_btc_context(
    symbol: str = "BTCUSDT",
    period: str = "1h",
    limit: int = 12,
    fred_series: str = "FEDFUNDS,DGS10,UNRATE",
    entities: str = "IBIT,FBTC,GBTC",
    depth_limit: int = 100,
    liquidation_sample_seconds: int = 4,
    include_okx: bool | None = None,
) -> dict[str, Any]:
    """Get the full non-chart BTC context bundle for use alongside TickerSage."""
    runtime = get_runtime()
    include_okx = runtime.server_config.include_okx_liquidity if include_okx is None else include_okx

    liquidity = await get_liquidity_context(
        symbol=symbol,
        depth_limit=depth_limit,
        liquidation_sample_seconds=liquidation_sample_seconds,
        include_okx=include_okx,
    )

    return {
        "generated_at": utc_now_iso(),
        "symbol": symbol.upper(),
        "sections": {
            "derivatives": _build_derivatives_context(symbol=symbol, period=period, limit=limit),
            "liquidity": liquidity,
            "macro": _build_macro_context(fred_series=fred_series),
            "regulatory": _build_regulatory_context(entities=entities),
            "sentiment_chain": _build_sentiment_chain_context(symbol=symbol),
        },
    }


app = mcp.http_app(path=load_mcp_server_config().path)
