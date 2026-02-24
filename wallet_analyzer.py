import asyncio
import os
from datetime import datetime
from typing import Optional

from chain_providers import EVM_CHAINS, get_provider, get_token_prices
from models import AddressType, ChainSummary, WalletReport
from utils import detect_address_type, get_chains_for_address


# Map chain IDs -> CoinGecko IDs for price lookups
CHAIN_TO_COINGECKO: dict[str, str] = {
    "ethereum": "ethereum",
    "polygon": "polygon-ecosystem-token",
    "bsc": "binancecoin",
    "arbitrum": "ethereum",
    "optimism": "ethereum",
    "avalanche": "avalanche-2",
    "base": "ethereum",
    "fantom": "fantom",
    "solana": "solana",
    "bitcoin": "bitcoin",
    "tron": "tron",
}


class WalletAnalyzer:
    """Orchestrates multi-chain wallet analysis."""

    async def analyze(
        self, address: str, chains: Optional[list[str]] = None
    ) -> WalletReport:
        address = address.strip()
        addr_type = detect_address_type(address)

        if addr_type == AddressType.UNKNOWN:
            raise ValueError(f"Unrecognized address format: {address}")

        target_chains = chains if chains else get_chains_for_address(address)
        if not target_chains:
            raise ValueError(
                f"No supported chains for address type: {addr_type.value}"
            )

        # ── Fetch token prices ────────────────────────────────────────────
        coingecko_ids = list(set(
            CHAIN_TO_COINGECKO[c] for c in target_chains if c in CHAIN_TO_COINGECKO
        ))
        prices = await get_token_prices(coingecko_ids)

        # ── Analyze each chain concurrently ───────────────────────────────
        tasks = []
        for chain_id in target_chains:
            provider = get_provider(chain_id)
            if provider:
                cg_id = CHAIN_TO_COINGECKO.get(chain_id, "")
                price = prices.get(cg_id, 0)
                tasks.append(self._analyze_chain(provider, address, price, chain_id))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # ── Collect successful summaries & warnings ───────────────────────
        chain_summaries: list[ChainSummary] = []
        warnings: list[str] = []
        api_key_missing = False

        for r in results:
            if isinstance(r, ChainSummary):
                chain_summaries.append(r)
            elif isinstance(r, PermissionError):
                api_key_missing = True

        if api_key_missing:
            warnings.append(
                "ETHERSCAN_API_KEY is missing or invalid. "
                "EVM chain data (Ethereum, Polygon, BSC, Arbitrum, Optimism, Avalanche, Base, Fantom) "
                "could not be fetched. Get a free key at https://etherscan.io/apis"
            )

        # Check for no results on EVM addresses
        evm_targets = [c for c in target_chains if c in EVM_CHAINS]
        if evm_targets and not chain_summaries and not os.getenv("ETHERSCAN_API_KEY"):
            warnings.append(
                "No data returned for any EVM chain. "
                "This is almost certainly because ETHERSCAN_API_KEY is not set. "
                "Set it in your .env file or Render environment variables."
            )

        # Sort by total transactions descending (top chains first)
        chain_summaries.sort(key=lambda s: s.total_transactions, reverse=True)

        # ── Aggregate ─────────────────────────────────────────────────────
        total_txs = sum(s.total_transactions for s in chain_summaries)
        total_received_usd = sum(s.total_received_usd for s in chain_summaries)
        total_sent_usd = sum(s.total_sent_usd for s in chain_summaries)
        total_gas_usd = sum(s.total_gas_spent_usd for s in chain_summaries)

        # ── Current balances ──────────────────────────────────────────────
        total_native_usd = sum(s.native_balance_usd for s in chain_summaries)
        total_tokens_usd = sum(
            sum(t.balance_usd for t in s.token_holdings)
            for s in chain_summaries
        )
        total_current_balance_usd = round(total_native_usd + total_tokens_usd, 2)

        # Flatten all token holdings across chains
        all_token_holdings = []
        for s in chain_summaries:
            all_token_holdings.extend(s.token_holdings)
        all_token_holdings.sort(key=lambda t: t.balance_usd, reverse=True)

        all_first = [
            s.first_transaction_date
            for s in chain_summaries
            if s.first_transaction_date
        ]
        all_last = [
            s.last_transaction_date
            for s in chain_summaries
            if s.last_transaction_date
        ]

        first_activity = min(all_first) if all_first else None
        last_activity = max(all_last) if all_last else None
        wallet_age = (datetime.now() - first_activity).days if first_activity else None

        top_chains = [
            {
                "chain": s.chain_name,
                "transactions": s.total_transactions,
                "volume_usd": round(s.total_received_usd + s.total_sent_usd, 2),
                "current_balance_usd": round(
                    s.native_balance_usd + sum(t.balance_usd for t in s.token_holdings), 2
                ),
            }
            for s in chain_summaries
        ]

        return WalletReport(
            address=address,
            address_type=addr_type.value,
            chains_analyzed=target_chains,
            chains_with_activity=[s.chain for s in chain_summaries],
            total_transactions=total_txs,
            total_received_usd=round(total_received_usd, 2),
            total_sent_usd=round(total_sent_usd, 2),
            total_gas_spent_usd=round(total_gas_usd, 2),
            net_flow_usd=round(total_received_usd - total_sent_usd, 2),
            total_current_balance_usd=total_current_balance_usd,
            chain_summaries=chain_summaries,
            all_token_holdings=all_token_holdings,
            top_chains_by_transactions=top_chains,
            first_activity=first_activity,
            last_activity=last_activity,
            wallet_age_days=wallet_age,
            warnings=warnings,
        )

    async def _analyze_chain(
        self, provider, address: str, price_usd: float, chain_id: str
    ) -> Optional[ChainSummary]:
        try:
            return await provider.get_chain_summary(address, price_usd)
        except Exception as e:
            print(f"  [!] {chain_id} failed: {e}")
            return None
