"""Task API endpoints for form extraction.

This module implements the API endpoints for form extraction tasks,
supporting both synchronous and asynchronous execution modes.
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Union

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.security import HTTPBearer

from app.core.form_extraction.graph import get_form_extraction_graph
from app.core.form_extraction.base import FormExtractionState
from app.core.logging import logger
from app.schemas.task import (
    FormExtractionRequest,
    FormExtractionSyncResponse,
    FormExtractionAsyncResponse,
    FormExtractionTaskStatus,
    FormExtractionError,
)

router = APIRouter()
security = HTTPBearer()

# In-memory task storage (should be replaced with proper database in production)
_task_storage: Dict[str, Dict[str, Any]] = {}


def execute_form_extraction_sync(utterance: str, form_code: str) -> Dict[str, Any]:
    """Execute form extraction synchronously.
    
    Args:
        utterance: Natural language input
        form_code: Form type code
        
    Returns:
        Dict[str, Any]: Extraction result
        
    Raises:
        Exception: If extraction fails
    """
    # Create initial state
    state: FormExtractionState = {
        "utterance": utterance,
        "form_code": form_code,
        "prompt": None,
        "raw_json": None,
        "data": None,
        "validated_data": None,
        "result": None,
        "error_code": None,
        "error_message": None,
    }
    
    # Get and execute the form extraction graph
    graph = get_form_extraction_graph()
    final_state = graph.invoke(state)
    
    # Check for errors
    if final_state.get("error_code"):
        raise Exception(f"Form extraction failed: {final_state.get('error_message')}")
    
    return final_state.get("result", {})


async def execute_form_extraction_async(task_id: str, utterance: str, form_code: str, callback_url: str = None):
    """Execute form extraction asynchronously.
    
    Args:
        task_id: Task identifier
        utterance: Natural language input
        form_code: Form type code
        callback_url: Optional callback URL for completion notification
    """
    try:
        # Update task status to running
        if task_id in _task_storage:
            _task_storage[task_id].update({
                "status": "running",
                "updated_at": datetime.utcnow().isoformat()
            })
        
        # Execute form extraction
        result = execute_form_extraction_sync(utterance, form_code)
        
        # Update task with success
        if task_id in _task_storage:
            _task_storage[task_id].update({
                "status": "succeeded",
                "result": result,
                "completed_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            })
        
        logger.info("async_task_completed", task_id=task_id, status="succeeded")
        
        # TODO: Send callback notification if callback_url is provided
        
    except Exception as e:
        logger.error("async_task_failed", task_id=task_id, error=str(e))
        
        # Update task with failure
        if task_id in _task_storage:
            _task_storage[task_id].update({
                "status": "failed",
                "error": str(e),
                "completed_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            })


@router.post("/form-extraction")
async def create_form_extraction_task(
    request: FormExtractionRequest,
    background_tasks: BackgroundTasks,
    token: str = Depends(security)
) -> Union[FormExtractionSyncResponse, FormExtractionAsyncResponse]:
    """Create a form extraction task.
    
    Args:
        request: Form extraction request
        background_tasks: FastAPI background tasks
        token: JWT authentication token
        
    Returns:
        Union[FormExtractionSyncResponse, FormExtractionAsyncResponse]: Task response
        
    Raises:
        HTTPException: If request is invalid or execution fails
    """
    try:
        logger.info(
            "form_extraction_request",
            form_code=request.form_code,
            async_mode=request.async_mode,
            utterance_length=len(request.utterance)
        )
        
        # Synchronous execution
        if not request.async_mode:
            try:
                result = execute_form_extraction_sync(request.utterance, request.form_code)
                return FormExtractionSyncResponse(status="succeeded", result=result)
            except Exception as e:
                logger.error("sync_form_extraction_failed", error=str(e))
                raise HTTPException(status_code=500, detail=f"Form extraction failed: {str(e)}")
        
        # Asynchronous execution
        else:
            task_id = str(uuid.uuid4())
            expires_at = datetime.utcnow() + timedelta(hours=24)  # 24 hour expiry
            
            # Store task metadata
            _task_storage[task_id] = {
                "task_id": task_id,
                "status": "pending",
                "utterance": request.utterance,
                "form_code": request.form_code,
                "callback_url": request.callback_url,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": expires_at.isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "result": None,
                "error": None,
                "completed_at": None,
            }
            
            # Schedule background task
            background_tasks.add_task(
                execute_form_extraction_async,
                task_id,
                request.utterance,
                request.form_code,
                request.callback_url
            )
            
            return FormExtractionAsyncResponse(
                task_id=task_id,
                status="pending",
                expires_at=expires_at.isoformat()
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("form_extraction_api_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")





@router.get("/form-extraction/codes")
async def get_supported_form_codes(token: str = Depends(security)) -> Dict[str, Any]:
    """Get list of supported form codes.
    
    Args:
        token: JWT authentication token
        
    Returns:
        Dict[str, Any]: List of supported form codes
    """
    try:
        from app.core.form_extraction.registry import get_registry
        
        registry = get_registry()
        supported_codes = registry.get_registered_codes()
        
        return {
            "supported_form_codes": supported_codes,
            "count": len(supported_codes)
        }
        
    except Exception as e:
        logger.error("form_codes_api_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/form-extraction/{task_id}")
async def get_form_extraction_status(
    task_id: str,
    token: str = Depends(security)
) -> FormExtractionTaskStatus:
    """Get the status of a form extraction task.
    
    Args:
        task_id: Task identifier
        token: JWT authentication token
        
    Returns:
        FormExtractionTaskStatus: Task status information
        
    Raises:
        HTTPException: If task is not found
    """
    try:
        # Validate task_id format
        try:
            uuid.UUID(task_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid task ID format")
        
        # Get task from storage
        task_data = _task_storage.get(task_id)
        if not task_data:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Check if task is expired
        expires_at = datetime.fromisoformat(task_data["expires_at"])
        if datetime.utcnow() > expires_at:
            task_data["status"] = "expired"
        
        logger.info("task_status_requested", task_id=task_id, status=task_data["status"])
        
        return FormExtractionTaskStatus(
            task_id=task_id,
            status=task_data["status"],
            result=task_data.get("result"),
            error=task_data.get("error"),
            created_at=task_data.get("created_at"),
            completed_at=task_data.get("completed_at"),
            expires_at=task_data.get("expires_at"),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("task_status_api_error", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error") 