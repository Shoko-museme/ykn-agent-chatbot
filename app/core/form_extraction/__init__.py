"""Form extraction module initialization.

This module provides form extraction functionality for processing
natural language input into structured form data.
"""

from app.core.form_extraction.base import BaseExecutor, FormExtractionState, should_continue
from app.core.form_extraction.registry import FormExtractionRegistry, get_registry
from app.core.form_extraction.hazard_report import HazardReportExecutor, HazardReportModel

# Register the hazard report executor
registry = get_registry()
registry.register("hazard_report", HazardReportExecutor)

__all__ = [
    "BaseExecutor",
    "FormExtractionState", 
    "should_continue",
    "FormExtractionRegistry",
    "get_registry",
    "HazardReportExecutor",
    "HazardReportModel",
] 