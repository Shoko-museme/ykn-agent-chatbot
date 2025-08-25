# app/core/form_extraction/base.py
from abc import ABC, abstractmethod

class FormExtractionError(Exception):
    """Custom exception for form extraction errors."""
    def __init__(self, message, error_code=None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

class BaseExecutor(ABC):
    """Abstract base class for all form extraction executors."""
    @abstractmethod
    def execute(self, utterance: str) -> dict:
        """
        Executes the form extraction process.

        Args:
            utterance: The user input string.

        Returns:
            A dictionary containing the extracted and validated data.

        Raises:
            FormExtractionError: If any step in the process fails.
        """
        raise NotImplementedError