# app/api/v1/task.py
from fastapi import APIRouter, HTTPException
from app.schemas.task import FormExtractionRequest, FormExtractionResponse
from app.services.form_extraction_service import run_extraction
from app.core.form_extraction.base import FormExtractionError

router = APIRouter()

@router.post("/form-extraction", response_model=FormExtractionResponse)
async def form_extraction(request: FormExtractionRequest):
    try:
        result_data = run_extraction(
            utterance=request.utterance,
            form_code=request.form_code
        )
        return FormExtractionResponse(status="succeeded", result=result_data)
    except FormExtractionError as e:
        raise HTTPException(status_code=400, detail={"error_code": e.error_code, "message": e.message})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error_code": "TASK_INTERNAL_ERROR", "message": str(e)})