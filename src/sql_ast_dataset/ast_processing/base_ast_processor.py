"""A base refiner."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, Optional, Tuple, Union

from sqlglot.diff import Insert, Keep, Move, Remove, Update
from sqlglot.expressions import Column, Expression, Identifier, Join, Table, TableAlias

from sql_ast_dataset.ast_processing.ast_diff_types import ASTDiffInput


class BaseMethod(ABC):
    """A base method to create ASTDiffInputs."""

    @abstractmethod
    def set_config(self, config_dict: Dict[str, Any]) -> Tuple[bool, str]:
        """Set the configuration.

        Args:
            config_dict: A configuration dictionary for the specific method.

        Return:
            (rc, error_msg)
        """

    @abstractmethod
    def get_name(self) -> str:
        """Get the name of the method."""

    @abstractmethod
    def get_parms(self) -> Dict[str, Any]:
        """Get the configuration parameters for the method.

        Return:
            The configuration parameters as a dictionary.
        """

    @abstractmethod
    def process(
        self,
        sql_query_1: str,
        sql_query_2: str,
        label: int,
    ) -> ASTDiffInput:
        """Constructs a QuerySubword list of the two SQL queries.

        Args:
            sql_query_1: The original/wrong query.
            sql_query_2: The ideal/gold query.
            label: The label if the query is correct.

        Returns:
            An instance of ASTDiffInput.
        """

    def overwrite_hash_of_expression(
        self, expression_itr: Iterable[Expression]
    ) -> None:
        """Overwrites the hash of expressions.

        Unfortunately the diff functions makes deep-copies of
        the expression and therefore we can not map the
        Expressions to the original ones. Workaround, overwrite
        each hash value of the sql-glot entry. This makes every
        expression in the iterator unique but may have unforseen
        consequences.

        Example:
            overwrite_hash_of_expression(chain(expr_1.walk(), expr_2.walk())

        Args:
            expression_itr: An iterable over Expressions.
        """
        count = 0
        for current_node in expression_itr:
            current_node.set("_hash", count)
            count += 1

    def remove_children_of_node(
        self, expression: Expression, inplace: bool = False
    ) -> Expression:
        """Removes all child expressions of a node.

        Args:
            expression: The SQL expression.
            inplace: If it should be done inplace.

        Returns:
            The expression without its children, if inplace is false,
            a copy of the expression is returned.
        """
        local_expr = expression
        if not inplace:
            local_expr = expression.copy()
        # Removes all childrens
        for expr in list(local_expr.iter_expressions()):
            expr.pop()
        return local_expr

    def get_unchanged_label_and_edit(
        self, expr: Expression, query_diff: Any
    ) -> Tuple[int, Optional[Any]]:
        """Extracts possible label and edit corresponding to expression.

        Args:
            expr: The expression to check which operation is associated
                in the AST difference.
            query_diff: The AST difference between two SQL queries.

        Returns:
            A Tuple with the label as its first entry and optionally the
            AST difference of expr.
        """
        label = 1
        ret: Any = None
        for index, edit in enumerate(query_diff):
            # Edit already used
            if edit is None:
                continue
            # Not relevant for us
            if isinstance(edit, Insert):
                continue
            # label is 0 when the epxpression has been removed
            elif isinstance(edit, Remove):
                if edit.expression == expr:
                    label = 0
                    ret = edit
                    query_diff[index] = None
                    break
            elif isinstance(edit, Move):
                # We just skip this operation.
                # if edit.expression == expr:
                continue
            elif isinstance(edit, Update):
                if edit.source == expr:
                    # We check if the column names and table names are the same
                    if (
                        (
                            (
                                isinstance(edit.source, Column)
                                and isinstance(edit.target, Column)
                            )
                            or (
                                isinstance(edit.source, Table)
                                and isinstance(edit.target, Table)
                            )
                        )
                        and isinstance(edit.source.this, Identifier)
                        and isinstance(edit.target.this, Identifier)
                    ):
                        # It is not a perfect check since the tablename of
                        # the columns could be wrong, but with the aliases
                        # there is no easy way to check.
                        if (
                            edit.source.this.quoted is True
                            or edit.target.this.quoted is True
                        ):
                            # If one of them is quoted we assume case sensitivity.
                            if edit.source.this.this == edit.target.this.this:
                                label = 1
                            else:
                                label = 0
                        else:
                            # If none of them are quoted we assume case insensitivty.
                            if (
                                str(edit.source.this.this).lower()
                                == str(edit.target.this.this).lower()
                            ):
                                label = 1
                            else:
                                label = 0
                    else:
                        label = 0
                    ret = edit
                    query_diff[index] = None
                    break
            elif isinstance(edit, Keep) and edit.source == expr:
                label = 1
                ret = edit
                query_diff[index] = None
                break
        return label, ret

    def get_label_and_edit(
        self, expr: Expression, query_diff: Any
    ) -> Tuple[int, Optional[Any]]:
        """Extracts possible label and edit corresponding to expression.

        Args:
            expr: The expression to check which operation is associated
                in the AST difference.
            query_diff: The AST difference between two SQL queries.

        Returns:
            A Tuple with the label as its first entry and optionally the
            AST difference of expr.
        """
        label = 1
        ret: Any = None
        for edit in query_diff:
            # Not relevant for us
            if isinstance(edit, Insert):
                pass
            # label is 0 when the epxpression has been updated or removed
            elif isinstance(edit, (Remove, Move)):
                if edit.expression == expr:
                    label = 0
                    ret = edit
            elif isinstance(edit, Update):
                # Second check due to chenged hash
                if edit.source == expr:
                    if edit.source.sql() != edit.target.sql():
                        label = 0
                    ret = edit
            elif isinstance(edit, Keep) and edit.source == expr:
                ret = edit
        return label, ret

    def _get_join_name(self, expr: Join) -> str:
        """Extracts simple name of the join.

        Args:
            expr: The join expression.

        Returns:
            A string wiht a simpliefied name for the join.
        """
        ret = ""
        if "side" in expr.args and expr.args["side"]:
            ret += expr.args["side"] + " "
        if "kind" in expr.args and expr.args["kind"]:
            ret += expr.args["kind"] + " "
        ret += "JOIN"
        if "on" in expr.arg_types:
            ret += " ON"
        return ret

    def get_expression_name(
        self,
        expr: Expression,
        skip_expressions: Optional[Union[Any, Tuple[Any, ...]]] = TableAlias,
    ) -> Optional[str]:
        """Returns the expression name for diff_expression.

        Args:
            expr: The expression to get the name.
            skip_expressions: Expressions to skip.

        Returns:
            A simplified name of the expression or None. None gets returned
            if we skip it or if the expression is an Identifier and a child
            from a Column or Table.
        """
        # We skip Identifiers that were already returned as
        # Columns or Tables
        if (
            isinstance(expr, Identifier)
            and expr.parent
            and isinstance(expr.parent, (Column, Table, TableAlias))
        ):
            return None
        # Skip expressions if specified
        if skip_expressions and isinstance(expr, skip_expressions):
            return None
        # Returns Column and Tables as is
        if isinstance(expr, (Column, Table)):
            return expr.sql()

        # Joins have to be done manually
        if isinstance(expr, Join):
            return self._get_join_name(expr=expr)

        # Otherwise remove all children nodes and return
        # the representation of the expression
        expr_only = self.remove_children_of_node(expression=expr)
        return expr_only.sql()

    def is_insertion_in_diff(self, query_diff: Any) -> int:
        """Checks if an Insert is in the diff.

        Args:
            query_diff: the diff expression.

        Returns:
            An bool as int, that is 1 if query_diff
            is an Insert expression.
        """
        for edit in query_diff:
            if isinstance(edit, Insert):
                return 1
        return 0
