"""Task-scoped admission ledger for model and tool calls."""

from __future__ import annotations

import asyncio
from contextvars import ContextVar, Token
from dataclasses import dataclass


class BudgetExceededError(RuntimeError):
    """Raised before an external call when the task budget is exhausted."""


@dataclass(frozen=True, slots=True)
class BudgetSnapshot:
    model_calls: int
    tool_calls: int
    max_model_calls: int
    max_tool_calls: int


class BudgetLedger:
    def __init__(self, *, max_model_calls: int, max_tool_calls: int) -> None:
        self.max_model_calls = max_model_calls
        self.max_tool_calls = max_tool_calls
        self._model_calls = 0
        self._tool_calls = 0
        self._lock = asyncio.Lock()

    async def reserve_model_call(self) -> int:
        async with self._lock:
            if self._model_calls >= self.max_model_calls:
                raise BudgetExceededError("task model-call budget exhausted")
            self._model_calls += 1
            return self._model_calls

    async def reserve_tool_calls(self, count: int) -> int:
        if count < 0:
            raise ValueError("tool call count cannot be negative")
        async with self._lock:
            if self._tool_calls + count > self.max_tool_calls:
                raise BudgetExceededError("task tool-call budget exhausted")
            self._tool_calls += count
            return self._tool_calls

    def snapshot(self) -> BudgetSnapshot:
        return BudgetSnapshot(
            model_calls=self._model_calls,
            tool_calls=self._tool_calls,
            max_model_calls=self.max_model_calls,
            max_tool_calls=self.max_tool_calls,
        )


_current_ledger: ContextVar[BudgetLedger | None] = ContextVar(
    "swarm_task_budget",
    default=None,
)


def bind_budget(ledger: BudgetLedger) -> Token[BudgetLedger | None]:
    return _current_ledger.set(ledger)


def reset_budget(token: Token[BudgetLedger | None]) -> None:
    _current_ledger.reset(token)


def current_budget() -> BudgetLedger | None:
    return _current_ledger.get()
