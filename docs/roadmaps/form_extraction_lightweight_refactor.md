# 表单提取模块轻量化改造指南 (V2 - 优化版)

## 1. 改造目标

- **移除 `LangGraph`**: 彻底剥离 `LangGraph` 依赖，消除其带来的状态管理和调度开销。
- **简化调用链路**: 将原有的图节点式执行改造为标准的函数式顺序调用。
- **提升性能与效率**: **采用单例模式复用 `Executor` 实例**，避免在每次请求时重复创建对象，降低延迟。
- **保留核心优势**: 维持现有的可插拔架构和基于 `Pydantic` 的强校验能力。

## 2. 新架构设计

我们将引入一个中心的 **Service** 层函数，它将取代 `LangGraph` 成为新的流程编排器。

**新执行流程如下:**

1.  **应用启动时**: 扫描并**实例化所有 `Executor`**，存入一个单例注册表 (`registry`) 中。
2.  **API 层 (`task.py`)**: 接收请求，调用 `FormExtractionService`。
3.  **Service 层 (`form_extraction_service.py`)**:
    a.  根据 `form_code` 从 `registry` 中**直接获取预先创建好的 `Executor` 实例**。
    b.  调用 `Executor` 实例的 `execute` 方法。
    c.  向 API 层返回结果或异常。
4.  **Executor 层 (`base.py`, `hazard_report.py`, etc.)**:
    a.  `Executor` 实例是**无状态的、可重用的**。
    b.  `execute` 方法内部按顺序执行完整的提取与校验逻辑。

## 3. 详细改造步骤

### 步骤 1: 整合 `Executor` 逻辑

此步骤保持不变。我们将 `Executor` 中分散的节点逻辑合并到一个 `execute` 方法中，并定义好业务异常。

**文件**: `app/core/form_extraction/base.py` & `app/core/form_extraction/hazard_report.py`

```python
# app/core/form_extraction/base.py
from abc import ABC, abstractmethod

class BaseExecutor(ABC):
    @abstractmethod
    def execute(self, utterance: str) -> dict:
        raise NotImplementedError

# app/core/form_extraction/hazard_report.py
import json
from pydantic import ValidationError

# 定义自定义异常
class FormExtractionError(Exception):
    def __init__(self, message, error_code=None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

class HazardReportExecutor(BaseExecutor):
    # ... (属性定义) ...
    def execute(self, utterance: str) -> dict:
        try:
            prompt = self._generate_prompt(utterance)
            raw_json_str = self._call_llm(prompt)
            data = json.loads(raw_json_str)
            validated_data = self.pydantic_model.model_validate(data)
            return validated_data.model_dump()
        except json.JSONDecodeError:
            raise FormExtractionError("LLM output is not valid JSON", error_code="TASK_INVALID_RESPONSE")
        except ValidationError as e:
            error_details = e.errors()[0]
            field, msg = error_details['loc'][0], error_details['msg']
            raise FormExtractionError(f"Validation failed on field '{field}': {msg}", error_code="TASK_VALIDATION_ERROR")
        except Exception as e:
            raise FormExtractionError(f"An unexpected internal error occurred: {e}", error_code="TASK_INTERNAL_ERROR")
    
    # ... (私有辅助方法) ...
```

### 步骤 2: 改造注册表为单例模式 (核心优化)

这是实现性能提升的关键。我们将注册表从存储“类”改为存储“实例”。

**文件**: `app/core/form_extraction/registry.py`

```python
# app/core/form_extraction/registry.py

from app.core.form_extraction.hazard_report import HazardReportExecutor
# from app.core.form_extraction.another_form import AnotherFormExecutor # 导入其他实现

# 在应用启动时创建好所有 Executor 实例，实现单例复用
form_executor_registry = {
    "hazard_report": HazardReportExecutor(),
    # "another_form": AnotherFormExecutor(),
    # ... 在此添加所有其他的 Executor 实例
}
```

### 步骤 3: 创建新的 Service 层

新的 Service 层直接使用注册表中的单例。

**新文件**: `app/services/form_extraction_service.py`

```python
# app/services/form_extraction_service.py
from app.core.form_extraction.registry import form_executor_registry
from app.core.form_extraction.hazard_report import FormExtractionError

def run_extraction(utterance: str, form_code: str) -> dict:
    """
    Orchestrates the form extraction process using pre-instantiated singleton executors.
    """
    executor_instance = form_executor_registry.get(form_code)
    if not executor_instance:
        raise ValueError(f"Form executor for code '{form_code}' not found in registry.")

    # 直接调用单例的 execute 方法
    return executor_instance.execute(utterance)
```

### 步骤 4: 更新 API 端点

API 层的代码与初版方案类似，但现在它调用的是优化后的 Service，性能更高。

**文件**: `app/api/v1/task.py`

```python
# app/api/v1/task.py
from fastapi import APIRouter, HTTPException
from app.schemas.task import FormExtractionRequest, FormExtractionResponse
from app.services.form_extraction_service import run_extraction
from app.core.form_extraction.hazard_report import FormExtractionError

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
```

### 步骤 5: 清理工作

1.  **删除 `graph.py`**: 安全删除 `app/core/form_extraction/graph.py`。
2.  **移除 `FormExtractionState`**: 从 `app/core/form_extraction/base.py` 中删除 `FormExtractionState` 的 `TypedDict` 定义。
3.  **更新依赖**: 检查 `pyproject.toml`，如果 `langgraph` 仅被此模块使用，可以考虑移除。

## 4. 总结

完成以上改造后，你的表单提取模块将变得：

- **更快**: 通过复用 `Executor` 单例，消除了重复的对象创建开销，显著降低了请求延迟。
- **更简单**: 代码逻辑回归为清晰的线性调用，易于理解、调试和维护。
- **更健壮**: 采用标准的 `try...except` 错误处理，同时保证了请求处理的无状态性。

此方案在提升性能和简化代码的同时，完整保留了原设计的核心价值，是生产环境下的推荐实践。