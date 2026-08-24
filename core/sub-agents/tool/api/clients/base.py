"""Synchronous provider base for the API runner."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class ProviderName(str, Enum):
    """Enum of all supported providers."""
    DEEPSEEK = "deepseek"
    GEMINI = "gemini"
    OPENAI = "openai"
    MANUS = "manus"
    KIMI = "kimi"
    QWEN = "qwen"
    ANTHROPIC = "anthropic"
    COHERE = "cohere"


@dataclass
class Message:
    """Standard message format."""
    role: str  # "user", "assistant", "system"
    content: Union[str, List[Dict[str, Any]]]


@dataclass
class TokenUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass
class Artifact:
    """A file deliverable fetched from a provider (e.g. a Manus attachment)."""
    filename: str
    content: bytes
    content_type: Optional[str] = None
    source_url: Optional[str] = None


@dataclass
class Response:
    content: str
    model: Optional[str] = None
    usage: Optional[TokenUsage] = None
    raw_response: Optional[Dict[str, Any]] = None
    artifacts: Optional[List["Artifact"]] = None
    structured_result: Optional[Dict[str, Any]] = None


@dataclass
class ProviderConfig:
    api_key: str
    base_url: Optional[str] = None
    timeout: Optional[int] = None
    retries: Optional[int] = None
    extra_params: Optional[Dict[str, Any]] = None


@dataclass
class RequestOptions:
    model: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    stop_sequences: Optional[List[str]] = None
    extra_params: Optional[Dict[str, Any]] = None


class ProviderClient(ABC):
    structured_output: bool = True

    @property
    @abstractmethod
    def name(self) -> ProviderName: ...

    @abstractmethod
    def initialize(self, config: ProviderConfig) -> None: ...

    @abstractmethod
    def chat(self, messages: List[Message], options: Optional[RequestOptions] = None) -> Response: ...
