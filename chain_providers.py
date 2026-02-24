import asyncio
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

import httpx

from models import ChainSummary, TokenBalance, Transaction
from utils import wei_to_ether, lamports_to_sol, satoshi_to_btc


# ── Etherscan V2 Unified API ──────────────────────────────────────────────────
# Single endpoint + chainid param. One API key covers all chains.

ETHERSCAN_V2_BASE = "https://api.etherscan.io/v2/api"

EVM_CHAINS = {
    "ethereum": {
        "name": "Ethereum",
        "symbol": "ETH",
        "chain_id": 1,
        "coingecko_id": "ethereum",
    },
    "polygon": {
        "name": "Polygon",
        "symbol": "POL",
        "chain_id": 137,
        "coingecko_id": "polygon-ecosystem-token",
    },
    "bsc": {
        "name": "BNB Chain",
        "symbol": "BNB",
        "chain_id": 56,
        "coingecko_id": "binancecoin",
    },
    "arbitrum": {
        "name": "Arbitrum",
        "symbol": "ETH",
        "chain_id": 42161,
        "coingecko_id": "ethereum",
    },
    "optimism": {
        "name": "Optimism",
        "symbol": "ETH",
        "chain_id": 10,
        "coingecko_id": "ethereum",
    },
    "avalanche": {
        "name": "Avalanche",
        "symbol": "AVAX",
        "chain_id": 43114,
        "coingecko_id": "avalanche-2",
    },
    "base": {
        "name": "Base",
        "symbol": "ETH",
        "chain_id": 8453,
        "coingecko_id": "ethereum",
    },
    "fantom": {
        "name": "Fantom",
        "symbol": "FTM",
        "chain_id": 250,
        "coingecko_id": "fantom",
    },
}


# ── Alchemy Token API ─────────────────────────────────────────────────────────
# Single API key, per-chain RPC endpoints.

ALCHEMY_NETWORKS: dict[str, str] = {
    "ethereum": "eth-mainnet",
    "polygon": "polygon-mainnet",
    "arbitrum": "arb-mainnet",
    "optimism": "opt-mainnet",
    "base": "base-mainnet",
    "avalanche": "avax-mainnet",
}

# Well-known stablecoins → treat as $1.00
_STABLECOIN_SYMBOLS = {
    "USDC", "USDT", "DAI", "BUSD", "TUSD", "FRAX", "LUSD", "USDP",
    "USDC.e", "USDT.e", "USDbC", "USDe",
}
# Wrapped native tokens → price = native token price
_WRAPPED_NATIVE = {"WETH", "WBNB", "WMATIC", "WPOL", "WAVAX", "WFTM"}


# ── Base Provider ─────────────────────────────────────────────────────────────


class ChainProvider(ABC):
    """Abstract base for chain-specific data providers."""

    @abstractmethod
    async def get_transactions(self, address: str) -> list[Transaction]:
        ...

    @abstractmethod
    async def get_chain_summary(
        self, address: str, price_usd: float
    ) -> Optional[ChainSummary]:
        ...


# ── EVM Provider (Etherscan for txns, Alchemy for token balances) ────────────


