# BTC Context MCP

This MCP server is designed to be used alongside charting apps such as `TickerSage`.

Recommended split:

- `TickerSage`: K-lines, chart structure, technical overlays
- `BTC Context MCP`: derivatives, liquidity, macro, regulatory, sentiment, and on-chain context

## Install

```powershell
py -m pip install -r requirements-gateway.txt
```

## Run

```powershell
py run_mcp_server.py
```

For Render, the server now automatically respects Render's `PORT` environment variable, so you do not need to hard-code a public port.

## Environment variables

Add these values to `.env` as needed:

```env
MCP_HOST=0.0.0.0
MCP_PORT=8001
MCP_PUBLIC_BASE_URL=https://your-public-mcp-domain.example.com
MCP_PATH=/mcp
MCP_INCLUDE_OKX_LIQUIDITY=true
```

## Render

You can deploy this as a separate Render Web Service.

Recommended settings:

- Build Command: `pip install -r requirements-gateway.txt`
- Start Command: `python run_mcp_server.py`

Or use:

- [render-mcp.yaml](D:/crypto/btc_mvp/render-mcp.yaml)

## Tools

- `get_full_btc_context`
- `get_derivatives_context`
- `get_liquidity_context`
- `get_macro_context`
- `get_regulatory_context`
- `get_sentiment_chain_context`
