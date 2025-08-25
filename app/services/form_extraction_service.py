# app/services/form_extraction_service.py
from app.core.form_extraction.registry import form_executor_registry
from app.core.form_extraction.base import FormExtractionError

def run_extraction(utterance: str, form_code: str) -> dict:
    """
    Orchestrates the form extraction process using pre-instantiated singleton executors.
    """
    executor_instance = form_executor_registry.get(form_code)
    if not executor_instance:
        raise ValueError(f"Form executor for code '{form_code}' not found in registry.")

    # 直接调用单例的 execute 方法
    return executor_instance.execute(utterance)
