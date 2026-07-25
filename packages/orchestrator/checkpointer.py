"""Checkpoint storage for the public beta."""

from __future__ import annotations


def get_checkpointer():
    """Return a process-local saver with a lifecycle owned by the graph.

    Durable SQLite/Postgres checkpointing remains a documented roadmap item.
    Returning their async context managers here was invalid and prevented graph
    compilation, so the beta uses LangGraph's supported in-memory saver.
    """
    from langgraph.checkpoint.memory import InMemorySaver

    return InMemorySaver()