class EVMChainProvider(ChainProvider):
    def __init__(self, chain_id: str):
        cfg = EVM_CHAINS[chain_id]
        self.chain_id = chain_id
        self.name = cfg["name"]
        self.symbol = cfg["symbol"]
        self.evm_chain_id = cfg["chain_id"]

        # Etherscan V2 config (transactions)
        snowtrace_key = os.getenv("SNOWTRACE_API_KEY", "")
        if chain_id == "avalanche" and snowtrace_key:
            self.api_base = "https://api.routescan.io/v2/network/mainnet/evm/43114/etherscan/api"
            self.api_key = snowtrace_key
            self.use_routescan = True
        else:
            self.api_base = ETHERSCAN_V2_BASE
            self.api_key = os.getenv("ETHERSCAN_API_KEY", "")
            self.use_routescan = False

        # Alchemy config (token balances + native balance)
        alchemy_key = os.getenv("ALCHEMY_API_KEY", "")
        alchemy_net = ALCHEMY_NETWORKS.get(chain_id)
        if alchemy_key and alchemy_net:
            self.alchemy_url = f"https://{alchemy_net}.g.alchemy.com/v2/{alchemy_key}"
        else:
            self.alchemy_url = ""

    # ── Etherscan API helpers ──────────────────────────────────────────────

    async def _api_call(self, client: httpx.AsyncClient, params: dict) -> dict:
        if not self.use_routescan:
            params["chainid"] = self.evm_chain_id
        if self.api_key:
            params["apikey"] = self.api_key
        resp = await client.get(self.api_base, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") == "0" and "API Key" in data.get("result", ""):
            raise PermissionError(
                f"ETHERSCAN_API_KEY missing or invalid. "
                f"Get a free key at https://etherscan.io/apis"
            )
        return data

    # ── Transaction History (Etherscan) ────────────────────────────────────

    async def get_transactions(self, address: str) -> list[Transaction]:
        transactions: list[Transaction] = []
        async with httpx.AsyncClient() as client:
            data = await self._api_call(client, {
                "module": "account",
                "action": "txlist",
                "address": address,
                "startblock": 0,
                "endblock": 99999999,
                "sort": "desc",
            })

            if data.get("status") != "1" or not data.get("result"):
                return []

            for tx in data["result"]:
                value = wei_to_ether(int(tx.get("value", 0)))
                gas_used = int(tx.get("gasUsed", 0))
                gas_price = int(tx.get("gasPrice", 0))
                gas_fee = wei_to_ether(gas_used * gas_price)
                is_incoming = tx.get("to", "").lower() == address.lower()

                ts = None
                if tx.get("timeStamp"):
                    try:
                        ts = datetime.fromtimestamp(int(tx["timeStamp"]))
                    except (ValueError, OSError):
                        pass

                fn = tx.get("functionName", "")
                method = fn.split("(")[0] if fn else None

                transactions.append(Transaction(
                    hash=tx.get("hash", ""),
                    chain=self.chain_id,
                    block_number=int(tx.get("blockNumber", 0)),
                    timestamp=ts,
                    from_address=tx.get("from", ""),
                    to_address=tx.get("to", ""),
                    value=value,
                    gas_used=gas_used,
                    gas_price=gas_price,
                    gas_fee=gas_fee,
                    is_incoming=is_incoming,
                    method=method,
                ))
        return transactions

    async def _get_token_transfers(
        self, address: str, client: httpx.AsyncClient
    ) -> list[Transaction]:
        transactions: list[Transaction] = []
        data = await self._api_call(client, {
            "module": "account",
            "action": "tokentx",
            "address": address,
            "startblock": 0,
            "endblock": 99999999,
            "sort": "desc",
        })

        if data.get("status") != "1" or not data.get("result"):
            return []

        for tx in data["result"][:500]:
            decimals = int(tx.get("tokenDecimal", 18))
            value = int(tx.get("value", 0)) / (10 ** decimals)
            is_incoming = tx.get("to", "").lower() == address.lower()

            ts = None
            if tx.get("timeStamp"):
                try:
                    ts = datetime.fromtimestamp(int(tx["timeStamp"]))
                except (ValueError, OSError):
                    pass

            transactions.append(Transaction(
                hash=tx.get("hash", ""),
                chain=self.chain_id,
                block_number=int(tx.get("blockNumber", 0)),
                timestamp=ts,
                from_address=tx.get("from", ""),
                to_address=tx.get("to", ""),
                value=value,
                is_incoming=is_incoming,
                is_token_transfer=True,
                token_symbol=tx.get("tokenSymbol", ""),
                token_name=tx.get("tokenName", ""),
            ))
        return transactions

    # ── Native Balance (Alchemy preferred, Etherscan fallback) ─────────────

    async def _get_native_balance(
        self, address: str, client: httpx.AsyncClient
    ) -> float:
        # Try Alchemy first (no rate limit issues)
        if self.alchemy_url:
            try:
                resp = await client.post(self.alchemy_url, json={
                    "jsonrpc": "2.0",
                    "method": "eth_getBalance",
                    "params": [address, "latest"],
                    "id": 1,
                }, timeout=15)
                data = resp.json()
                hex_bal = data.get("result", "0x0")
                return wei_to_ether(int(hex_bal, 16))
            except Exception:
                pass

        # Etherscan fallback
        try:
            data = await self._api_call(client, {
                "module": "account",
                "action": "balance",
                "address": address,
            })
            if data.get("status") == "1" and data.get("result"):
                return wei_to_ether(int(data["result"]))
        except Exception:
            pass
        return 0.0

    # ── Token Holdings (Alchemy — one call gets ALL tokens) ────────────────

    async def _get_token_holdings(
        self, address: str, client: httpx.AsyncClient, price_usd: float
    ) -> list[TokenBalance]:
        if not self.alchemy_url:
            return []

        try:
            # Step 1: Get ALL token balances in one call
            resp = await client.post(self.alchemy_url, json={
                "jsonrpc": "2.0",
                "method": "alchemy_getTokenBalances",
                "params": [address, "erc20"],
                "id": 1,
            }, timeout=30)
            data = resp.json()

            all_balances = data.get("result", {}).get("tokenBalances", [])

            # Filter non-zero balances
            non_zero = []
            for tb in all_balances:
                hex_bal = tb.get("tokenBalance", "0x0")
                if hex_bal and hex_bal != "0x0" and int(hex_bal, 16) > 0:
                    non_zero.append(tb)

            if not non_zero:
                return []

            # Step 2: Batch fetch metadata for all non-zero tokens (one HTTP call)
            batch = [
                {
                    "jsonrpc": "2.0",
                    "method": "alchemy_getTokenMetadata",
                    "params": [tb["contractAddress"]],
                    "id": i,
                }
                for i, tb in enumerate(non_zero[:30])
            ]

            meta_resp = await client.post(self.alchemy_url, json=batch, timeout=30)
            meta_results = meta_resp.json()

            # Handle both list (batch) and single dict (error) responses
            if not isinstance(meta_results, list):
                meta_results = [meta_results]

            # Step 3: Build holdings
            holdings: list[TokenBalance] = []
            for i, tb in enumerate(non_zero[:30]):
                meta = {}
                if i < len(meta_results):
                    meta = meta_results[i].get("result", {}) or {}

                decimals = meta.get("decimals") or 18
                symbol = meta.get("symbol") or ""
                name = meta.get("name") or symbol

                # Skip tokens with no symbol (likely spam/scam)
                if not symbol:
                    continue

                raw = int(tb["tokenBalance"], 16)
                balance = raw / (10 ** decimals) if decimals else float(raw)

                if balance > 0:
                    usd = self._estimate_token_usd(symbol, balance, price_usd)
                    holdings.append(TokenBalance(
                        chain=self.chain_id,
                        symbol=symbol,
                        name=name,
                        balance=round(balance, 6),
                        balance_usd=round(usd, 2),
                        contract_address=tb["contractAddress"],
                        decimals=decimals,
                    ))

            # Sort by USD value descending (known-value tokens first)
            holdings.sort(key=lambda t: t.balance_usd, reverse=True)
            return holdings

        except Exception as e:
            print(f"  [!] Alchemy token balances failed for {self.chain_id}: {e}")
            return []

    @staticmethod
    def _estimate_token_usd(symbol: str, balance: float, native_price: float) -> float:
        upper = symbol.upper()
        # Check stablecoins (including bridged variants like USDC.e)
        if upper in _STABLECOIN_SYMBOLS or upper.replace(".E", ".e") in _STABLECOIN_SYMBOLS:
            return balance * 1.0
        if upper in _WRAPPED_NATIVE:
            return balance * native_price
        return 0.0

    # ── Chain Summary (combines Etherscan txns + Alchemy balances) ─────────

    async def get_chain_summary(
        self, address: str, price_usd: float
    ) -> Optional[ChainSummary]:
        async with httpx.AsyncClient() as client:
            try:
                normal_txs = await self.get_transactions(address)
                token_txs = await self._get_token_transfers(address, client)
                native_balance = await self._get_native_balance(address, client)
                token_holdings = await self._get_token_holdings(
                    address, client, price_usd
                )
            except Exception:
                return None

            if not normal_txs and not token_txs:
                return None

            all_txs = normal_txs + token_txs
            incoming = [t for t in normal_txs if t.is_incoming]
            outgoing = [t for t in normal_txs if not t.is_incoming]

            total_received = sum(t.value for t in incoming)
            total_sent = sum(t.value for t in outgoing)
            total_gas = sum(t.gas_fee or 0 for t in normal_txs)

            timestamps = [t.timestamp for t in all_txs if t.timestamp]

            unique_contracts: set[str] = set()
            for t in normal_txs:
                if t.to_address:
                    unique_contracts.add(t.to_address.lower())

            return ChainSummary(
                chain=self.chain_id,
                chain_name=self.name,
                native_symbol=self.symbol,
                total_transactions=len(normal_txs),
                incoming_transactions=len(incoming),
                outgoing_transactions=len(outgoing),
                total_received=round(total_received, 8),
                total_received_usd=round(total_received * price_usd, 2),
                total_sent=round(total_sent, 8),
                total_sent_usd=round(total_sent * price_usd, 2),
                total_gas_spent=round(total_gas, 8),
                total_gas_spent_usd=round(total_gas * price_usd, 2),
                native_balance=round(native_balance, 8),
                native_balance_usd=round(native_balance * price_usd, 2),
                token_holdings=token_holdings,
                first_transaction_date=min(timestamps) if timestamps else None,
                last_transaction_date=max(timestamps) if timestamps else None,
                unique_contracts_interacted=len(unique_contracts),
                token_transfers_count=len(token_txs),
            )


# ── Solana Provider ───────────────────────────────────────────────────────────


class SolanaProvider(ChainProvider):
    def __init__(self):
        self.rpc_url = os.getenv(
            "SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com"
        )
        self.chain_id = "solana"
        self.name = "Solana"
        self.symbol = "SOL"

    async def _rpc(self, client: httpx.AsyncClient, method: str, params: list) -> dict:
        resp = await client.post(
            self.rpc_url,
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    async def get_transactions(self, address: str) -> list[Transaction]:
        transactions: list[Transaction] = []
        async with httpx.AsyncClient() as client:
            result = await self._rpc(
                client, "getSignaturesForAddress", [address, {"limit": 1000}]
            )

            for sig in result.get("result", []):
                ts = None
                if sig.get("blockTime"):
                    try:
                        ts = datetime.fromtimestamp(sig["blockTime"])
                    except (ValueError, OSError):
                        pass

                transactions.append(Transaction(
                    hash=sig.get("signature", ""),
                    chain="solana",
                    block_number=sig.get("slot"),
                    timestamp=ts,
                    from_address=address,
                    to_address="",
                    value=0,
                    is_incoming=False,
                ))
        return transactions

    async def get_chain_summary(
        self, address: str, price_usd: float
    ) -> Optional[ChainSummary]:
        async with httpx.AsyncClient() as client:
            try:
                txs = await self.get_transactions(address)

                bal_result = await self._rpc(client, "getBalance", [address])
                balance_sol = lamports_to_sol(
                    bal_result.get("result", {}).get("value", 0)
                )
            except Exception:
                return None

            if not txs:
                return None

            timestamps = [t.timestamp for t in txs if t.timestamp]

            return ChainSummary(
                chain="solana",
                chain_name="Solana",
                native_symbol="SOL",
                total_transactions=len(txs),
                incoming_transactions=0,
                outgoing_transactions=0,
                total_received=round(balance_sol, 6),
                total_received_usd=round(balance_sol * price_usd, 2),
                total_sent=0,
                total_sent_usd=0,
                total_gas_spent=0,
                total_gas_spent_usd=0,
                native_balance=round(balance_sol, 6),
                native_balance_usd=round(balance_sol * price_usd, 2),
                first_transaction_date=min(timestamps) if timestamps else None,
                last_transaction_date=max(timestamps) if timestamps else None,
                unique_contracts_interacted=0,
                token_transfers_count=0,
            )


# ── Bitcoin Provider ──────────────────────────────────────────────────────────


class BitcoinProvider(ChainProvider):
    def __init__(self):
        self.api_base = "https://blockchain.info"
        self.chain_id = "bitcoin"
        self.name = "Bitcoin"
        self.symbol = "BTC"

    async def get_transactions(self, address: str) -> list[Transaction]:
        transactions: list[Transaction] = []
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.api_base}/rawaddr/{address}",
                params={"limit": 100},
                timeout=30,
            )
            if resp.status_code != 200:
                return []

            data = resp.json()

            for tx in data.get("txs", []):
                value_in = sum(
                    out.get("value", 0)
                    for out in tx.get("out", [])
                    if out.get("addr") == address
                )
                value_out = sum(
                    inp.get("prev_out", {}).get("value", 0)
                    for inp in tx.get("inputs", [])
                    if inp.get("prev_out", {}).get("addr") == address
                )

                is_incoming = value_in > value_out
                value_btc = satoshi_to_btc(max(value_in, value_out))

                ts = None
                if tx.get("time"):
                    try:
                        ts = datetime.fromtimestamp(tx["time"])
                    except (ValueError, OSError):
                        pass

                transactions.append(Transaction(
                    hash=tx.get("hash", ""),
                    chain="bitcoin",
                    block_number=tx.get("block_height"),
                    timestamp=ts,
                    from_address="" if is_incoming else address,
                    to_address=address if is_incoming else "",
                    value=value_btc,
                    is_incoming=is_incoming,
                ))
        return transactions

    async def get_chain_summary(
        self, address: str, price_usd: float
    ) -> Optional[ChainSummary]:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{self.api_base}/rawaddr/{address}",
                    params={"limit": 50},
                    timeout=30,
                )
                if resp.status_code != 200:
                    return None
                data = resp.json()
            except Exception:
                return None

            n_tx = data.get("n_tx", 0)
            if n_tx == 0:
                return None

            total_received = satoshi_to_btc(data.get("total_received", 0))
            total_sent = satoshi_to_btc(data.get("total_sent", 0))
            final_balance = satoshi_to_btc(data.get("final_balance", 0))

            timestamps: list[datetime] = []
            for tx in data.get("txs", []):
                if tx.get("time"):
                    try:
                        timestamps.append(datetime.fromtimestamp(tx["time"]))
                    except (ValueError, OSError):
                        pass

            return ChainSummary(
                chain="bitcoin",
                chain_name="Bitcoin",
                native_symbol="BTC",
                total_transactions=n_tx,
                incoming_transactions=0,
                outgoing_transactions=0,
                total_received=round(total_received, 8),
                total_received_usd=round(total_received * price_usd, 2),
                total_sent=round(total_sent, 8),
                total_sent_usd=round(total_sent * price_usd, 2),
                total_gas_spent=0,
                total_gas_spent_usd=0,
                native_balance=round(final_balance, 8),
                native_balance_usd=round(final_balance * price_usd, 2),
                first_transaction_date=min(timestamps) if timestamps else None,
                last_transaction_date=max(timestamps) if timestamps else None,
                unique_contracts_interacted=0,
                token_transfers_count=0,
            )


