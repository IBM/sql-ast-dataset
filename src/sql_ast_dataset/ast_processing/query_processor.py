"""Query Processor."""

import re
from typing import Any, Dict, List, Optional, Tuple

import sqlglot
import sqlglot.expressions
from sqlglot.expressions import Column, Expression, Identifier, Limit, Table, TableAlias

from sql_ast_dataset.ast_processing.ast_diff_types import ASTDiffInput, QueryASTWord
from sql_ast_dataset.ast_processing.base_ast_processor import BaseMethod


class QueryProcessor(BaseMethod):
    """A processor that uses the AST of the query."""

    def __init__(self):
        """Initialize the processing method.

        For the configuration following parameters can be set:
        """
        self.config = None
        self.sqlglot_dialect = None

    def get_name(self) -> str:
        """Get the name of the method."""
        return type(self).__name__

    def set_config(self, config_dict: Dict[str, Any]) -> Tuple[bool, str]:
        """Set the configuration.

        Args:
            config_dict: A configuration dictionary for the specific method.

        Return:
            (rc, error_msg)
        """
        # Load the default config
        self.config = self._get_default_dict()
        # Override user specific arguments
        for key, value in config_dict.items():
            self.config[key] = value

        self.sqlglot_dialect = self.config["sqlglot_dialect"]

        return True, ""

    def _get_default_dict(self) -> Dict[str, Any]:
        """Get the configuration parameters for the method.

        Return:
            The configuration parameters as a dictionary.
        """
        return {
            "sqlglot_dialect": "sqlite",
        }

    def get_parms(self) -> Dict[str, Any]:
        """Get the configuration parameters for the method.

        Return:
            The configuration parameters as a dictionary.
        """
        return {
            "sqlglot_dialect": "The dialect to use for parsing.",
        }

    def skip_node(self, expr: Expression) -> bool:
        """Returns if the expr can be skipped.

        Args:
            expr: The Expression.

        Returns:
            True: if the expression should be skipped.
            False: if the expression should be included.
        """
        # We skip Identifiers that were already returned as
        # Columns or Tables
        if (
            isinstance(expr, Identifier)
            and expr.parent
            and isinstance(expr.parent, (Column, Table, TableAlias))
        ):
            return True
        return False

    def _find_node_in_parent(
        self,
        node: Expression,
        node_sql: str,
        available_sql: str,
        left: int,
        char_list: List[Optional[Expression]],
        check_parent: bool = False,
    ) -> int:
        """Find the firs suitable occurance.

        Args:
            node: the current AST node.
            node_sql: the sql string of node.
            available_sql: the sql string of the parent node.
            left: The left char boundary of initial_sql.
            char_list: For each char in initial_sql store the associated
                expression.
            check_parent: If set makes sure that we always find a substring
                that is only occupied by the parent of node.

        Returns:
            The left char index of the node depending on nodes parent. Or -1
            if nothing as found.
        """
        left_index = -1
        start_ind_list = [
            m.start() for m in re.finditer(re.escape(node_sql), available_sql)
        ]

        for start_ind in start_ind_list:
            local_node_left = left + start_ind
            local_node_right = local_node_left + len(node_sql)
            # If there is already an entry with the same string
            if (
                char_list[local_node_left] is not None
                and char_list[local_node_left].sql() == node_sql  # type: ignore
            ):
                pass
                # continue

            if check_parent and node.parent is not None:
                # Check that in the possible positions
                # only the parent exists
                parent_ok = True
                for parent_node in char_list[local_node_left:local_node_right]:
                    if parent_node != node.parent:
                        parent_ok = False
                        break
                if not parent_ok:
                    continue

            left_index = start_ind
            break
        return left_index

    def dfs_simple_node_to_char(
        self,
        node: Expression,
        initial_sql: str,
        left: int,
        right: int,
        char_list: List[Any],
        prune: Any = None,
        check_parent: bool = False,
    ) -> Tuple[int, int]:
        """Best effort of mapping the SQL AST to the char of the string.

        Updates the char_list with pointers to the associated Expressions.

        Args:
            node: The current expression.
            initial_sql: The initial SQL expression as a string.
            left: The left char boundary of initial_sql.
            right: The right char boundry of initial_sql.
            char_list: For each char in initial_sql store the associated
                expression.
            check_parent: If set makes sure that we always find a substring
                that is only occupied by the parent of node.

        Returns:
            The new left and right index.
        """
        if prune and prune(node):
            return left, right

        available_sql = initial_sql[left:right]
        node_sql = node.sql()
        if (
            isinstance(node, sqlglot.expressions.If)
            and node.parent is not None
            and isinstance(node.parent, sqlglot.expressions.Case)
            and node_sql.endswith(" END")
        ):
            # The If seems to be a weird case
            # The string representation of its parent and itself
            # can slightly change.
            node_sql = node_sql[: -len(" END")]

        left_index = self._find_node_in_parent(
            node=node,
            node_sql=node_sql,
            available_sql=available_sql,
            left=left,
            char_list=char_list,
            check_parent=check_parent,
        )

        if left_index == -1:
            # Soemthing went wrong
            raise ValueError(
                (
                    f'SQL node "{node_sql}" was not found in "{available_sql}", '
                    "or all occurrences already occupied.\n"
                    f"Left: {left}. Right: {right}."
                )
            )

        # Computing the new global indices
        node_left = left + left_index
        node_right = node_left + len(node_sql)

        if not self.skip_node(expr=node):
            # Assigning position in array
            char_list[node_left:node_right] = [node] * len(node_sql)

        # Attention this is specific to SQLite
        # In DFS the LIMIT node comes before FROM, WHERE, etc.
        # But this is not conform wiht how we write it.
        limit = None

        for v in node.iter_expressions(reverse=False):
            if isinstance(v, Limit):
                limit = v
                continue
            _, _ = self.dfs_simple_node_to_char(
                node=v,
                initial_sql=initial_sql,
                left=node_left,
                right=node_right,
                char_list=char_list,
                prune=prune,
                check_parent=check_parent,
            )

        if limit is not None:
            _, _ = self.dfs_simple_node_to_char(
                node=limit,
                initial_sql=initial_sql,
                left=node_left,
                right=node_right,
                char_list=char_list,
                prune=prune,
                check_parent=check_parent,
            )

        return node_left, node_right

    def map_node_to_char_index_list(
        self, char_list: List[Expression]
    ) -> Dict[Expression, List[int]]:
        """Maps the node to a char_index_list.

        Args:
            char_list: The list of char to expression nodes.

        Returns:
            A dict that maps an expression to a char_index_list.
        """
        ret: Dict[Expression, List[int]] = {}
        for index, entry in enumerate(char_list):
            ret[entry] = ret.get(entry, []) + [index]
        return ret

    def process(self, sql_query_1: str, sql_query_2: str, label: int) -> ASTDiffInput:
        """Constructs a QuerySubword list of the two SQL queries.

        Args:
            sql_query_1: The original/wrong query.
            sql_query_2: The ideal/gold query.
            label: The label if the query is correct.

        Returns:
            An instance of ASTDiffInput.
        """
        parsed_sql_query_1 = sqlglot.parse_one(
            sql_query_1, dialect=self.sqlglot_dialect
        )
        sql_query_1 = parsed_sql_query_1.sql()  # To make it consistent
        parsed_sql_query_2 = sqlglot.parse_one(
            sql_query_2, dialect=self.sqlglot_dialect
        )
        sql_query_2 = parsed_sql_query_2.sql()  # To make it consistent

        # Map each char to its node
        char_list = [None] * len(sql_query_1)
        self.dfs_simple_node_to_char(
            node=parsed_sql_query_1,
            initial_sql=sql_query_1,
            left=0,
            right=len(sql_query_1),
            char_list=char_list,
            check_parent=True,
        )
        node_map_to_char_index_list = self.map_node_to_char_index_list(
            char_list=char_list  # type: ignore
        )

        # Create the difference between the sql nodes
        diff_1_2 = sqlglot.diff(parsed_sql_query_1, parsed_sql_query_2)
        a_ast_list: List[QueryASTWord] = []

        for expr in parsed_sql_query_1.walk(bfs=False):
            expr_name = expr.sql()

            char_index_list: Optional[List[int]] = node_map_to_char_index_list.get(
                expr, None
            )
            if char_index_list is None:
                continue

            node_label, possible_edit = self.get_unchanged_label_and_edit(
                expr=expr, query_diff=diff_1_2
            )

            if label == 1 and node_label != 1:
                raise ValueError(
                    (
                        f"AST diff was not able to match {expr.sql()}"
                        " to a correct counterpart."
                    )
                )

            # For the root node we assume
            # it is always a SELECT
            if expr == parsed_sql_query_1:
                node_label = 1

            a_ast_list.append(
                QueryASTWord(
                    expr_name=expr_name,
                    label=node_label,
                    expr_depth=expr.depth,
                    expr=expr,
                    edit=possible_edit,
                    char_index_list=char_index_list,
                )
            )

        # The metadata
        metadata = {
            "ast_processor_name": self.get_name(),
            "ast_processor_config": self.config,
        }

        return ASTDiffInput(
            gold_query=sql_query_2,
            query=sql_query_1,
            label=label,
            processed_query=sql_query_1,
            query_subwords=a_ast_list,
            metadata=metadata,
        )
