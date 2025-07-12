"""
Shared data models for the workflow system.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any


class BaseModel:
    """Base model class for all data models"""
    pass


@dataclass
class ExecutionResult:
    """Base class for execution results"""
    success: bool
    feedback: str


class TeamMember(Enum):
    """Available team members"""
    planner = "planner_agent"
    designer = "designer_agent"
    coder = "coder_agent"
    test_writer = "test_writer_agent"
    reviewer = "reviewer_agent"
    executor = "executor_agent"
    
    # Aliases for backward compatibility
    PLANNER = planner
    DESIGNER = designer
    CODER = coder
    TEST_WRITER = test_writer
    REVIEWER = reviewer


class WorkflowStep(Enum):
    """Available workflow steps"""
    # Full workflows
    tdd_workflow = "tdd_workflow"
    full_workflow = "full_workflow"
    
    # Individual steps
    planning = "planning"
    design = "design"
    test_writing = "test_writing"
    implementation = "implementation"
    review = "review"


@dataclass
class CodingTeamInput:
    """Input data for coding team workflows"""
    requirements: str
    workflow: Optional[WorkflowStep] = None  # For backward compatibility
    workflow_type: Optional[str] = None  # New field name
    step_type: Optional[str] = None
    team_members: List[TeamMember] = field(default_factory=list)
    max_retries: int = 3
    timeout_seconds: int = 300
    validate_output: bool = False  # Enable post-workflow validation
    validation_config: Optional[Dict[str, Any]] = None  # Validation configuration
    
    def __post_init__(self):
        # Handle backward compatibility between workflow and workflow_type
        if self.workflow and not self.workflow_type:
            # Extract the value from the enum
            if hasattr(self.workflow, 'value'):
                self.workflow_type = self.workflow.value.replace('_workflow', '')
            else:
                self.workflow_type = str(self.workflow)
        elif self.workflow_type and not self.workflow:
            # Map string back to enum if needed
            workflow_map = {
                'tdd': WorkflowStep.tdd_workflow,
                'full': WorkflowStep.full_workflow,
                'planning': WorkflowStep.planning,
                'design': WorkflowStep.design,
                'test_writing': WorkflowStep.test_writing,
                'implementation': WorkflowStep.implementation,
                'review': WorkflowStep.review
            }
            self.workflow = workflow_map.get(self.workflow_type)


@dataclass
class TeamMemberResult:
    """Result from a team member"""
    team_member: TeamMember
    output: str
    name: Optional[str] = None  # For backward compatibility
    
    def __post_init__(self):
        if not self.name and self.team_member:
            self.name = self.team_member.value.replace('_agent', '')


@dataclass
class CodingTeamResult:
    """Result from the coding team workflow"""
    results: List[TeamMemberResult]
    final_summary: str
    progress_report: str = ""
    success_metrics: Dict[str, Any] = field(default_factory=dict)
    monitoring_report: Optional[str] = None
    execution_tracer: Optional[Any] = None


@dataclass
class CodingTeamOutput:
    """Output wrapper for coding team results"""
    result: CodingTeamResult


@dataclass
class ValidationResult:
    """Result from post-workflow validation"""
    success: bool
    project_type: str  # e.g., "node", "python", "rust"
    installation_log: str
    execution_log: str
    error_log: Optional[str] = None
    port_listening: Optional[int] = None
    health_check_passed: bool = False
    recommendations: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    environment_path: Optional[str] = None