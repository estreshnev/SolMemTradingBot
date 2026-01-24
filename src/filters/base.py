from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

from src.models.events import BaseEvent

T = TypeVar("T", bound=BaseEvent)


@dataclass
class FilterResult:
    """Result of a filter evaluation."""

    passed: bool
    reason: str | None = None

    @classmethod
    def accept(cls) -> "FilterResult":
        return cls(passed=True)

    @classmethod
    def reject(cls, reason: str) -> "FilterResult":
        return cls(passed=False, reason=reason)


class BaseFilter(ABC, Generic[T]):
    """Base class for all filters. Implement `evaluate` to add custom logic."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Filter name for logging."""
        ...

    @abstractmethod
    async def evaluate(self, event: T) -> FilterResult:
        """Evaluate the event against this filter."""
        ...


class FilterChain(Generic[T]):
    """Chain of filters applied sequentially. Stops on first rejection."""

    def __init__(self, filters: list[BaseFilter[T]] | None = None):
        self._filters: list[BaseFilter[T]] = filters or []

    def add(self, filter_: BaseFilter[T]) -> "FilterChain[T]":
        """Add a filter to the chain. Returns self for chaining."""
        self._filters.append(filter_)
        return self

    async def evaluate(self, event: T) -> FilterResult:
        """Run all filters. Returns first rejection or final accept."""
        for f in self._filters:
            result = await f.evaluate(event)
            if not result.passed:
                return FilterResult.reject(f"{f.name}: {result.reason}")
        return FilterResult.accept()

    @property
    def filters(self) -> list[BaseFilter[T]]:
        return self._filters
