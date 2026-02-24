# Web3 Wallet Analyzer Agent

A multi-chain blockchain wallet analysis agent that takes any public wallet address — EVM, Solana, Bitcoin, or Tron — and delivers a complete transaction report with chain-by-chain breakdowns, USD volume metrics, and AI-powered insights. Built with FastAPI, it exposes REST, A2A (Agent-to-Agent), and MCP (Model Context Protocol) endpoints — making it consumable by humans, applications, and other AI agents.

---

## Live Deployment

| | URL |
|---|---|
| **Base URL** | `https://web3-wallet-analyzer-agent.onrender.com` |
| **API Docs** | `https://web3-wallet-analyzer-agent.onrender.com/docs` |
| **Health Check** | `https://web3-wallet-analyzer-agent.onrender.com/health` |
| **Analyze Wallet** | `https://web3-wallet-analyzer-agent.onrender.com/analyze` |
| **A2A Agent Card** | `https://web3-wallet-analyzer-agent.onrender.com/.well-known/agent.json` |
| **A2A Task Endpoint** | `https://web3-wallet-analyzer-agent.onrender.com/a2a` |
| **MCP Endpoint** | `https://web3-wallet-analyzer-agent.onrender.com/mcp` |

---

## Table of Contents

- [What It Does](#what-it-does)
- [Supported Chains](#supported-chains)
- [Features](#features)
- [Architecture](#architecture)
- [API Reference](#api-reference)
  - [GET /health](#get-health)
  - [POST /analyze](#post-analyze)
  - [GET /.well-known/agent.json](#get-well-knownagentjson)
  - [POST /a2a](#post-a2a)
- [Output Formats](#output-formats)
- [MCP Integration](#mcp-integration)
- [A2A Integration](#a2a-integration)
- [Testing the Live Agent](#testing-the-live-agent)
  - [REST API Tests](#rest-api-tests)
  - [A2A Protocol Tests](#a2a-protocol-tests)
  - [MCP Client Setup](#mcp-client-setup)
- [Local Development](#local-development)
- [Environment Variables](#environment-variables)
- [Deployment](#deployment)
- [Project Structure](#project-structure)
- [Report Fields](#report-fields)
- [Error Handling](#error-handling)

---

## What It Does

You give it a wallet address. It tells you everything about that wallet.

The agent auto-detects whether the address belongs to an EVM chain (Ethereum, Polygon, BSC, etc.), Solana, Bitcoin, or Tron. It then scans **all applicable chains concurrently**, fetches transaction data, converts volumes to USD using live prices, and returns a complete report sorted by the most active chains first.

**Input:** A public wallet address — that's it.

**Output:** Complete wallet intelligence report as JSON, CSV, or Excel.

```
Public Wallet Address (0x... / bc1... / T... / So1...)
                    |
             Address Detection
        (EVM? Solana? Bitcoin? Tron?)
                    |
         Concurrent Chain Scanning
   (8 EVM chains + Solana + Bitcoin + Tron)
                    |
         Live USD Price Conversion
              (CoinGecko)
                    |
    +-------------------------------+
    |  Total Received / Sent / Gas  |
    |  Chain-by-Chain Breakdown     |
    |  Sorted by Top Activity       |
    |  AI-Powered Insights          |
    +-------------------------------+
                    |
        JSON / CSV / Excel Report
```

---

## Supported Chains

| Chain | Type | Native Token | Address Format | API Source |
|---|---|---|---|---|
| **Ethereum** | EVM | ETH | `0x...` (42 chars) | Etherscan V2 |
| **Polygon** | EVM | POL | `0x...` (42 chars) | Etherscan V2 |
| **BNB Chain** | EVM | BNB | `0x...` (42 chars) | Etherscan V2 |
| **Arbitrum** | EVM | ETH | `0x...` (42 chars) | Etherscan V2 |
| **Optimism** | EVM | ETH | `0x...` (42 chars) | Etherscan V2 |
| **Avalanche** | EVM | AVAX | `0x...` (42 chars) | Etherscan V2 |
| **Base** | EVM | ETH | `0x...` (42 chars) | Etherscan V2 |
| **Fantom** | EVM | FTM | `0x...` (42 chars) | Etherscan V2 |
| **Solana** | Solana | SOL | Base58 (32-44 chars) | Solana RPC |
| **Bitcoin** | Bitcoin | BTC | `1...` / `3...` / `bc1...` | Blockchain.info |
| **Tron** | Tron | TRX | `T...` (34 chars) | TronGrid |

> **EVM addresses are scanned across all 8 chains concurrently.** If your address has activity on Ethereum, Polygon, and Arbitrum but not the others, only chains with actual transactions appear in the report.

---

## Features

- **Auto address detection** — Automatically identifies EVM, Solana, Bitcoin, or Tron from the address format
- **Multi-chain concurrent scanning** — All applicable chains scanned in parallel for fast results
- **11 chains supported** — 8 EVM chains + Solana + Bitcoin + Tron
- **Live USD conversion** — All volumes converted to USD using real-time CoinGecko prices
- **Sorted by activity** — Results always sorted by transaction count, top chains first
- **Three output formats** — JSON (API), CSV (download), Excel (download with formatted sheets)
- **AI-powered insights** — Optional natural language analysis of wallet behavior, patterns, and risk indicators
- **Triple AI provider support** — Anthropic Claude, OpenAI GPT, or Google Gemini for the AI insights layer
- **REST API** — Standard HTTP endpoint at `/analyze`
- **A2A Protocol** — Google Agent-to-Agent protocol for agent-to-agent communication
- **MCP Protocol** — Model Context Protocol for Claude Desktop, Cursor, Windsurf, and other MCP clients
- **Interactive docs** — Swagger UI at `/docs`

---

## Architecture

```
+-------------------------------------------------------------+
|                     FastAPI Application                       |
|                                                              |
|  +----------+  +----------+  +-------------+  +-----------+ |
|  | /analyze |  |  /a2a    |  | /.well-     |  |   /mcp    | |
|  | REST API |  |  A2A     |  |  known/     |  |   MCP     | |
|  +----------+  +----------+  | agent.json  |  +-----------+ |
|                               +-------------+                |
|                        |                                     |
|                 WalletAnalyzer                                |
|                        |                                     |
|    +-------------------------------------------+             |
|    |         Chain Providers (concurrent)       |             |
|    |  +-------+ +-------+ +-------+ +-------+  |             |
|    |  |  EVM  | |Solana | |Bitcoin| | Tron  |  |             |
|    |  | x 8   | |  RPC  | | .info | | Grid  |  |             |
|    |  +-------+ +-------+ +-------+ +-------+  |             |
|    +-------------------------------------------+             |
|                        |                                     |
|              CoinGecko Price API                             |
|                        |                                     |
|            WalletInsightsAgent (AI)                           |
|    +-------------------------------------------+             |
|    |  Anthropic Claude | OpenAI | Google Gemini |             |
|    +-------------------------------------------+             |
|                        |                                     |
|    +-------------------------------------------+             |
|    |  Export: JSON | CSV | Excel (2 sheets)     |             |
|    +-------------------------------------------+             |
+-------------------------------------------------------------+
```

**File breakdown:**

| File | Responsibility |
|---|---|
| `main.py` | FastAPI app — REST, A2A, MCP endpoints, lifespan management |
| `wallet_analyzer.py` | Multi-chain orchestrator — concurrent scanning, aggregation, sorting |
| `chain_providers.py` | Chain-specific API providers — EVM (Etherscan V2), Solana RPC, Bitcoin, Tron |
| `agent.py` | AI insights agent — Anthropic / OpenAI / Gemini provider support |
| `models.py` | Pydantic data models — Transaction, ChainSummary, WalletReport, API schemas |
| `prompts.py` | AI prompt templates for wallet analysis |
| `exports.py` | CSV and Excel report generation |
| `utils.py` | Address detection, chain mapping, unit conversions |

---

## API Reference

### GET /health

Returns the current status of the agent.

**Request**
```bash
curl https://web3-wallet-analyzer-agent.onrender.com/health
```

**Response**
```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

---

### POST /analyze

The main endpoint. Send a wallet address and get a complete analysis.

**URL:** `https://web3-wallet-analyzer-agent.onrender.com/analyze`
**Method:** `POST`
**Content-Type:** `application/json`

**Request Body**

| Field | Type | Required | Description |
|---|---|---|---|
| `address` | string | Yes | Public wallet address (EVM / Solana / Bitcoin / Tron) |
| `chains` | string[] | No | Specific chain IDs to scan. Auto-detected if omitted. |

**Query Parameters**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `format` | string | `json` | Output format: `json` \| `csv` \| `excel` |
| `include_insights` | boolean | `true` | Include AI-powered analysis in the report |

---

**Example 1 — Bitcoin wallet, JSON response**

```bash
curl -X POST "https://web3-wallet-analyzer-agent.onrender.com/analyze?format=json" \
  -H "Content-Type: application/json" \
  -d '{"address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"}'
```

```json
{
  "success": true,
  "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
  "processing_time_ms": 562,
  "report": {
    "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
    "address_type": "bitcoin",
    "chains_analyzed": ["bitcoin"],
    "chains_with_activity": ["bitcoin"],
    "total_transactions": 56755,
    "total_received_usd": 6749364.71,
    "total_sent_usd": 0.0,
    "net_flow_usd": 6749364.71,
    "total_gas_spent_usd": 0.0,
    "wallet_age_days": 21,
    "chain_summaries": [
      {
        "chain": "bitcoin",
        "chain_name": "Bitcoin",
        "native_symbol": "BTC",
        "total_transactions": 56755,
        "total_received": 107.11067091,
        "total_received_usd": 6749364.71,
        "total_sent": 0.0,
        "total_sent_usd": 0.0,
        "first_transaction_date": "2026-02-02T11:33:04",
        "last_transaction_date": "2026-02-24T06:50:59"
      }
    ],
    "top_chains_by_transactions": [
      {
        "chain": "Bitcoin",
        "transactions": 56755,
        "volume_usd": 6749364.71
      }
    ],
    "ai_insights": "## WALLET OVERVIEW\nThis is a Bitcoin-only wallet..."
  }
}
```

---

**Example 2 — EVM wallet (scans 8 chains)**

```bash
curl -X POST "https://web3-wallet-analyzer-agent.onrender.com/analyze?format=json" \
  -H "Content-Type: application/json" \
  -d '{"address": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"}'
```

This scans Ethereum, Polygon, BSC, Arbitrum, Optimism, Avalanche, Base, and Fantom concurrently and returns only chains with activity.

---

**Example 3 — Download CSV report**

```bash
curl -X POST "https://web3-wallet-analyzer-agent.onrender.com/analyze?format=csv&include_insights=false" \
  -H "Content-Type: application/json" \
  -d '{"address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"}' \
  -o wallet_report.csv
```

---

**Example 4 — Download Excel report**

```bash
curl -X POST "https://web3-wallet-analyzer-agent.onrender.com/analyze?format=excel" \
  -H "Content-Type: application/json" \
  -d '{"address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"}' \
  -o wallet_report.xlsx
```

Downloads a formatted Excel workbook with two sheets:
- **Summary** — Address, type, totals, wallet age, key metrics
- **Chain Breakdown** — Per-chain transaction counts, volumes, gas, activity dates

---

**Example 5 — Scan specific chains only**

```bash
curl -X POST "https://web3-wallet-analyzer-agent.onrender.com/analyze?format=json" \
  -H "Content-Type: application/json" \
  -d '{"address": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045", "chains": ["ethereum", "polygon", "arbitrum"]}'
```

---

### GET /.well-known/agent.json

Returns the A2A Agent Card — a standardized description of this agent's identity, capabilities, and skills. Other AI agents use this endpoint to discover and understand how to interact with this agent.

**Request**
```bash
curl https://web3-wallet-analyzer-agent.onrender.com/.well-known/agent.json
```

**Response**
```json
{
  "name": "Web3 Wallet Analyzer Agent",
  "description": "Multi-chain blockchain wallet analyzer. Provide any public wallet address (EVM, Solana, Bitcoin, Tron) and receive comprehensive transaction analysis, chain breakdowns, volume metrics, and AI-powered insights.",
  "url": "https://web3-wallet-analyzer-agent.onrender.com",
  "version": "1.0.0",
  "capabilities": {
    "streaming": false,
    "pushNotifications": false
  },
  "skills": [
    {
      "id": "analyze_wallet",
      "name": "Analyze Wallet",
      "tags": ["web3", "blockchain", "wallet", "analytics", "defi", "crypto", "ethereum", "solana", "bitcoin"]
    }
  ]
}
```

---

### POST /a2a

Google Agent-to-Agent (A2A) Protocol endpoint. Accepts JSON-RPC 2.0 requests. Other AI agents send wallet addresses here to invoke analysis.

**URL:** `https://web3-wallet-analyzer-agent.onrender.com/a2a`
**Method:** `POST`
**Content-Type:** `application/json`

**Request Body**
```json
{
  "jsonrpc": "2.0",
  "method": "tasks/send",
  "id": "1",
  "params": {
    "id": "task-uuid-here",
    "message": {
      "role": "user",
      "parts": [
        {
          "type": "text",
          "text": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        }
      ]
    }
  }
}
```

**Example**
```bash
curl -X POST https://web3-wallet-analyzer-agent.onrender.com/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks/send",
    "id": "1",
    "params": {
      "id": "task-wallet-001",
      "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"}]
      }
    }
  }'
```

**Response**
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "result": {
    "id": "task-wallet-001",
    "status": {
      "state": "completed",
      "timestamp": "2026-02-24T07:07:03Z"
    },
    "artifacts": [
      {
        "name": "wallet_report",
        "description": "Multi-chain wallet analysis for 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
        "parts": [
          {
            "type": "data",
            "data": {
              "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
              "address_type": "bitcoin",
              "total_transactions": 56755,
              "total_received_usd": 6749364.71,
              "chain_summaries": ["..."]
            }
          }
        ]
      }
    ]
  }
}
```

---

## Output Formats

| Format | How to request | Use case |
|---|---|---|
| `json` | `?format=json` (default) | Application integrations, APIs, dashboards |
| `csv` | `?format=csv` | Data analysts, spreadsheet import, further processing |
| `excel` | `?format=excel` | Business reports, portfolio review, accounting |

---

## MCP Integration

MCP (Model Context Protocol) lets AI assistants like Claude Desktop use this agent as a native tool — the assistant can analyze any wallet address during a conversation without the user writing any code.

### Connect via Remote URL

Add the following to your MCP client configuration file:

**Claude Desktop** — `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "web3-wallet-analyzer": {
      "url": "https://web3-wallet-analyzer-agent.onrender.com/mcp"
    }
  }
}
```

**Cursor** — `.cursor/mcp.json`

```json
{
  "mcpServers": {
    "web3-wallet-analyzer": {
      "url": "https://web3-wallet-analyzer-agent.onrender.com/mcp"
    }
  }
}
```

**Windsurf** — `~/.codeium/windsurf/mcp_config.json`

```json
{
  "mcpServers": {
    "web3-wallet-analyzer": {
      "url": "https://web3-wallet-analyzer-agent.onrender.com/mcp"
    }
  }
}
```

Restart your client. You can then say:
> *"Analyze this wallet: 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"*
> *"Show me the transaction report for this Bitcoin address: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"*
> *"Which chains does this wallet use the most?"*

The assistant will call this agent automatically.

**Exposed MCP Tools:**

| Tool | Description |
|---|---|
| `analyze_wallet_mcp` | Analyze a blockchain wallet across multiple chains. Takes an address and optional chain list. Returns full report. |

---

## A2A Integration

This agent implements the [Google Agent-to-Agent (A2A) Protocol](https://google.github.io/A2A). Other AI agents can:

1. **Discover** the agent via `GET /.well-known/agent.json`
2. **Send tasks** via `POST /a2a` using JSON-RPC 2.0
3. **Receive structured results** directly in the response (stateless — no polling needed)

**Supported A2A methods:**

| Method | Description |
|---|---|
| `tasks/send` | Send a wallet address for analysis and receive the full report immediately |

---

## Testing the Live Agent

Copy-paste these commands into your terminal to test every endpoint on the live deployment.

### REST API Tests

```bash
# 1. Health check
curl -s https://web3-wallet-analyzer-agent.onrender.com/health

# 2. Analyze a Bitcoin wallet (Satoshi's genesis address)
curl -s -X POST "https://web3-wallet-analyzer-agent.onrender.com/analyze?format=json&include_insights=false" \
  -H "Content-Type: application/json" \
  -d '{"address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"}'

# 3. Analyze an EVM wallet (scans 8 chains concurrently)
curl -s -X POST "https://web3-wallet-analyzer-agent.onrender.com/analyze?format=json&include_insights=false" \
  -H "Content-Type: application/json" \
  -d '{"address": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"}'

# 4. Analyze a Solana wallet
curl -s -X POST "https://web3-wallet-analyzer-agent.onrender.com/analyze?format=json&include_insights=false" \
  -H "Content-Type: application/json" \
  -d '{"address": "So11111111111111111111111111111111111111112"}'

# 5. Download CSV report
curl -s -X POST "https://web3-wallet-analyzer-agent.onrender.com/analyze?format=csv&include_insights=false" \
  -H "Content-Type: application/json" \
  -d '{"address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"}' \
  -o wallet_report.csv

# 6. Download Excel report
curl -s -X POST "https://web3-wallet-analyzer-agent.onrender.com/analyze?format=excel&include_insights=false" \
  -H "Content-Type: application/json" \
  -d '{"address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"}' \
  -o wallet_report.xlsx

# 7. Scan only specific chains
curl -s -X POST "https://web3-wallet-analyzer-agent.onrender.com/analyze?format=json&include_insights=false" \
  -H "Content-Type: application/json" \
  -d '{"address": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045", "chains": ["ethereum", "polygon"]}'

# 8. With AI insights enabled (requires AI provider configured on server)
curl -s -X POST "https://web3-wallet-analyzer-agent.onrender.com/analyze?format=json&include_insights=true" \
  -H "Content-Type: application/json" \
  -d '{"address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"}'
```

### A2A Protocol Tests

```bash
# 1. Discover the agent
curl -s https://web3-wallet-analyzer-agent.onrender.com/.well-known/agent.json

# 2. Send a task via A2A (Bitcoin address)
curl -s -X POST https://web3-wallet-analyzer-agent.onrender.com/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks/send",
    "id": "1",
    "params": {
      "id": "task-btc-001",
      "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"}]
      }
    }
  }'

# 3. Send a task via A2A (EVM address)
curl -s -X POST https://web3-wallet-analyzer-agent.onrender.com/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks/send",
    "id": "2",
    "params": {
      "id": "task-evm-001",
      "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"}]
      }
    }
  }'

# 4. Test invalid method (should return error)
curl -s -X POST https://web3-wallet-analyzer-agent.onrender.com/a2a \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tasks/get", "id": "3", "params": {}}'
```

### MCP Client Setup

**Claude Desktop:**

1. Open `~/Library/Application Support/Claude/claude_desktop_config.json`
2. Add:
```json
{
  "mcpServers": {
    "web3-wallet-analyzer": {
      "url": "https://web3-wallet-analyzer-agent.onrender.com/mcp"
    }
  }
}
```
3. Restart Claude Desktop
4. Ask: *"Analyze this wallet: 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"*

**Cursor:**

1. Create or edit `.cursor/mcp.json` in your project root
2. Add:
```json
{
  "mcpServers": {
    "web3-wallet-analyzer": {
      "url": "https://web3-wallet-analyzer-agent.onrender.com/mcp"
    }
  }
}
```
3. Restart Cursor
4. Ask: *"What chains does this wallet use? 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"*

---

## Local Development

### Prerequisites

- Python 3.10+
- Etherscan API key (free — one key covers all 8 EVM chains via V2 API)
- AI provider API key (Anthropic / OpenAI / Gemini) — optional, only needed for AI insights

### Setup

```bash
# 1. Navigate to the agent folder
cd agents/web3-wallet-analyzer

# 2. Create virtual environment
python3.12 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — add your Etherscan API key and optionally an AI provider key
```

### Run

```bash
python main.py
# Starts on http://localhost:8000
# Hot reload enabled in development mode
```

### Test

```bash
# Health check
curl http://localhost:8000/health

# Analyze a Bitcoin wallet (no API key needed — blockchain.info is free)
curl -s -X POST "http://localhost:8000/analyze?format=json&include_insights=false" \
  -H "Content-Type: application/json" \
  -d '{"address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"}'

# Analyze an EVM wallet (needs ETHERSCAN_API_KEY in .env)
curl -s -X POST "http://localhost:8000/analyze?format=json&include_insights=false" \
  -H "Content-Type: application/json" \
  -d '{"address": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"}'

# Download CSV
curl -s -X POST "http://localhost:8000/analyze?format=csv&include_insights=false" \
  -H "Content-Type: application/json" \
  -d '{"address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"}' \
  -o wallet_report.csv

# Download Excel
curl -s -X POST "http://localhost:8000/analyze?format=excel&include_insights=false" \
  -H "Content-Type: application/json" \
  -d '{"address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"}' \
  -o wallet_report.xlsx
```

### Run with Docker

```bash
# Build and start
docker compose up --build

# Agent available at http://localhost:8000
```

---

## Environment Variables

Copy `.env.example` to `.env` and configure:

```env
# ── AI Provider (optional — only needed for AI insights) ──────────────────────
AI_PROVIDER=anthropic             # anthropic | openai | gemini

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-sonnet-4-6

# OpenAI (alternative)
# OPENAI_API_KEY=sk-...
# OPENAI_MODEL=gpt-4o

# Gemini (alternative)
# GEMINI_API_KEY=...
# GEMINI_MODEL=gemini-2.0-flash

# ── EVM Chains (one key covers all 8 chains) ─────────────────────────────────
ETHERSCAN_API_KEY=                # https://etherscan.io/apis (free tier)

# ── Non-EVM Chains ───────────────────────────────────────────────────────────
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
TRONGRID_API_KEY=                 # https://www.trongrid.io/ (optional)

# ── Server ────────────────────────────────────────────────────────────────────
HOST=0.0.0.0
PORT=8000
APP_ENV=development
```

| Variable | Required | Default | Description |
|---|---|---|---|
| `AI_PROVIDER` | No | `anthropic` | AI provider for insights: `anthropic`, `openai`, or `gemini` |
| `ANTHROPIC_API_KEY` | If using Claude insights | — | Anthropic API key |
| `CLAUDE_MODEL` | No | `claude-sonnet-4-6` | Claude model ID |
| `OPENAI_API_KEY` | If using OpenAI insights | — | OpenAI API key |
| `OPENAI_MODEL` | No | `gpt-4o` | OpenAI model ID |
| `GEMINI_API_KEY` | If using Gemini insights | — | Google Gemini API key |
| `GEMINI_MODEL` | No | `gemini-2.0-flash` | Gemini model ID |
| `ETHERSCAN_API_KEY` | For EVM chains | — | Etherscan V2 API key (one key = 8 chains) |
| `SOLANA_RPC_URL` | No | Public RPC | Solana RPC endpoint |
| `TRONGRID_API_KEY` | No | — | TronGrid API key (improves rate limits) |
| `APP_ENV` | No | `development` | `development` enables hot reload |
| `PORT` | No | `8000` | Server port |

> **Note:** Bitcoin analysis works without any API keys. EVM chains require a free Etherscan API key. Solana works with the default public RPC but has rate limits. AI insights are optional.

---

## Deployment

### Render (Recommended)

1. Push code to a GitHub repository
2. Go to [render.com](https://render.com) -> **New** -> **Web Service**
3. Connect your GitHub repository
4. Render auto-detects the `Dockerfile` and configures the build
5. Add environment variables under **Settings -> Environment**:
   - `ETHERSCAN_API_KEY` = your free Etherscan key
   - `AI_PROVIDER` = `anthropic` (optional, for AI insights)
   - `ANTHROPIC_API_KEY` = your key (optional)
6. Click **Deploy**

> **Free tier note:** Render free tier spins down services after 15 minutes of inactivity. The first request after a sleep period may take up to 30 seconds. Upgrade to a paid plan for always-on availability.

### Railway

```bash
npm install -g @railway/cli
railway login && railway init && railway up
railway variables set ETHERSCAN_API_KEY=your-key
railway variables set AI_PROVIDER=anthropic
railway variables set ANTHROPIC_API_KEY=sk-ant-...
```

### Fly.io

```bash
fly launch
fly secrets set ETHERSCAN_API_KEY=your-key AI_PROVIDER=anthropic ANTHROPIC_API_KEY=sk-ant-...
fly deploy
```

---

## Project Structure

```
web3-wallet-analyzer/
├── main.py                    # FastAPI app — REST, A2A, MCP endpoints
├── wallet_analyzer.py         # Multi-chain orchestrator — concurrent scanning, aggregation
├── chain_providers.py         # Chain providers — EVM (Etherscan V2), Solana, Bitcoin, Tron
├── agent.py                   # AI insights agent — Claude / OpenAI / Gemini
├── models.py                  # Pydantic models — Transaction, ChainSummary, WalletReport
├── prompts.py                 # AI prompt templates for wallet analysis
├── exports.py                 # CSV and Excel report generation
├── utils.py                   # Address detection, chain mapping, unit conversions
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Container definition
├── docker-compose.yml         # Local Docker Compose setup
├── .env.example               # Environment variable template
├── .gitignore
├── LICENSE
└── logo.svg                   # Agent logo
```

---

## Report Fields

Every successful analysis returns a `WalletReport` with these fields:

### Top-Level Summary

| Field | Type | Description |
|---|---|---|
| `address` | string | The wallet address that was analyzed |
| `address_type` | string | Detected type: `evm`, `solana`, `bitcoin`, or `tron` |
| `chains_analyzed` | string[] | All chain IDs that were scanned |
| `chains_with_activity` | string[] | Only chains where transactions were found |
| `total_transactions` | int | Sum of transactions across all active chains |
| `total_received_usd` | float | Total value received across all chains in USD |
| `total_sent_usd` | float | Total value sent across all chains in USD |
| `net_flow_usd` | float | Received minus Sent — positive means net accumulator |
| `total_gas_spent_usd` | float | Total gas fees paid across all EVM chains in USD |
| `first_activity` | datetime | Earliest transaction across all chains |
| `last_activity` | datetime | Most recent transaction across all chains |
| `wallet_age_days` | int | Days since first transaction |
| `ai_insights` | string | AI-generated analysis (if `include_insights=true`) |

### Per-Chain Summary (`chain_summaries[]`)

Sorted by `total_transactions` descending (most active chain first).

| Field | Type | Description |
|---|---|---|
| `chain` | string | Chain ID (e.g. `ethereum`, `bitcoin`) |
| `chain_name` | string | Display name (e.g. `Ethereum`, `Bitcoin`) |
| `native_symbol` | string | Native token symbol (e.g. `ETH`, `BTC`) |
| `total_transactions` | int | Total transactions on this chain |
| `incoming_transactions` | int | Transactions received |
| `outgoing_transactions` | int | Transactions sent |
| `total_received` | float | Total received in native token |
| `total_received_usd` | float | Total received in USD |
| `total_sent` | float | Total sent in native token |
| `total_sent_usd` | float | Total sent in USD |
| `total_gas_spent` | float | Gas fees in native token |
| `total_gas_spent_usd` | float | Gas fees in USD |
| `first_transaction_date` | datetime | First transaction on this chain |
| `last_transaction_date` | datetime | Last transaction on this chain |
| `unique_contracts_interacted` | int | Number of unique contract addresses interacted with |
| `token_transfers_count` | int | Number of ERC-20 / token transfers |

---

## Error Handling

All errors from the `/analyze` endpoint return a consistent JSON structure:

```json
{
  "success": false,
  "address": "invalid-address",
  "error": "Unrecognized address format: invalid-address",
  "processing_time_ms": 0
}
```

**Common errors:**

| Situation | HTTP Status | Error message |
|---|---|---|
| Invalid address format | `422` | `Unrecognized address format: ...` |
| No supported chains | `422` | `No supported chains for address type: unknown` |
| Chain API failure | `200` | Returns partial results (failed chains are silently skipped) |
| Missing AI key | `200` | AI insights field shows `"AI insights unavailable: ..."` |

**A2A errors follow JSON-RPC 2.0 format:**

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "error": {
    "code": -32602,
    "message": "No text part found. Send a 'text' part containing the wallet address."
  }
}
```

| Code | Meaning |
|---|---|
| `-32700` | Parse error — invalid JSON |
| `-32601` | Method not found |
| `-32602` | Invalid params — missing wallet address |
| `-32603` | Internal error — analysis failed |
