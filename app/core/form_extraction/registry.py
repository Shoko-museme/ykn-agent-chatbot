# app/core/form_extraction/registry.py

from app.core.form_extraction.hazard_report import HazardReportExecutor
# from app.core.form_extraction.another_form import AnotherFormExecutor # 导入其他实现

# 在应用启动时创建好所有 Executor 实例，实现单例复用
form_executor_registry = {
    "hazard_report": HazardReportExecutor(),
    # "another_form": AnotherFormExecutor(),
    # ... 在此添加所有其他的 Executor 实例
}