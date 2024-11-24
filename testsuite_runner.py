"""An utility to trigger all the tests."""

import sys
import unittest
from typing import List

enabled_module_dirs: List[str] = [
    "ast_processing",
]


def perform_tests(module_dirs: List[str]):
    """Performs the tests.

    Args:
        module_dirs: The list of directories from which we look for unit tests.
    """
    for start_dir in module_dirs:
        print(f"Running tests for {start_dir}")
        loader = unittest.TestLoader()

        suite = loader.discover(
            start_dir,
            pattern="*_test.py",
            top_level_dir="./src/sql_ast_dataset",
        )
        runner = unittest.TextTestRunner()
        result = runner.run(suite)

        if not result.wasSuccessful():
            sys.exit(-1)


if __name__ == "__main__":
    perform_tests(enabled_module_dirs)
