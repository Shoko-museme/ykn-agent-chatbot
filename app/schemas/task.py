"""Task-related schemas for form extraction API.

This module defines the request and response schemas for the
form extraction task API endpoints.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class FormExtractionRequest(BaseModel):
    """Request schema for form extraction task."""
    
    utterance: str = Field(..., description="自然语言输入文本", min_length=1, max_length=10000)
    form_code: str = Field(..., description="表单类型代码", min_length=1, max_length=50)
    async_mode: bool = Field(default=True, alias="async", description="是否异步执行")
    callback_url: Optional[str] = Field(default=None, description="异步回调URL")
    
    @field_validator("utterance")
    @classmethod
    def validate_utterance(cls, v: str) -> str:
        """Validate utterance field.
        
        Args:
            v: Utterance text
            
        Returns:
            str: Validated utterance
            
        Raises:
            ValueError: If utterance is invalid
        """
        if not v.strip():
            raise ValueError("utterance cannot be empty")
        return v.strip()
    
    @field_validator("form_code")
    @classmethod
    def validate_form_code(cls, v: str) -> str:
        """Validate form_code field.
        
        Args:
            v: Form code
            
        Returns:
            str: Validated form code
            
        Raises:
            ValueError: If form code is invalid
        """
        if not v.strip():
            raise ValueError("form_code cannot be empty")
        return v.strip().lower()
    
    @field_validator("callback_url")
    @classmethod
    def validate_callback_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate callback URL.
        
        Args:
            v: Callback URL
            
        Returns:
            Optional[str]: Validated callback URL
            
        Raises:
            ValueError: If URL format is invalid
        """
        if v is not None:
            v = v.strip()
            if v and not (v.startswith("http://") or v.startswith("https://")):
                raise ValueError("callback_url must be a valid HTTP/HTTPS URL")
        return v


class FormExtractionSyncResponse(BaseModel):
    """Response schema for synchronous form extraction."""
    
    status: str = Field("succeeded", description="任务状态")
    result: Dict[str, Any] = Field(..., description="提取结果")


class FormExtractionAsyncResponse(BaseModel):
    """Response schema for asynchronous form extraction task creation."""
    
    task_id: str = Field(..., description="任务唯一标识")
    status: str = Field("pending", description="任务状态")
    expires_at: str = Field(..., description="任务过期时间 (ISO 8601)")
    
    @field_validator("task_id")
    @classmethod
    def validate_task_id(cls, v: str) -> str:
        """Validate task ID format.
        
        Args:
            v: Task ID
            
        Returns:
            str: Validated task ID
            
        Raises:
            ValueError: If task ID format is invalid
        """
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError("task_id must be a valid UUID")
        return v


class FormExtractionTaskStatus(BaseModel):
    """Response schema for task status queries."""
    
    task_id: str = Field(..., description="任务唯一标识")
    status: str = Field(..., description="任务状态 (pending, succeeded, failed)")
    result: Optional[Dict[str, Any]] = Field(default=None, description="提取结果 (仅成功时)")
    error: Optional[str] = Field(default=None, description="错误信息 (仅失败时)")
    created_at: Optional[str] = Field(default=None, description="任务创建时间")
    completed_at: Optional[str] = Field(default=None, description="任务完成时间")
    expires_at: Optional[str] = Field(default=None, description="任务过期时间")


class FormExtractionError(BaseModel):
    """Error response schema for form extraction."""
    
    error: bool = Field(True, description="是否为错误")
    error_code: str = Field(..., description="错误代码")
    error_message: str = Field(..., description="错误详情")
    details: Optional[Dict[str, Any]] = Field(default=None, description="额外错误信息") 