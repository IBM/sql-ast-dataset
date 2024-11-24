"""Functionality to parse a SQL query for the AST predictions."""

from itertools import chain
from typing import Any, List, Optional, Tuple, Union

from sqlglot import Expression, diff, parse_one
from sqlglot.diff import Insert, Keep, Move, Remove, Update
from sqlglot.expressions import Column, Identifier, Join, Table, TableAlias

from sql_ast_dataset.ast_processing.ast_diff_types import QuerySubword


def remove_children_of_node(
    expression: Expression, inplace: bool = False
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


def get_label_and_edit(expr: Expression, query_diff: Any) -> Tuple[int, Optional[Any]]:
    """Extracts possible label and edit corresponding to expression."""
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


def _get_join_name(expr: Join) -> Optional[str]:
    """Extracts the name of the join."""
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
    expr: Expression,
    skip_expressions: Optional[Union[Any, Tuple[Any, ...]]] = TableAlias,
) -> Optional[str]:
    """Returns the expression name for diff_expression."""
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
        return _get_join_name(expr=expr)

    # Otherwise remove all children nodes and return
    # the representation of the expression
    expr_only = remove_children_of_node(expression=expr)
    return expr_only.sql()


def is_insertion_in_diff(query_diff: Any) -> int:
    """Checks if an Insert is in the diff."""
    for edit in query_diff:
        if isinstance(edit, Insert):
            return 1
    return 0


def extract_diff_expressions(
    sql_query_1: Union[str, Expression],
    sql_query_2: Union[str, Expression],
    add_insertion_token: bool = True,
    add_expression_references: bool = False,
) -> List[QuerySubword]:
    """Constructs List of the two SQL queries.

    Args:
        sql_query_1: The original/wrong query.
        sql_query_2: The ideal/gold query.
        add_insertion_token: adds entry at the end
            for expressions that are not included
            in sql_query_1 but needed to get to
            sql_query_2 (Insert).
        add_expression_references: If set also adds
            references to the expression and
            edit of the difference.

    Returns:
        A list of dicts with the key:
            - expr_name: The name of the expression.
            - label: The binary label if the
                    expression in sql_query_1 is
                    part of sql_query_2.
    """
    if isinstance(sql_query_1, str):
        sql_query_1 = parse_one(sql_query_1)
    else:
        sql_query_1 = sql_query_1.copy()

    if isinstance(sql_query_2, str):
        sql_query_2 = parse_one(sql_query_2)
    else:
        sql_query_2 = sql_query_2.copy()

    assert isinstance(sql_query_1, Expression)
    assert isinstance(sql_query_2, Expression)

    # Unfortunately the diff functions makes deep-copies of
    # the expression and therefore we can not map the
    # Expressions to the original ones. Workaround, overwrite
    # each hash value of the sql-glot entry. This makes every
    # expression unique but may have unforseen consequences.
    count = 0
    for current_node in chain(sql_query_1.walk(), sql_query_2.walk()):
        current_node.set("_hash", count)
        count += 1

    diff_1_2 = diff(sql_query_1, sql_query_2)
    ret: List[QuerySubword] = []

    for expr in sql_query_1.walk(bfs=False):
        expr_name = get_expression_name(expr=expr)
        if not expr_name:
            continue
        label, possible_edit = get_label_and_edit(expr=expr, query_diff=diff_1_2)
        # For the root node we assume
        # it is always a SELECT
        if expr == sql_query_1:
            label = 1

        qsw = QuerySubword(expr_name=expr_name, label=label, expr_depth=expr.depth)
        if add_expression_references:
            qsw.expr = expr
            qsw.edit = possible_edit

        ret.append(qsw)
    # CONSIDRE: For each subtask
    if add_insertion_token:
        # Adding a special token at the end indicating if the
        # expression is missing a token.
        label = 1 - is_insertion_in_diff(query_diff=diff_1_2)
        ret.append(
            QuerySubword(
                expr_name="No additional Expressions needed",
                label=label,
                is_special_token=True,
            )
        )

    return ret
