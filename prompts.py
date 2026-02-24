SYSTEM_PROMPT = """You are a Web3 wallet intelligence analyst. You analyze blockchain wallet data \
and provide comprehensive, actionable insights.

Your analysis should be:
- Data-driven with specific numbers
- Organized by importance
- Written in clear, professional language
- Focused on patterns, risks, and opportunities

You receive structured wallet report data and generate human-readable analysis."""


ANALYSIS_PROMPT = """Analyze this wallet report and provide a comprehensive intelligence briefing.

WALLET DATA:
{wallet_data}

Generate a detailed analysis covering:

1. **WALLET OVERVIEW**: Quick summary — address type, age, total activity across all chains, \
and net USD position (received minus sent).

2. **CHAIN ACTIVITY BREAKDOWN** (sorted by most active first):
   For each active chain include:
   - Transaction count and direction split (in vs out)
   - Volume in native token and USD
   - Gas expenditure
   - Token transfer activity
   - First and last activity dates

3. **KEY INSIGHTS**:
   - Dominant chain and what that suggests about the user
   - Spending vs receiving patterns (net accumulator or net spender?)
   - Gas efficiency across chains
   - Notable patterns (heavy DeFi usage, NFT activity, bridging, dormancy, etc.)

4. **RISK INDICATORS**:
   - Unusual concentration on a single chain
   - High gas-to-volume ratio
   - Long dormancy periods followed by sudden activity
   - Any other anomalies in the data

5. **WALLET PROFILE VERDICT**: One paragraph classifying this wallet — trader, long-term holder, \
DeFi farmer, NFT collector, developer/deployer, casual user, or mixed profile. \
Support your classification with data points.

Be specific. Use actual numbers from the report. Never invent data."""
