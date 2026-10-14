from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver


_memory_saver = MemorySaver()


def get_memory_saver() -> BaseCheckpointSaver:
    """Return an in-memory checkpointer for local demos."""
    return _memory_saver
