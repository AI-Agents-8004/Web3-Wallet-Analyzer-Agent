import io
import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Literal, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastmcp import FastMCP

load_dotenv()

from agent import WalletInsightsAgent
from exports import to_csv, to_excel, to_json
from models import AnalyzeRequest, AnalyzeResponse, HealthResponse, WalletReport
from wallet_analyzer import WalletAnalyzer


# ── MCP Server (mounted at /sse) ─────────────────────────────────────────────

mcp = FastMCP(
    name="Web3 Wallet Analyzer Agent",
    instructions=(
        "Analyzes blockchain wallets across multiple chains (EVM, Solana, Bitcoin, Tron). "
        "Provide a public wallet address and get a comprehensive transaction analysis report "
        "with chain breakdowns, volume metrics, and AI-powered insights."
    ),
)


@mcp.tool()
async def analyze_wallet_mcp(
    address: str, chains: Optional[list[str]] = None
) -> dict:
    """
    Analyze a blockchain wallet across multiple chains.

    Args:
        address: Public wallet address (EVM 0x..., Solana, Bitcoin, or Tron).
        chains:  Optional list of chain IDs to analyze. Auto-detected if omitted.

    Returns:
        Complete wallet analysis with chain breakdowns and AI insights.
    """
    report = await analyzer.analyze(address, chains)
    if insights_agent:
        try:
            report.ai_insights = insights_agent.generate_insights(report)
        except Exception as e:
            report.ai_insights = f"AI insights unavailable: {e}"
    return report.model_dump()


# ── Lifespan ──────────────────────────────────────────────────────────────────

analyzer: WalletAnalyzer | None = None
insights_agent: WalletInsightsAgent | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global analyzer, insights_agent
    analyzer = WalletAnalyzer()
    try:
        insights_agent = WalletInsightsAgent()
    except Exception as e:
        print(f"  [!] AI insights disabled: {e}")
        insights_agent = None
    print("  Web3 Wallet Analyzer Agent ready")
    yield
    print("  Shutting down.")


# ── App ───────────────────────────────────────────────────────────────────────

SUPPORTED_CHAINS = [
    "Ethereum", "Polygon", "BNB Chain", "Arbitrum", "Optimism",
    "Avalanche", "Base", "Fantom", "Solana", "Bitcoin", "Tron",
]

app = FastAPI(
    title="Web3 Wallet Analyzer Agent",
    description=(
        "Multi-chain blockchain wallet analysis agent. Supports EVM (Ethereum, Polygon, "
        "BSC, Arbitrum, Optimism, Avalanche, Base, Fantom), Solana, Bitcoin, and Tron.\n\n"
        "Provide any public wallet address and receive a complete transaction analysis "
        "report with chain breakdowns, volume metrics, and AI-powered insights.\n\n"
        "Exposes **REST** (`/analyze`), **MCP** (`/sse`), and **A2A** (`/a2a`) endpoints."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/mcp", mcp.http_app())


# ── Info ──────────────────────────────────────────────────────────────────────


@app.get("/", tags=["Info"])
def root(request: Request):
    base = str(request.base_url).rstrip("/")
    return {
        "name": "Web3 Wallet Analyzer Agent",
        "version": "1.0.0",
        "supported_chains": SUPPORTED_CHAINS,
        "endpoints": {
            "docs": f"{base}/docs",
            "health": f"{base}/health",
            "analyze": f"{base}/analyze",
            "a2a_card": f"{base}/.well-known/agent.json",
            "a2a_tasks": f"{base}/a2a",
            "mcp": f"{base}/mcp",
        },
    }


@app.get("/health", response_model=HealthResponse, tags=["Info"])
def health():
    return HealthResponse(status="ok", version="1.0.0")


# ── Core: Analyze Wallet ──────────────────────────────────────────────────────


@app.post("/analyze", tags=["Wallet"])
async def analyze_wallet(
    req: AnalyzeRequest,
    format: Literal["json", "csv", "excel"] = Query(
        default="json",
        description="Output format: json (default) | csv | excel",
    ),
    include_insights: bool = Query(
        default=True,
        description="Include AI-powered insights in the report",
    ),
):
    """
    Analyze a blockchain wallet address.

    Supports:
    - **EVM** (0x...): Ethereum, Polygon, BSC, Arbitrum, Optimism, Avalanche, Base, Fantom
    - **Solana**: Base58 addresses
    - **Bitcoin**: Legacy (1...), P2SH (3...), Bech32 (bc1...)
    - **Tron**: T... addresses

    Auto-detects the address type and scans all applicable chains concurrently.
    Results are sorted by transaction count (top chains first).
    """
    start = time.time()

    try:
        report = await analyzer.analyze(req.address, req.chains)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        return AnalyzeResponse(
            success=False, address=req.address, error=str(e),
            processing_time_ms=elapsed,
        )

    # AI insights
    if include_insights and insights_agent and report.chains_with_activity:
        try:
            report.ai_insights = insights_agent.generate_insights(report)
        except Exception as e:
            report.ai_insights = f"AI insights generation failed: {e}"

    elapsed = int((time.time() - start) * 1000)
    short = req.address[:12]

    if format == "json":
        return AnalyzeResponse(
            success=True, address=req.address, report=report,
            processing_time_ms=elapsed,
        )

    if format == "csv":
        return StreamingResponse(
            content=io.BytesIO(to_csv(report)),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="wallet_{short}_report.csv"'
            },
        )

    if format == "excel":
        return StreamingResponse(
            content=io.BytesIO(to_excel(report)),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="wallet_{short}_report.xlsx"'
            },
        )


