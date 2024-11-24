"""A factory to refine schemas."""

from typing import Any, Dict, List, Optional

from sql_ast_dataset.ast_processing.base_ast_processor import BaseMethod
from sql_ast_dataset.ast_processing.query_processor import QueryProcessor


class Factory:
    """A factory to build instances of refining methods."""

    def __init__(self):
        """Initializes the factory."""
        self.supported_methods = {
            "QueryProcessor": QueryProcessor().get_parms(),
        }

    def get_supported_methods(self) -> List[str]:
        """Get the list of supported methods.

        Return:
            A list of string storing the names of the methods.
        """
        return self.supported_methods.keys()

    def get_parms(self, method_name: str) -> Optional[Dict[str, Any]]:
        """Get the supported parameters by a specific method.

        Args:
            method_name: the name of the method.

        Return:
            The dictionary of supported parameters or None.
        """
        if method_name not in self.get_supported_methods():
            return None

        return self.supported_methods[method_name]

    def build(
        self, method_name: str, config_dict: Dict[str, Any]
    ) -> Optional[BaseMethod]:
        """Build an instance of a method.

        Parms:
            method_name: the name of the method.
            config_dict: the configuration dictionary for the method.

        Return:
            An instance that can be used to perform the filtering.
        """
        if method_name not in self.get_supported_methods():
            return None

        method: Optional[BaseMethod] = None
        if method_name == "QueryProcessor":
            method = QueryProcessor()

        if method is None:
            return None

        rc, message = method.set_config(config_dict=config_dict)
        if rc is False:
            print(f"Unable to build {method_name}: {message}")
            return None

        return method
