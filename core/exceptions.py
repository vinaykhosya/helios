"""
core/exceptions.py

Domain-specific exceptions for Helios.

Hierarchy:
  HeliosError
    ├── ConnectorError
    │     ├── ConnectorNotFoundError
    │     ├── ConnectorRateLimitError
    │     ├── ConnectorAuthError
    │     ├── ConnectorParseError
    │     └── ConnectorHealthError
    ├── PipelineError
    │     ├── NormalizationError
    │     ├── DeduplicationError
    │     └── EmbeddingError
    ├── AIEngineError
    │     ├── ProviderError
    │     │     └── ProviderRateLimitError
    │     └── PromptError
    ├── DomainError
    │     ├── JobNotFoundError
    │     ├── CompanyNotFoundError
    │     ├── ApplicationNotFoundError
    │     └── UserNotFoundError
    └── DataError
          ├── SalaryDataNotFoundError
          └── SalaryDataParseError

Usage:
    from core.exceptions import ConnectorRateLimitError, JobNotFoundError
"""


class HeliosError(Exception):
    """Root exception for all Helios errors."""


# ── Connector ─────────────────────────────────────────────────────────────────

class ConnectorError(HeliosError):
    """A connector failed to retrieve or parse job data."""


class ConnectorNotFoundError(ConnectorError):
    """No connector registered for the given name."""


class ConnectorRateLimitError(ConnectorError):
    """The portal returned HTTP 429; back-off required."""


class ConnectorAuthError(ConnectorError):
    """Authentication or authorization failed on the portal."""


class ConnectorParseError(ConnectorError):
    """Failed to parse the portal's response into a Job."""


class ConnectorHealthError(ConnectorError):
    """The portal did not respond to the health check."""


# ── Pipeline ──────────────────────────────────────────────────────────────────

class PipelineError(HeliosError):
    """A pipeline stage encountered an unrecoverable error."""


class NormalizationError(PipelineError):
    """NormalizerStage could not clean or validate a job."""


class DeduplicationError(PipelineError):
    """DeduplicatorStage encountered a database error."""


class EmbeddingError(PipelineError):
    """EmbeddingGeneratorStage failed to produce a vector."""


# ── AI ────────────────────────────────────────────────────────────────────────

class AIEngineError(HeliosError):
    """An AI engine failed to produce output."""


class ProviderError(AIEngineError):
    """The underlying LLM provider API call failed."""


class ProviderRateLimitError(ProviderError):
    """The LLM provider returned a rate limit error."""


class PromptError(AIEngineError):
    """A prompt template was malformed or could not be rendered."""


# ── Domain ────────────────────────────────────────────────────────────────────

class DomainError(HeliosError):
    """A domain entity was not found or in an invalid state."""


class JobNotFoundError(DomainError):
    """No job found for the given ID."""


class CompanyNotFoundError(DomainError):
    """No company found for the given ID or name."""


class ApplicationNotFoundError(DomainError):
    """No application found for the given ID."""


class UserNotFoundError(DomainError):
    """No user found for the given ID or email."""


# ── Data ──────────────────────────────────────────────────────────────────────

class DataError(HeliosError):
    """A data file is missing, malformed, or unreadable."""


class SalaryDataNotFoundError(DataError):
    """salary_data.json does not exist. Run tools/convert_salary_excel.py first."""


class SalaryDataParseError(DataError):
    """salary_data.json exists but could not be parsed."""
