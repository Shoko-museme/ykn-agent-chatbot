"""Hazard report form extraction implementation.

This module implements the specific executor and validation model
for the hazard_report form type.
"""

import re
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.form_extraction.base import BaseExecutor
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
        """Validate and normalize check date.
        
        Args:
            v: Date string to validate
            
        Returns:
            str: Normalized date string in YYYYMMDD format or current date if invalid
        """
        if not v:
            return get_current_date()
        
        # Remove any non-digit characters
        date_digits = re.sub(r'\D', '', v)
        
        # If only month and day provided, add current year
        if len(date_digits) == 4:
            current_year = datetime.now().year
            date_digits = f"{current_year}{date_digits}"
        elif len(date_digits) == 6:
            # Assume YYMMDD format, add 20 prefix
            date_digits = f"20{date_digits}"
        elif len(date_digits) != 8:
            logger.warning("invalid_checkDate_format", value=v)
            return get_current_date()
        
        # Validate the date
        try:
            datetime.strptime(date_digits, "%Y%m%d")
        except ValueError:
            logger.warning("invalid_checkDate_value", value=v)
            return get_current_date()
        
        return date_digits
    
    @field_validator("hiddenTroubleLevel")
    @classmethod
    def validate_hidden_trouble_level(cls, v: int) -> int:
        """Validate hidden trouble level.
        
        Args:
            v: Hidden trouble level
            
        Returns:
            int: Validated hidden trouble level
            
        Raises:
            ValueError: If level is not valid
        """
        valid_levels = {5, 6, 7, 8}
        if v not in valid_levels:
            logger.warning("invalid_hiddenTroubleLevel", value=v)
            return 7
        return v
    
    @field_validator("checkType")
    @classmethod
    def validate_check_type(cls, v: int) -> int:
        """Validate check type.
        
        Args:
            v: Check type
            
        Returns:
            int: Validated check type
            
        Raises:
            ValueError: If type is not valid
        """
        valid_types = {1, 3, 4, 5, 6, 8}
        if v not in valid_types:
            logger.warning("invalid_checkType", value=v)
            return 1
        return v
    
    @field_validator("hiddenTroubleType")
    @classmethod
    def validate_hidden_trouble_type(cls, v: Optional[int]) -> Optional[int]:
        """Validate hidden trouble type.
        
        Args:
            v: Hidden trouble type
            
        Returns:
            int: Validated hidden trouble type
            
        Raises:
            ValueError: If type is not valid
        """
        valid_types = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18}
        if v is not None and v not in valid_types:
            logger.warning("invalid_hiddenTroubleType", value=v)
            return None
        return v
    
    @field_validator("illegalType")
    @classmethod
    def validate_illegal_type(cls, v: Optional[int]) -> Optional[int]:
        """Validate illegal type.
        
        Args:
            v: Illegal type
            
        Returns:
            int: Validated illegal type
            
        Raises:
            ValueError: If type is not valid
        """
        valid_types = {1, 2, 3, 4}
        if v is not None and v not in valid_types:
            logger.warning("invalid_illegalType", value=v)
            return None
        return v
    
    @field_validator("checkLeader")
    @classmethod
    def validate_check_leader(cls, v: Optional[int]) -> Optional[int]:
        """Validate check leader.
        
        Args:
            v: Check leader
            
        Returns:
            Optional[int]: Validated check leader
            
        Raises:
            ValueError: If leader is not valid
        """
        if v is not None:
            valid_leaders = {1, 2, 3, 4, 6, 7, 8, 9, 10, 11, 13, 14}
            if v not in valid_leaders:
                logger.warning("invalid_checkLeader", value=v)
                return None
        return v
    
    @model_validator(mode='after')
    def validate_conditional_fields(self) -> 'HazardReportModel':
        """Validate conditional required fields.
        
        Returns:
            HazardReportModel: Validated model instance
            
        Raises:
            ValueError: If conditional validation fails
        """
        # checkLeader is required when checkType == 8
        if self.checkType == 8 and self.checkLeader is None:
            logger.warning("missing_checkLeader", checkType=self.checkType)
        
        return self


class HazardReportExecutor(BaseExecutor):
    """Executor for hazard report form extraction."""
    
    def get_template_name(self) -> str:
        """Get the template file name for hazard report.
        
        Returns:
            str: Template file name
        """
        return "hazard_report.jinja2"
    
    def get_validation_model(self) -> type[BaseModel]:
        """Get the Pydantic model for validation.
        
        Returns:
            type[BaseModel]: HazardReportModel class
        """
        return HazardReportModel
    
    def post_process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Post-process the validated hazard report data.
        
        Args:
            data: Validated data from HazardReportModel
            
        Returns:
            Dict[str, Any]: Post-processed data
        """
        # Create a copy to avoid modifying the original
        result = data.copy()
        
        # Convert empty strings to None for optional fields
        optional_fields = ["checkMoney", "checkScore", "checkLeader"]
        for field in optional_fields:
            if result.get(field) == "":
                result[field] = None
        
        # Ensure numeric fields are properly typed
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
        
        # Log the post-processing
        logger.info(
            "hazard_report_post_processed",
            original_fields=len(data),
            processed_fields=len(result),
            check_date=result.get("checkDate"),
            check_org=result.get("underCheckOrg")
        )
        
        return result 