# ── Tron Provider ─────────────────────────────────────────────────────────────


class TronProvider(ChainProvider):
    def __init__(self):
        self.api_base = "https://api.trongrid.io"
        self.api_key = os.getenv("TRONGRID_API_KEY", "")
        self.chain_id = "tron"
        self.name = "Tron"
        self.symbol = "TRX"

    async def get_transactions(self, address: str) -> list[Transaction]:
        transactions: list[Transaction] = []
        headers: dict[str, str] = {}
        if self.api_key:
            headers["TRON-PRO-API-KEY"] = self.api_key

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.api_base}/v1/accounts/{address}/transactions",
                params={"limit": 200},
                headers=headers,
                timeout=30,
            )
            if resp.status_code != 200:
                return []

            data = resp.json()
            for tx in data.get("data", []):
                raw = tx.get("raw_data", {})
                contracts = raw.get("contract", [])

                value = 0.0
                to_addr = ""
                from_addr = ""
                if contracts:
                    param = contracts[0].get("parameter", {}).get("value", {})
                    to_addr = param.get("to_address", "")
                    from_addr = param.get("owner_address", "")
                    value = param.get("amount", 0) / 1e6  # SUN -> TRX

                is_incoming = to_addr.lower() == address.lower()

                ts = None
                if tx.get("block_timestamp"):
                    try:
                        ts = datetime.fromtimestamp(tx["block_timestamp"] / 1000)
                    except (ValueError, OSError):
                        pass

                transactions.append(Transaction(
                    hash=tx.get("txID", ""),
                    chain="tron",
                    block_number=tx.get("blockNumber"),
                    timestamp=ts,
                    from_address=from_addr,
                    to_address=to_addr,
                    value=value,
                    is_incoming=is_incoming,
                ))
        return transactions

    async def get_chain_summary(
        self, address: str, price_usd: float
    ) -> Optional[ChainSummary]:
        try:
            txs = await self.get_transactions(address)
        except Exception:
            return None

        if not txs:
            return None

        incoming = [t for t in txs if t.is_incoming]
        outgoing = [t for t in txs if not t.is_incoming]
        total_received = sum(t.value for t in incoming)
        total_sent = sum(t.value for t in outgoing)

        timestamps = [t.timestamp for t in txs if t.timestamp]

        return ChainSummary(
            chain="tron",
            chain_name="Tron",
            native_symbol="TRX",
            total_transactions=len(txs),
            incoming_transactions=len(incoming),
            outgoing_transactions=len(outgoing),
            total_received=round(total_received, 6),
            total_received_usd=round(total_received * price_usd, 2),
            total_sent=round(total_sent, 6),
            total_sent_usd=round(total_sent * price_usd, 2),
            total_gas_spent=0,
            total_gas_spent_usd=0,
            first_transaction_date=min(timestamps) if timestamps else None,
            last_transaction_date=max(timestamps) if timestamps else None,
            unique_contracts_interacted=0,
            token_transfers_count=0,
        )


