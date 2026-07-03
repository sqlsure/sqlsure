"""sqlsure — the semantic inspector for SQL.

A semantic constraint checker ("the inspector") that validates SQL against a
dimensional model — grain, join cardinality, measure additivity, join keys,
and column policy — before the query runs. Works on human- or AI-generated SQL.
"""
from .model import SemanticModel
from .checker import check, Violation

__version__ = "0.1.1"
__all__ = ["SemanticModel", "check", "Violation"]
