"""External adapters for natural-language extraction."""

from app.adapters.ai_extraction import AIExtractionAdapter
from app.adapters.vnd_parser import RawExtractionResult, extract_expense_fallback

__all__ = ["AIExtractionAdapter", "RawExtractionResult", "extract_expense_fallback"]
