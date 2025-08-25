"""Task-related schemas for form extraction API.

This module defines the request and response schemas for the
form extraction task API endpoints.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class FormExtractionRequest(BaseModel):
    """Request schema for form extraction task."""
    
    utterance: str = Field(..., description="自然语言输入文本", min_length=1, max_length=10000)
    form_code: str = Field(..., description="表单类型代码", min_length=1, max_length=50)


class FormExtractionResponse(BaseModel):
    """Response schema for synchronous form extraction."""
    
    status: str = Field("succeeded", description="任务状态")
    result: Dict[str, Any] = Field(..., description="提取结果")