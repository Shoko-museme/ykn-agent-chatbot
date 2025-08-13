"""Form extraction base classes and state definition.

This module provides the foundation for form extraction functionality,
including the state definition and base executor class that all
specific form extractors should inherit from.
"""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional, TypedDict

from jinja2 import Environment, FileSystemLoader, Template
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from openai import OpenAIError
from pathlib import Path
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.core.logging import logger


class FormExtractionState(TypedDict):
    """State for form extraction workflow.
    
    All nodes in the form extraction graph should use this state structure
    to ensure type safety and consistency across the workflow.
    """
    utterance: str                          # 原始用户输入
    form_code: str                         # 表单标识码
    prompt: Optional[str]                  # 生成的提示词
    raw_json: Optional[str]                # LLM返回的原始JSON字符串
    data: Optional[Dict[str, Any]]         # 解析后的数据字典
    validated_data: Optional[Dict[str, Any]] # 校验后的数据
    result: Optional[Dict[str, Any]]       # 最终结果
    error_code: Optional[str]              # 错误码
    error_message: Optional[str]           # 详细错误信息


class BaseExecutor(ABC):
    """Base executor for form extraction.
    
    This class provides the common execution logic for all form extractors.
    Specific form types should inherit from this class and implement the
    required abstract methods.
    """
    
    def __init__(self):
        """Initialize the base executor."""
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=settings.DEFAULT_LLM_TEMPERATURE,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_URL,
            max_tokens=settings.MAX_TOKENS,
        )
        self.template_env = Environment(
            loader=FileSystemLoader(Path(__file__).parent / "templates")
        )
    
    @abstractmethod
    def get_template_name(self) -> str:
        """Get the template file name for this form type.
        
        Returns:
            str: Template file name (e.g., "hazard_report.jinja2")
        """
        pass
    
    @abstractmethod
    def get_validation_model(self) -> type[BaseModel]:
        """Get the Pydantic model for validation.
        
        Returns:
            type[BaseModel]: Pydantic model class for validation
        """
        pass
    
    @abstractmethod
    def post_process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Post-process the validated data.
        
        Args:
            data: Validated data from Pydantic model
            
        Returns:
            Dict[str, Any]: Post-processed data
        """
        pass
    
    def load_template(self) -> Template:
        """Load the Jinja2 template for this form type.
        
        Returns:
            Template: Loaded Jinja2 template
            
        Raises:
            FileNotFoundError: If template file is not found
        """
        try:
            return self.template_env.get_template(self.get_template_name())
        except Exception as e:
            logger.error("template_load_error", template=self.get_template_name(), error=str(e))
            raise FileNotFoundError(f"Template {self.get_template_name()} not found")
    
    def prompt_node(self, state: FormExtractionState) -> FormExtractionState:
        """Generate prompt from template.
        
        Args:
            state: Current form extraction state
            
        Returns:
            FormExtractionState: Updated state with prompt
        """
        try:
            template = self.load_template()
            prompt = template.render(user_input=state["utterance"])
            state["prompt"] = prompt
            logger.info("prompt_generated", form_code=state["form_code"], prompt_length=len(prompt))
        except Exception as e:
            logger.error("prompt_generation_error", form_code=state["form_code"], error=str(e))
            state["error_code"] = "TASK_INTERNAL_ERROR"
            state["error_message"] = f"Failed to generate prompt: {str(e)}"
        
        return state
    
    def llm_node(self, state: FormExtractionState) -> FormExtractionState:
        """Call LLM to extract form data.
        
        Args:
            state: Current form extraction state
            
        Returns:
            FormExtractionState: Updated state with LLM response
        """
        if state.get("error_code"):
            return state
            
        try:
            messages = [HumanMessage(content=state["prompt"])]
            response = self.llm.invoke(messages)
            
            if isinstance(response, AIMessage):
                state["raw_json"] = response.content
            else:
                state["raw_json"] = str(response)
                
            logger.info("llm_response_received", form_code=state["form_code"], response_length=len(state["raw_json"]))
            
        except OpenAIError as e:
            logger.error("llm_error", form_code=state["form_code"], error=str(e))
            state["error_code"] = "TASK_LLM_INNER_ERROR"
            state["error_message"] = f"LLM call failed: {str(e)}"
        except Exception as e:
            logger.error("llm_unexpected_error", form_code=state["form_code"], error=str(e))
            state["error_code"] = "TASK_INTERNAL_ERROR"
            state["error_message"] = f"Unexpected error during LLM call: {str(e)}"
        
        return state
    
    def parse_node(self, state: FormExtractionState) -> FormExtractionState:
        """Parse JSON response from LLM.
        
        Args:
            state: Current form extraction state
            
        Returns:
            FormExtractionState: Updated state with parsed data
        """
        if state.get("error_code"):
            return state
            
        try:
            # Clean the response - remove any non-JSON content
            raw_json = state["raw_json"].strip()
            
            # Try to extract JSON from markdown code blocks
            if "```json" in raw_json:
                start = raw_json.find("```json") + 7
                end = raw_json.find("```", start)
                if end > start:
                    raw_json = raw_json[start:end].strip()
            elif "```" in raw_json:
                start = raw_json.find("```") + 3
                end = raw_json.find("```", start)
                if end > start:
                    raw_json = raw_json[start:end].strip()
            
            # Parse JSON
            data = json.loads(raw_json)
            state["data"] = data
            logger.info("json_parsed_successfully", form_code=state["form_code"], fields_count=len(data))
            
        except json.JSONDecodeError as e:
            logger.error("json_parse_error", form_code=state["form_code"], error=str(e), raw_json=state["raw_json"])
            state["error_code"] = "TASK_INVALID_RESPONSE"
            state["error_message"] = f"Failed to parse JSON response: {str(e)}"
        except Exception as e:
            logger.error("parse_unexpected_error", form_code=state["form_code"], error=str(e))
            state["error_code"] = "TASK_INTERNAL_ERROR"
            state["error_message"] = f"Unexpected error during parsing: {str(e)}"
        
        return state
    
    def validate_node(self, state: FormExtractionState) -> FormExtractionState:
        """Validate parsed data using Pydantic model.
        
        Args:
            state: Current form extraction state
            
        Returns:
            FormExtractionState: Updated state with validated data
        """
        if state.get("error_code"):
            return state
            
        try:
            validation_model = self.get_validation_model()
            validated_instance = validation_model(**state["data"])
            state["validated_data"] = validated_instance.model_dump()
            logger.info("validation_successful", form_code=state["form_code"])
            
        except ValidationError as e:
            logger.error("validation_error", form_code=state["form_code"], error=str(e))
            state["error_code"] = "TASK_VALIDATION_ERROR"
            state["error_message"] = f"Validation failed: {str(e)}"
        except Exception as e:
            logger.error("validation_unexpected_error", form_code=state["form_code"], error=str(e))
            state["error_code"] = "TASK_INTERNAL_ERROR"
            state["error_message"] = f"Unexpected error during validation: {str(e)}"
        
        return state
    
    def post_process_node(self, state: FormExtractionState) -> FormExtractionState:
        """Apply post-processing to validated data.
        
        Args:
            state: Current form extraction state
            
        Returns:
            FormExtractionState: Updated state with final result
        """
        if state.get("error_code"):
            return state
            
        try:
            # Expose utterance to executor for rule-based post processing needs
            try:
                setattr(self, "_utterance", state.get("utterance"))
            except Exception:
                pass

            result = self.post_process(state["validated_data"])
            state["result"] = result
            logger.info("post_processing_complete", form_code=state["form_code"])
            
        except Exception as e:
            logger.error("post_process_error", form_code=state["form_code"], error=str(e))
            state["error_code"] = "TASK_INTERNAL_ERROR"
            state["error_message"] = f"Post-processing failed: {str(e)}"
        
        return state
    
    def error_node(self, state: FormExtractionState) -> FormExtractionState:
        """Handle errors and prepare error response.
        
        Args:
            state: Current form extraction state
            
        Returns:
            FormExtractionState: Updated state with error information
        """
        logger.error(
            "form_extraction_error",
            form_code=state["form_code"],
            error_code=state.get("error_code"),
            error_message=state.get("error_message")
        )
        
        # Ensure we have a result even in error case
        if not state.get("result"):
            state["result"] = {
                "error": True,
                "error_code": state.get("error_code", "TASK_INTERNAL_ERROR"),
                "error_message": state.get("error_message", "Unknown error occurred")
            }
        
        return state


def should_continue(state: FormExtractionState) -> bool:
    """Check if the workflow should continue or go to error handling.
    
    Args:
        state: Current form extraction state
        
    Returns:
        bool: True if no error, False if error occurred
    """
    return state.get("error_code") is None 