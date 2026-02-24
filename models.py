from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────────────────────────


class ChainType(str, Enum):
    ETHEREUM = "ethereum"
    POLYGON = "polygon"
    BSC = "bsc"
    ARBITRUM = "arbitrum"
    OPTIMISM = "optimism"
    AVALANCHE = "avalanche"
    BASE = "base"
    FANTOM = "fantom"
    SOLANA = "solana"
    BITCOIN = "bitcoin"
    TRON = "tron"


class AddressType(str, Enum):
    EVM = "evm"
    SOLANA = "solana"
    BITCOIN = "bitcoin"
    TRON = "tron"
    UNKNOWN = "unknown"


# ── Core Data Models ──────────────────────────────────────────────────────────


class Transaction(BaseModel):
    hash: str
    chain: str
    block_number: Optional[int] = None
    timestamp: Optional[datetime] = None
    from_address: str
    to_address: Optional[str] = None
    value: float = 0.0
    value_usd: float = 0.0
    gas_used: Optional[float] = None
    gas_price: Optional[float] = None
    gas_fee: Optional[float] = None
    gas_fee_usd: Optional[float] = None
    token_symbol: Optional[str] = None
    token_name: Optional[str] = None
    is_incoming: bool = False
    is_token_transfer: bool = False
    method: Optional[str] = None


class TokenBalance(BaseModel):
    chain: str
    symbol: str
    name: Optional[str] = None
    balance: float = 0.0
    balance_usd: float = 0.0
    contract_address: Optional[str] = None
    decimals: int = 18


class ChainSummary(BaseModel):
    chain: str
    chain_name: str
    native_symbol: str
    total_transactions: int = 0
    incoming_transactions: int = 0
    outgoing_transactions: int = 0
    total_received: float = 0.0
    total_received_usd: float = 0.0
    total_sent: float = 0.0
    total_sent_usd: float = 0.0
    total_gas_spent: float = 0.0
    total_gas_spent_usd: float = 0.0
    native_balance: float = 0.0
    native_balance_usd: float = 0.0
    token_holdings: list["TokenBalance"] = []
    first_transaction_date: Optional[datetime] = None
    last_transaction_date: Optional[datetime] = None
    unique_contracts_interacted: int = 0
    token_transfers_count: int = 0


class WalletReport(BaseModel):
    address: str
    address_type: str
    chains_analyzed: list[str] = []
    chains_with_activity: list[str] = []
    total_transactions: int = 0
    total_received_usd: float = 0.0
    total_sent_usd: float = 0.0
    total_gas_spent_usd: float = 0.0
    net_flow_usd: float = 0.0
    total_current_balance_usd: float = 0.0
    chain_summaries: list[ChainSummary] = []
    all_token_holdings: list[TokenBalance] = []
    top_chains_by_transactions: list[dict] = []
    first_activity: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    wallet_age_days: Optional[int] = None
    ai_insights: Optional[str] = None
    warnings: list[str] = []


# ── API Models ────────────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    status: str
    version: str


class AnalyzeRequest(BaseModel):
    address: str = Field(..., description="Public wallet address (EVM/Solana/BTC/Tron)")
    chains: Optional[list[str]] = Field(
        None,
        description="Specific chains to analyze. Leave empty for auto-detection.",
    )


class AnalyzeResponse(BaseModel):
    success: bool
    address: str
    error: Optional[str] = None
    report: Optional[WalletReport] = None
    processing_time_ms: Optional[int] = None
