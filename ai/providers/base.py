"""
ai/providers/base.py

BaseProvider re-exported from core for use within the ai/ package.
Concrete implementations live here in Phase 2:
  - ai/providers/anthropic.py  (AnthropicProvider)
  - ai/providers/openai.py     (OpenAIProvider)
  - ai/providers/ollama.py     (OllamaProvider)

Engines import providers through dependency injection, never directly.
"""
from core.interfaces.ai_engine import BaseProvider

__all__ = ["BaseProvider"]
