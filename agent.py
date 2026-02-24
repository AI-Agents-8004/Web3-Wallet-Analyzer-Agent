import json
import os

from models import WalletReport
from prompts import ANALYSIS_PROMPT, SYSTEM_PROMPT


class WalletInsightsAgent:
    """AI agent that generates natural-language insights from wallet data."""

    def __init__(self):
        self.provider = os.getenv("AI_PROVIDER", "anthropic").lower()

        if self.provider == "anthropic":
            self._init_anthropic()
        elif self.provider == "gemini":
            self._init_gemini()
        elif self.provider == "openai":
            self._init_openai()
        else:
            raise ValueError(
                f"Unknown AI_PROVIDER '{self.provider}'. "
                "Set AI_PROVIDER to 'anthropic', 'openai', or 'gemini'."
            )

    # ── Provider Init ─────────────────────────────────────────────────────

    def _init_anthropic(self):
        import anthropic

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY is not set.")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
        print(f"  AI Provider: Anthropic | Model: {self.model}")

    def _init_gemini(self):
        import google.generativeai as genai

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError("GEMINI_API_KEY is not set.")
        genai.configure(api_key=api_key)
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self.client = genai.GenerativeModel(self.model)
        print(f"  AI Provider: Gemini | Model: {self.model}")

    def _init_openai(self):
        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY is not set.")
        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o")
        print(f"  AI Provider: OpenAI | Model: {self.model}")

    # ── Generate Insights ─────────────────────────────────────────────────

    def generate_insights(self, report: WalletReport) -> str:
        """Generate AI-powered analysis from wallet report data."""
        wallet_data = json.dumps(report.model_dump(), indent=2, default=str)
        prompt = ANALYSIS_PROMPT.format(wallet_data=wallet_data)

        if self.provider == "anthropic":
            return self._call_anthropic(prompt)
        elif self.provider == "gemini":
            return self._call_gemini(prompt)
        elif self.provider == "openai":
            return self._call_openai(prompt)
        return ""

    def _call_anthropic(self, prompt: str) -> str:
        message = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    def _call_gemini(self, prompt: str) -> str:
        response = self.client.generate_content(f"{SYSTEM_PROMPT}\n\n{prompt}")
        return response.text

    def _call_openai(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=4096,
        )
        return response.choices[0].message.content
