"""
Simplified stub for workflow monitoring - tracing disabled for debugging.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum


class StepStatus(Enum):
    """Status of a workflow step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    SKIPPED = "skipped"


class ReviewDecision(Enum):
    """Review decision outcomes."""
    APPROVED = "approved"
    REVISION_NEEDED = "revision_needed"
    REJECTED = "rejected"
    AUTO_APPROVED = "auto_approved"


@dataclass
class WorkflowExecutionReport:
    """Stub execution report."""
    workflow_type: str = ""
    execution_id: str = ""
    start_time: datetime = None
    end_time: datetime = None
    duration_seconds: float = 0.0
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = None


class WorkflowExecutionTracer:
    """Stub tracer that does nothing - simplified for debugging."""
    
    def __init__(self, workflow_type: str = "", execution_id: str = ""):
        self.workflow_type = workflow_type
        self.execution_id = execution_id
        self.metadata = {}
    
    def start_step(self, step_name: str, agent_name: str, input_data: Dict[str, Any] = None) -> str:
        """Stub method - returns dummy step ID."""
        return f"step_{step_name}"
    
    def complete_step(self, step_id: str, output_data: Dict[str, Any] = None, success: bool = True):
        """Stub method - does nothing."""
        pass
    
    def add_metadata(self, key: str, value: Any):
        """Stub method - does nothing."""
        self.metadata[key] = value
    
    def complete_execution(self, final_output: Dict[str, Any] = None, error: str = None):
        """Stub method - does nothing."""
        pass
    
    def get_report(self) -> WorkflowExecutionReport:
        """Return a stub report."""
        return WorkflowExecutionReport(
            workflow_type=self.workflow_type,
            execution_id=self.execution_id,
            metadata=self.metadata
        )
    
    def record_review(self, **kwargs):
        """Stub method - does nothing."""
        pass
    
    def record_test_execution(self, **kwargs):
        """Stub method - does nothing."""
        pass
    
    def add_agent_interaction(self, **kwargs):
        """Stub method - does nothing."""
        pass