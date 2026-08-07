"""
core/interfaces/ai_engine.py

Two base classes:

  BaseProvider — LLM infrastructure adapter (OpenAI, Anthropic, Ollama, …).
                 Lives in ai/providers/.

  BaseAIEngine — Business logic engine (Resume, CoverLetter, Reviewer, …).
                 Lives in ai/engines/.
                 Engines depend on providers via dependency injection,
                 not on specific APIs.

Separation rationale (ADR-005):
  A provider knows HOW to call an LLM.
  An engine knows WHAT to ask and WHY.
  Ranking is not purely AI — it belongs in intelligence/, not ai/.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """
    LLM provider adapter.

    Wraps a single AI API (OpenAI, Anthropic, Ollama, etc.) behind
    a uniform interface so engines are not coupled to any specific API.

    Phase 2: Implementations in ai/providers/.
    """

    #: Provider identifier, e.g. "openai", "anthropic", "ollama".
    name: str

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        """
        Send a prompt and return the completion text.

        Args:
            prompt: The user-turn message.
            system: Optional system prompt.
            temperature: Sampling temperature.
            max_tokens: Token ceiling for the response.

        Returns:
            Raw completion text from the model.

        Raises:
            ProviderError: On API failure.
            ProviderRateLimitError: On 429 / quota exceeded.
        """
        ...

    @abstractmethod
    async def embed(self, text: str, model: Optional[str] = None) -> list[float]:
        """
        Generate a vector embedding for the given text.

        Args:
            text: Input text to embed.
            model: Optional embedding model override.

        Returns:
            Embedding vector as a list of floats.

        Raises:
            ProviderError: On API failure.
        """
        ...


# Allow Optional without importing typing at call sites
from typing import Optional  # noqa: E402


class BaseAIEngine(ABC):
    """
    Helios AI engine.

    Engines contain business logic — what to prompt, how to structure
    the output, what context to pass. They are provider-agnostic;
    the provider is injected at construction time.

    Current engines (Phase 1 contracts, Phase 2 implementations):
      - ResumeEngine     → wraps ai-job-search resume generation logic
      - CoverLetterEngine → wraps ai-job-search cover letter logic
      - InterviewEngine  → wraps ai-job-search interview prep logic
      - ReviewerEngine   → wraps ai-job-search drafter-reviewer logic
      - SkillGapEngine   → wraps upskill SKILL.md logic
      - CareerAdvisorEngine → new
    """

    #: Engine identifier, e.g. "resume", "cover_letter".
    name: str

    @abstractmethod
    async def run(self, context: dict) -> dict:
        """
        Execute the engine with the given context.

        Args:
            context: Engine-specific input dictionary. At minimum contains
                     the user profile and the target job.

        Returns:
            Engine-specific output dictionary. Schema is documented per engine.

        Raises:
            AIEngineError: On engine-level failure.
            ProviderError: On underlying LLM failure.
        """
        ...
