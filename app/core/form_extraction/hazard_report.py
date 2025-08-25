"""Hazard report form extraction implementation.

This module implements the specific executor and validation model
for the hazard_report form type.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import (BaseModel, Field, ValidationError, field_validator,
                    model_validator)

from app.core.config import settings
from app.core.form_extraction.base import BaseExecutor, FormExtractionError
from app.core.logging import logger


def get_current_date() -> str:
    """Get current date in YYYYMMDD format."""
    return datetime.now().strftime("%Y%m%d")


class HazardReportModel(BaseModel):
    """Pydantic model for hazard report form validation.
    
    This model defines the structure and validation rules for the
    hazard report form fields.
    """
    
    # Required fields
    underCheckOrg: str = Field(..., description="被检查部门")
    checkDate: str = Field(default_factory=get_current_date, description="检查日期 (YYYYMMDD)")
    hiddenTroubleLevel: int = Field(default=7, description="隐患级别")
    checkType: int = Field(default=1, description="检查类型")
    hiddenTroubleType: Optional[int] = Field(default=None, description="隐患类别")
    illegalType: Optional[int] = Field(default=None, description="隐患标签")
    
    # Optional fields
    checkMoney: Optional[float] = Field(default=None, description="考核金额(元)")
    checkScore: Optional[int] = Field(default=None, description="考核分数")
    checkLeader: Optional[int] = Field(default=None, description="带队领导")
    
    @field_validator("checkDate")
    @classmethod
    def validate_check_date(cls, v: Optional[str]) -> str:
        """Validate and normalize check date."""
        if not v:
            return get_current_date()
        
        date_digits = re.sub(r'\D', '', v)
        
        if len(date_digits) == 4:
            current_year = datetime.now().year
            date_digits = f"{current_year}{date_digits}"
        elif len(date_digits) == 6:
            date_digits = f"20{date_digits}"
        elif len(date_digits) != 8:
            logger.warning("invalid_checkDate_format", value=v)
            return get_current_date()
        
        try:
            datetime.strptime(date_digits, "%Y%m%d")
        except ValueError:
            logger.warning("invalid_checkDate_value", value=v)
            return get_current_date()
        
        return date_digits
    
    @field_validator("hiddenTroubleLevel")
    @classmethod
    def validate_hidden_trouble_level(cls, v: int) -> int:
        """Validate hidden trouble level."""
        valid_levels = {5, 6, 7, 8}
        if v not in valid_levels:
            logger.warning("invalid_hiddenTroubleLevel", value=v)
            return 7
        return v
    
    @field_validator("checkType")
    @classmethod
    def validate_check_type(cls, v: int) -> int:
        """Validate check type."""
        valid_types = {1, 3, 4, 5, 6, 8}
        if v not in valid_types:
            logger.warning("invalid_checkType", value=v)
            return 1
        return v
    
    @field_validator("hiddenTroubleType")
    @classmethod
    def validate_hidden_trouble_type(cls, v: Optional[int]) -> Optional[int]:
        """Validate hidden trouble type."""
        valid_types = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18}
        if v is not None and v not in valid_types:
            logger.warning("invalid_hiddenTroubleType", value=v)
            return None
        return v
    
    @field_validator("illegalType")
    @classmethod
    def validate_illegal_type(cls, v: Optional[int]) -> Optional[int]:
        """Validate illegal type."""
        valid_types = {1, 2, 3, 4}
        if v is not None and v not in valid_types:
            logger.warning("invalid_illegalType", value=v)
            return None
        return v
    
    @field_validator("checkLeader")
    @classmethod
    def validate_check_leader(cls, v: Optional[int]) -> Optional[int]:
        """Validate check leader."""
        if v is not None:
            valid_leaders = {1, 2, 3, 4, 6, 7, 8, 9, 10, 11, 13, 14}
            if v not in valid_leaders:
                logger.warning("invalid_checkLeader", value=v)
                return None
        return v
    
    @model_validator(mode='after')
    def validate_conditional_fields(self) -> 'HazardReportModel':
        """Validate conditional required fields."""
        if self.checkType == 8 and self.checkLeader is None:
            logger.warning("missing_checkLeader", checkType=self.checkType)
        return self


class HazardReportExecutor(BaseExecutor):
    """Executor for hazard report form extraction."""

    def __init__(self):
        """Initialize the executor."""
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
        self.pydantic_model = HazardReportModel
        try:
            self.template = self.template_env.get_template("hazard_report.jinja2")
        except Exception as e:
            logger.error("template_load_error", template="hazard_report.jinja2", error=str(e))
            raise FormExtractionError(
                f"Template hazard_report.jinja2 not found: {e}",
                error_code="TASK_INTERNAL_ERROR"
            )

    def _generate_prompt(self, utterance: str) -> str:
        """Generates the prompt for the LLM."""
        return self.template.render(user_input=utterance)

    def _call_llm(self, prompt: str) -> str:
        """Calls the language model and returns the raw response."""
        try:
            messages = [HumanMessage(content=prompt)]
            response = self.llm.invoke(messages)
            content = response.content if isinstance(response, AIMessage) else str(response)
            logger.info("llm_response_received", response_length=len(content))
            return content
        except Exception as e:
            logger.error("llm_error", error=str(e))
            raise FormExtractionError(f"LLM call failed: {e}", error_code="TASK_LLM_INNER_ERROR")

    def _clean_and_parse_json(self, raw_json: str) -> dict:
        """Cleans and parses the JSON string from the LLM."""
        cleaned_str = raw_json.strip()
        
        match = re.search(r"```(json)?(.*)```", cleaned_str, re.DOTALL)
        if match:
            cleaned_str = match.group(2).strip()

        try:
            data = json.loads(cleaned_str)
            logger.info("json_parsed_successfully", fields_count=len(data))
            return data
        except json.JSONDecodeError as e:
            logger.error("json_parse_error", error=str(e), raw_json=raw_json)
            raise FormExtractionError(f"LLM output is not valid JSON: {e}", error_code="TASK_INVALID_RESPONSE")

    def _post_process(self, data: dict, utterance: str) -> dict:
        """Applies post-processing rules to the validated data."""
        result = data.copy()
        normalized = utterance.lower()

        if result.get("checkType") != 8:
            if "专项" in normalized:
                result["checkType"] = 3
            elif "月度" in normalized:
                result["checkType"] = 4
            elif "季度" in normalized:
                result["checkType"] = 6
            # No else, keep the model's prediction if no keyword matches

        optional_fields = ["checkMoney", "checkScore", "checkLeader"]
        for field in optional_fields:
            if result.get(field) == "":
                result[field] = None
        
        if result.get("checkMoney") is not None:
            try:
                result["checkMoney"] = float(result["checkMoney"])
            except (ValueError, TypeError):
                result["checkMoney"] = None
        
        if result.get("checkScore") is not None:
            try:
                result["checkScore"] = int(result["checkScore"])
            except (ValueError, TypeError):
                result["checkScore"] = None
        
        logger.info("post_processing_complete")
        return result

    def execute(self, utterance: str) -> dict:
        """Executes the full form extraction and validation pipeline."""
        logger.info("starting_form_extraction", form_code="hazard_report")
        try:
            prompt = self._generate_prompt(utterance)
            raw_json_str = self._call_llm(prompt)
            data = self._clean_and_parse_json(raw_json_str)
            
            validated_data = self.pydantic_model.model_validate(data)
            logger.info("validation_successful")
            
            final_data = self._post_process(validated_data.model_dump(), utterance)
            
            logger.info("form_extraction_succeeded", form_code="hazard_report")
            return final_data

        except ValidationError as e:
            error_details = e.errors()[0]
            field, msg = error_details['loc'][0], error_details['msg']
            logger.error("validation_error", field=field, message=msg)
            raise FormExtractionError(f"Validation failed on field '{field}': {msg}", error_code="TASK_VALIDATION_ERROR")
        
        except FormExtractionError as e:
            logger.error("form_extraction_failed", error_code=e.error_code, message=e.message)
            raise
        
        except Exception as e:
            logger.error("form_extraction_unexpected_error", error=str(e))
            raise FormExtractionError(f"An unexpected internal error occurred: {e}", error_code="TASK_INTERNAL_ERROR")