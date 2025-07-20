"""Form extraction registry.

This module manages the registry of form extractors, mapping form codes
to their corresponding executor classes.
"""

from typing import Dict, Type

from app.core.form_extraction.base import BaseExecutor
from app.core.logging import logger


class FormExtractionRegistry:
    """Registry for form extraction executors.
    
    This class manages the mapping between form codes and their corresponding
    executor classes. It provides methods to register new extractors and
    retrieve them by form code.
    """
    
    def __init__(self):
        """Initialize the registry."""
        self._executors: Dict[str, Type[BaseExecutor]] = {}
    
    def register(self, form_code: str, executor_class: Type[BaseExecutor]) -> None:
        """Register a form extractor.
        
        Args:
            form_code: The form code identifier (e.g., "hazard_report")
            executor_class: The executor class that inherits from BaseExecutor
            
        Raises:
            ValueError: If form_code is already registered
        """
        if form_code in self._executors:
            logger.warning("form_code_already_registered", form_code=form_code)
            raise ValueError(f"Form code '{form_code}' is already registered")
        
        # Validate that the executor class inherits from BaseExecutor
        if not issubclass(executor_class, BaseExecutor):
            raise ValueError(f"Executor class must inherit from BaseExecutor")
        
        self._executors[form_code] = executor_class
        logger.info("form_extractor_registered", form_code=form_code, executor_class=executor_class.__name__)
    
    def get_executor(self, form_code: str) -> BaseExecutor:
        """Get an executor instance for the given form code.
        
        Args:
            form_code: The form code identifier
            
        Returns:
            BaseExecutor: An instance of the executor for the given form code
            
        Raises:
            ValueError: If form_code is not registered
        """
        if form_code not in self._executors:
            logger.error("form_code_not_found", form_code=form_code, available_codes=list(self._executors.keys()))
            raise ValueError(f"Form code '{form_code}' is not registered")
        
        executor_class = self._executors[form_code]
        return executor_class()
    
    def is_registered(self, form_code: str) -> bool:
        """Check if a form code is registered.
        
        Args:
            form_code: The form code identifier
            
        Returns:
            bool: True if the form code is registered, False otherwise
        """
        return form_code in self._executors
    
    def get_registered_codes(self) -> list[str]:
        """Get all registered form codes.
        
        Returns:
            list[str]: List of all registered form codes
        """
        return list(self._executors.keys())
    
    def unregister(self, form_code: str) -> None:
        """Unregister a form extractor.
        
        Args:
            form_code: The form code identifier to unregister
            
        Raises:
            ValueError: If form_code is not registered
        """
        if form_code not in self._executors:
            raise ValueError(f"Form code '{form_code}' is not registered")
        
        del self._executors[form_code]
        logger.info("form_extractor_unregistered", form_code=form_code)


# Global registry instance
registry = FormExtractionRegistry()


def get_registry() -> FormExtractionRegistry:
    """Get the global form extraction registry.
    
    Returns:
        FormExtractionRegistry: The global registry instance
    """
    return registry 