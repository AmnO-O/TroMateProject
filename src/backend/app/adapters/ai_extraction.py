"""Gemini-backed natural language expense extractor with rule-based fallback."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.adapters.vnd_parser import RawExtractionResult, extract_expense_fallback

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You extract Vietnamese shared roommate expenses into strict JSON.
Return ONLY a JSON object with these keys:
- is_expense (boolean): true if the message logs an expense, false otherwise.
- raw_amount (string): total amount token (e.g. "150k", "1 củ rưỡi", "650000").
- description (string): short expense description in Vietnamese.
- payer_hint (string): who paid ("sender" if the sender paid or no payer is named; otherwise the
  exact name of the person stated as having paid, e.g. "Lan"). Default "sender".
- participant_hints (array of strings): sharing members, or [] if whole room.
- split_type (string): "EQUAL" or "CUSTOM_AMOUNT".
- custom_splits (object): member -> amount map when split_type is "CUSTOM_AMOUNT", else {}.
- category_hint (string): "Food & Drinks" | "Groceries" | "Household Supplies" |
  "Utilities" | "Rent" | "Internet" | "Other".
"""


class AIExtractionAdapter:
    """Extracts structured expense intent via Google Gemini API with automatic fallback."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        model: str = "gemini-3.5-flash-lite",
        timeout_s: float = 10.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = (api_key or "").strip()
        self.model = model
        self.timeout_s = timeout_s
        self._client = client

    async def extract(self, text: str) -> RawExtractionResult | None:
        """Extract expense data using Gemini if configured, else fallback to ``vnd_parser``."""

        cleaned = text.strip()
        if not cleaned:
            return None

        if not self.api_key:
            return extract_expense_fallback(cleaned)

        try:
            return await self._extract_with_gemini(cleaned)
        except Exception as exc:
            logger.warning(
                "Gemini extraction failed (%s); falling back to vnd_parser",
                type(exc).__name__,
            )
            return extract_expense_fallback(cleaned)

    async def _extract_with_gemini(self, text: str) -> RawExtractionResult | None:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent"
        )
        headers = {"x-goog-api-key": self.api_key}
        body: dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": _SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": text}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.0,
            },
        }

        if self._client is not None:
            response = await self._client.post(
                url,
                headers=headers,
                json=body,
                timeout=self.timeout_s,
            )
        else:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                response = await client.post(url, headers=headers, json=body)

        response.raise_for_status()
        payload = response.json()
        raw_text = payload["candidates"][0]["content"]["parts"][0]["text"]
        data = json.loads(raw_text)

        if not data.get("is_expense", True) and not data.get("raw_amount"):
            return None

        raw_amount = str(data.get("raw_amount", "")).strip()
        if not raw_amount:
            raise ValueError("Gemini response missing raw_amount")

        split_type = str(data.get("split_type") or "EQUAL").upper()
        if split_type not in {"EQUAL", "CUSTOM_AMOUNT"}:
            split_type = "EQUAL"

        custom_splits_raw = data.get("custom_splits") or {}
        custom_splits = (
            {str(k): str(v) for k, v in custom_splits_raw.items()}
            if isinstance(custom_splits_raw, dict)
            else {}
        )
        participants_raw = data.get("participant_hints") or []
        participant_hints = (
            [str(item) for item in participants_raw if str(item).strip()]
            if isinstance(participants_raw, list)
            else []
        )

        return RawExtractionResult(
            raw_amount=raw_amount,
            description=str(data.get("description") or "Chi tiêu chung").strip(),
            payer_hint=str(data.get("payer_hint") or "sender").strip(),
            participant_hints=participant_hints,
            split_type=split_type,
            custom_splits=custom_splits,
            category_hint=str(data.get("category_hint") or "Other").strip(),
            source="gemini",
        )
