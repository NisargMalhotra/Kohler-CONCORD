"""KOHLER CONCORD — Evaluation module."""

__all__ = ["EvalRunner"]


def __getattr__(name: str):
    if name == "EvalRunner":
        from eval.runner import EvalRunner
        return EvalRunner
    raise AttributeError(f"module 'eval' has no attribute {name!r}")
