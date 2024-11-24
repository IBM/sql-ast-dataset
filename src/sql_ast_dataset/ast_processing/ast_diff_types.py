"""Datacalasses and types for the AST diff."""

from dataclasses import dataclass
from typing import Any, List, Optional

from sqlglot import Expression


@dataclass
class QueryASTWord:
    """Class for keeping track of the tokenized query AST."""

    expr_name: str
    label: int
    expr_depth: int = 0
    expr: Optional[Expression] = None
    edit: Optional[Any] = None
    char_index_list: Optional[List[int]] = None  # Indices based on the processed_query


@dataclass
class ASTDiffInput:
    """Class for keeping track of the AST representation of the query."""

    gold_query: str
    query: str
    label: int
    processed_query: str = ""
    query_subwords: Optional[List[QueryASTWord]] = None
    query_ast_diff_subwords: Optional[str] = None
    metadata: Optional[Any] = None

    def query_subword_indices_as_list(self) -> List[List[int]]:
        """Extracts the char indices from the query_subwords."""
        return (
            [
                qsi.char_index_list if qsi.char_index_list is not None else []
                for qsi in self.query_subwords
            ]
            if self.query_subwords is not None
            else []
        )

    def get_labels(self, include_final: bool = False) -> List[int]:
        """Extracts the labels of the AST."""
        labels = (
            [qs.label for qs in self.query_subwords]
            if self.query_subwords is not None
            else []
        )
        if include_final:
            labels.append(self.label)
        return labels
