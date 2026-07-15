from abc import ABC, abstractmethod
from typing import Any


class ERPProviderError(Exception):
    def __init__(self, message: str, status: str = "error"):
        super().__init__(message)
        self.message = message
        self.status = status


class ERPProvider(ABC):
    provider_id: str
    provider_label: str
    description: str

    @abstractmethod
    def is_configured(self) -> bool:
        """Return whether enough configuration exists to call this provider."""

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """Return a small provider health payload without raising for setup issues."""

    @abstractmethod
    def query_resource(
        self,
        resource: str,
        provider_resource: str,
        query: str | None,
        filters: dict[str, Any] | list[Any] | None,
        fields: list[str],
        limit: int,
    ) -> dict[str, Any]:
        """Query a mapped ERP resource."""