# ── Price Fetcher ─────────────────────────────────────────────────────────────

# Fallback prices (updated periodically) — used when CoinGecko is rate-limited
_FALLBACK_PRICES: dict[str, float] = {
    "ethereum": 2500.0,
    "polygon-ecosystem-token": 0.35,
    "binancecoin": 650.0,
    "avalanche-2": 25.0,
    "fantom": 0.50,
    "solana": 170.0,
    "bitcoin": 95000.0,
    "tron": 0.13,
}


async def get_token_prices(coingecko_ids: list[str]) -> dict[str, float]:
    """Fetch current USD prices from CoinGecko. Falls back to approximate prices on failure."""
    if not coingecko_ids:
        return {}

    async with httpx.AsyncClient() as client:
        for attempt in range(2):
            try:
                resp = await client.get(
                    "https://api.coingecko.com/api/v3/simple/price",
                    params={"ids": ",".join(coingecko_ids), "vs_currencies": "usd"},
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    prices = {k: v.get("usd", 0) for k, v in data.items()}
                    if any(v > 0 for v in prices.values()):
                        return prices
                if resp.status_code == 429 and attempt == 0:
                    await asyncio.sleep(2)
                    continue
            except Exception:
                pass
            break

    print("  [!] CoinGecko unavailable — using fallback prices")
    return {cid: _FALLBACK_PRICES.get(cid, 0) for cid in coingecko_ids}


# ── Factory ───────────────────────────────────────────────────────────────────


def get_provider(chain_id: str) -> Optional[ChainProvider]:
    if chain_id in EVM_CHAINS:
        return EVMChainProvider(chain_id)
    elif chain_id == "solana":
        return SolanaProvider()
    elif chain_id == "bitcoin":
        return BitcoinProvider()
    elif chain_id == "tron":
        return TronProvider()
    return None
