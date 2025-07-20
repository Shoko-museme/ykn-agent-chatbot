"""Form extraction LangGraph workflow.

This module implements the LangGraph workflow for form extraction,
orchestrating the execution of different form extractors.
"""

from typing import Literal

from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph

from app.core.form_extraction.base import FormExtractionState, should_continue
from app.core.form_extraction.registry import get_registry
from app.core.logging import logger


def create_form_extraction_graph() -> CompiledStateGraph:
    """Create and compile the form extraction graph.
    
    Returns:
        CompiledStateGraph: Compiled form extraction workflow
    """
    
    def start_node(state: FormExtractionState) -> FormExtractionState:
        """Initialize the form extraction workflow.
        
        Args:
            state: Current form extraction state
            
        Returns:
            FormExtractionState: Updated state
        """
        logger.info("form_extraction_started", form_code=state["form_code"], utterance_length=len(state["utterance"]))
        
        # Validate required fields
        if not state.get("utterance"):
            state["error_code"] = "TASK_INVALID_REQUEST"
            state["error_message"] = "utterance is required"
            return state
        
        if not state.get("form_code"):
            state["error_code"] = "TASK_INVALID_REQUEST"
            state["error_message"] = "form_code is required"
            return state
        
        # Check if form_code is registered
        registry = get_registry()
        if not registry.is_registered(state["form_code"]):
            state["error_code"] = "TASK_INVALID_REQUEST"
            state["error_message"] = f"Unknown form_code: {state['form_code']}"
            return state
        
        return state
    
    def execute_form_extraction(state: FormExtractionState) -> FormExtractionState:
        """Execute the form extraction using the appropriate executor.
        
        Args:
            state: Current form extraction state
            
        Returns:
            FormExtractionState: Updated state with extraction results
        """
        if state.get("error_code"):
            return state
        
        try:
            # Get the executor for this form code
            registry = get_registry()
            executor = registry.get_executor(state["form_code"])
            
            # Execute the extraction pipeline
            state = executor.prompt_node(state)
            if state.get("error_code"):
                return state
            
            state = executor.llm_node(state)
            if state.get("error_code"):
                return state
            
            state = executor.parse_node(state)
            if state.get("error_code"):
                return state
            
            state = executor.validate_node(state)
            if state.get("error_code"):
                return state
            
            state = executor.post_process_node(state)
            if state.get("error_code"):
                return state
            
            logger.info("form_extraction_completed", form_code=state["form_code"])
            
        except Exception as e:
            logger.error("form_extraction_executor_error", form_code=state["form_code"], error=str(e))
            state["error_code"] = "TASK_INTERNAL_ERROR"
            state["error_message"] = f"Executor error: {str(e)}"
        
        return state
    
    def error_handler(state: FormExtractionState) -> FormExtractionState:
        """Handle errors in the form extraction workflow.
        
        Args:
            state: Current form extraction state with error
            
        Returns:
            FormExtractionState: Updated state with error response
        """
        logger.error(
            "form_extraction_workflow_error",
            form_code=state.get("form_code"),
            error_code=state.get("error_code"),
            error_message=state.get("error_message")
        )
        
        # Prepare error result
        if not state.get("result"):
            state["result"] = {
                "error": True,
                "error_code": state.get("error_code", "TASK_INTERNAL_ERROR"),
                "error_message": state.get("error_message", "Unknown error occurred")
            }
        
        return state
    
    def success_handler(state: FormExtractionState) -> FormExtractionState:
        """Handle successful form extraction.
        
        Args:
            state: Current form extraction state with results
            
        Returns:
            FormExtractionState: Updated state with final response
        """
        logger.info("form_extraction_success", form_code=state["form_code"])
        
        # Ensure we have a proper result structure
        if not state.get("result"):
            state["result"] = state.get("validated_data", {})
        
        return state
    
    def route_after_execution(state: FormExtractionState) -> Literal["error", "success"]:
        """Route to error or success handler based on execution result.
        
        Args:
            state: Current form extraction state
            
        Returns:
            str: Next node to execute ("error" or "success")
        """
        if state.get("error_code"):
            return "error"
        return "success"
    
    # Create the workflow graph
    workflow = StateGraph(FormExtractionState)
    
    # Add nodes
    workflow.add_node("start", start_node)
    workflow.add_node("execute", execute_form_extraction)
    workflow.add_node("error", error_handler)
    workflow.add_node("success", success_handler)
    
    # Add edges
    workflow.set_entry_point("start")
    
    # From start: go to execute if no error, otherwise go to error
    workflow.add_conditional_edges(
        "start",
        should_continue,
        {
            True: "execute",
            False: "error"
        }
    )
    
    # From execute: route based on result
    workflow.add_conditional_edges(
        "execute",
        route_after_execution,
        {
            "error": "error",
            "success": "success"
        }
    )
    
    # Both error and success end the workflow
    workflow.add_edge("error", END)
    workflow.add_edge("success", END)
    
    # Compile and return the graph
    return workflow.compile()


# Global compiled graph instance
_form_extraction_graph = None


def get_form_extraction_graph() -> CompiledStateGraph:
    """Get the compiled form extraction graph.
    
    Returns:
        CompiledStateGraph: The compiled form extraction workflow
    """
    global _form_extraction_graph
    if _form_extraction_graph is None:
        _form_extraction_graph = create_form_extraction_graph()
    return _form_extraction_graph 