# ── A2A: Agent Card ──────────────────────────────────────────────────────────


@app.get("/.well-known/agent.json", tags=["A2A"])
def agent_card(request: Request):
    """Google A2A Agent Card — describes this agent's identity and capabilities."""
    base = str(request.base_url).rstrip("/")
    return JSONResponse({
        "name": "Web3 Wallet Analyzer Agent",
        "description": (
            "Multi-chain blockchain wallet analyzer. Provide any public wallet address "
            "(EVM, Solana, Bitcoin, Tron) and receive comprehensive transaction analysis, "
            "chain breakdowns, volume metrics, and AI-powered insights."
        ),
        "url": base,
        "version": "1.0.0",
        "provider": {
            "organization": "AI Agents Marketplace",
            "url": base,
        },
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "stateTransitionHistory": False,
        },
        "authentication": {"schemes": []},
        "defaultInputModes": ["application/json"],
        "defaultOutputModes": ["application/json"],
        "skills": [
            {
                "id": "analyze_wallet",
                "name": "Analyze Wallet",
                "description": (
                    "Analyze a public blockchain wallet across multiple chains. "
                    "Returns transaction counts, received/sent volumes in USD, gas costs, "
                    "chain-by-chain breakdown sorted by activity, and AI-generated insights."
                ),
                "tags": [
                    "web3", "blockchain", "wallet", "analytics",
                    "defi", "crypto", "ethereum", "solana", "bitcoin",
                ],
                "examples": [
                    "Analyze this Ethereum wallet: 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
                    "Show me the transaction history for this Bitcoin address",
                    "Which chains does this wallet use the most?",
                    "Give me a full report on this Solana wallet",
                ],
                "inputModes": ["application/json"],
                "outputModes": ["application/json"],
            }
        ],
    })


# ── A2A: JSON-RPC Task Endpoint ──────────────────────────────────────────────


@app.post("/a2a", tags=["A2A"])
async def a2a_endpoint(request: Request):
    """
    Google A2A Protocol — JSON-RPC 2.0 task endpoint.

    Send a task with a wallet address (as text part) and receive the analysis report.

    Example request:
    ```json
    {
      "jsonrpc": "2.0",
      "method": "tasks/send",
      "id": "1",
      "params": {
        "id": "task-uuid",
        "message": {
          "role": "user",
          "parts": [{"type": "text", "text": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"}]
        }
      }
    }
    ```
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({
            "jsonrpc": "2.0", "id": None,
            "error": {"code": -32700, "message": "Parse error"},
        })

    rpc_id = body.get("id")
    method = body.get("method", "")
    params = body.get("params", {})

    def rpc_error(code: int, message: str):
        return JSONResponse({
            "jsonrpc": "2.0", "id": rpc_id,
            "error": {"code": code, "message": message},
        })

    if method != "tasks/send":
        return rpc_error(-32601, f"Method '{method}' not supported. Use 'tasks/send'.")

    # Extract wallet address from text part
    parts = params.get("message", {}).get("parts", [])
    text_part = next(
        (p.get("text", "") for p in parts if p.get("type") == "text"), None
    )

    if not text_part:
        return rpc_error(
            -32602,
            "No text part found. Send a 'text' part containing the wallet address.",
        )

    address = text_part.strip()

    try:
        report = await analyzer.analyze(address)
    except Exception as e:
        return rpc_error(-32603, f"Analysis failed: {e}")

    if insights_agent and report.chains_with_activity:
        try:
            report.ai_insights = insights_agent.generate_insights(report)
        except Exception:
            pass

    task_id = params.get("id", str(uuid.uuid4()))

    return JSONResponse({
        "jsonrpc": "2.0",
        "id": rpc_id,
        "result": {
            "id": task_id,
            "status": {
                "state": "completed",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
            "artifacts": [
                {
                    "name": "wallet_report",
                    "description": f"Multi-chain wallet analysis for {address}",
                    "parts": [
                        {
                            "type": "data",
                            "data": json.loads(
                                json.dumps(report.model_dump(), default=str)
                            ),
                        }
                    ],
                }
            ],
        },
    })


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("APP_ENV", "development") == "development",
    )
