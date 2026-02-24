import re

from models import AddressType


def detect_address_type(address: str) -> AddressType:
    """Detect the blockchain address type from format."""
    address = address.strip()

    # EVM — 0x + 40 hex chars
    if re.match(r"^0x[a-fA-F0-9]{40}$", address):
        return AddressType.EVM

    # Bitcoin Legacy (1...) or P2SH (3...)
    if re.match(r"^(1|3)[a-km-zA-HJ-NP-Z1-9]{25,34}$", address):
        return AddressType.BITCOIN

    # Bitcoin Bech32 (bc1...)
    if re.match(r"^bc1[a-zA-HJ-NP-Z0-9]{25,90}$", address):
        return AddressType.BITCOIN

    # Tron — starts with T, 34 chars
    if re.match(r"^T[a-zA-Z0-9]{33}$", address):
        return AddressType.TRON

    # Solana — Base58, 32-44 chars (checked last to avoid false positives)
    if re.match(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$", address):
        return AddressType.SOLANA

    return AddressType.UNKNOWN


def get_chains_for_address(address: str) -> list[str]:
    """Return chain IDs to scan for a given address."""
    addr_type = detect_address_type(address)

    if addr_type == AddressType.EVM:
        return [
            "ethereum", "polygon", "bsc", "arbitrum",
            "optimism", "avalanche", "base", "fantom",
        ]
    elif addr_type == AddressType.SOLANA:
        return ["solana"]
    elif addr_type == AddressType.BITCOIN:
        return ["bitcoin"]
    elif addr_type == AddressType.TRON:
        return ["tron"]
    return []


def short_address(address: str, chars: int = 6) -> str:
    """Truncate: 0x1234...abcd"""
    if len(address) <= chars * 2 + 3:
        return address
    return f"{address[:chars]}...{address[-chars:]}"


def wei_to_ether(wei: int | str) -> float:
    return int(wei) / 1e18


def lamports_to_sol(lamports: int | str) -> float:
    return int(lamports) / 1e9


def satoshi_to_btc(satoshi: int | str) -> float:
    return int(satoshi) / 1e8


def format_currency(amount: float, symbol: str = "$", decimals: int = 2) -> str:
    if abs(amount) >= 1_000_000:
        return f"{symbol}{amount / 1_000_000:,.{decimals}f}M"
    elif abs(amount) >= 1_000:
        return f"{symbol}{amount / 1_000:,.{decimals}f}K"
    return f"{symbol}{amount:,.{decimals}f}"


def format_number(n: int) -> str:
    return f"{n:,}"
