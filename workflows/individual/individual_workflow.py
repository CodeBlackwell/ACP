"""
Individual workflow step implementation.
"""
from typing import List, Optional
import asyncio
from shared.data_models import (
    TeamMember, WorkflowStep, CodingTeamInput, CodingTeamResult, TeamMemberResult
)
# Import executor components
from agents.executor.executor_agent import generate_session_id

async def execute_individual_workflow(input_data: CodingTeamInput) -> List[TeamMemberResult]:
    """
    Execute an individual workflow step.
    
    Args:
        input_data: The input data containing requirements and workflow configuration
        
    Returns:
        List of team member results
    """
    # Extract workflow step from input data
    workflow_step = input_data.step_type or input_data.workflow_type or "planning"
    
    try:
        # Execute the workflow
        results = await run_individual_workflow(input_data.requirements, workflow_step)
        return results
    except Exception as e:
        # Handle exceptions
        error_msg = f"Individual workflow error: {str(e)}"
        print(f"ERROR: {error_msg}")
        raise


async def run_individual_workflow(requirements: str, step_type: str) -> List[TeamMemberResult]:
    """
    Run a single workflow step.
    
    Args:
        requirements: The project requirements
        step_type: The type of step to run
        
    Returns:
        List of team member results
    """
    # Import run_team_member dynamically to avoid circular imports
    from orchestrator.orchestrator_agent import run_team_member_with_tracking
    
    results = []
    
    if step_type == "planning":
        result = await run_team_member_with_tracking("planner_agent", requirements, "individual_planning")
        results.append(TeamMemberResult(
            team_member=TeamMember.planner,
            output=str(result),
            name="planner"
        ))
        
    elif step_type == "design":
        result = await run_team_member_with_tracking("designer_agent", requirements, "individual_design")
        results.append(TeamMemberResult(
            team_member=TeamMember.designer,
            output=str(result),
            name="designer"
        ))
        
    elif step_type == "test_writing":
        result = await run_team_member_with_tracking("test_writer_agent", requirements, "individual_test_writing")
        results.append(TeamMemberResult(
            team_member=TeamMember.test_writer,
            output=str(result),
            name="test_writer"
        ))
        
    elif step_type == "implementation":
        result = await run_team_member_with_tracking("coder_agent", requirements, "individual_implementation")
        results.append(TeamMemberResult(
            team_member=TeamMember.coder,
            output=str(result),
            name="coder"
        ))
        
    elif step_type == "review":
        result = await run_team_member_with_tracking("reviewer_agent", requirements, "individual_review")
        results.append(TeamMemberResult(
            team_member=TeamMember.reviewer,
            output=str(result),
            name="reviewer"
        ))
        
    elif step_type == "execution":
        # Generate session ID for execution
        session_id = generate_session_id()
        
        # Prepare execution input with session ID
        execution_input = f"""SESSION_ID: {session_id}

Execute the following code:

{requirements}
"""
        
        result = await run_team_member_with_tracking("executor_agent", execution_input, "individual_execution")
        results.append(TeamMemberResult(
            team_member=TeamMember.executor,
            output=str(result),
            name="executor"
        ))
        
    else:
        raise ValueError(f"Unknown step type: {step_type}")
    
    return results