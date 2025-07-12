"""
TDD Workflow Implementation

This module implements the Test-Driven Development workflow.
"""
import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Add the project root to the Python path FIRST before any local imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Now import shared data models
from shared.data_models import (
    TeamMember, WorkflowStep, CodingTeamInput, TeamMemberResult
)

# Import configuration
from workflows.workflow_config import MAX_REVIEW_RETRIES

# Import executor components
from agents.executor.executor_agent import generate_session_id


async def execute_tdd_workflow(input_data: CodingTeamInput) -> List[TeamMemberResult]:
    """
    Execute the TDD workflow.
    
    Args:
        input_data: The input data containing requirements and workflow configuration
        
    Returns:
        List of team member results
    """
    # Import utils module for review_output function
    import workflows.workflow_utils as utils_module
    # Correctly reference the async review_output function
    review_output = utils_module.review_output

    # Import run_team_member dynamically to avoid circular imports
    from orchestrator.orchestrator_agent import run_team_member
    
    # Initialize results list
    results = []
    
    try:
        # Planning phase
        planning_result = await run_team_member(
            "planner_agent",
            input_data.requirements)
        planning_output = str(planning_result)
        results.append(TeamMemberResult(
            team_member=TeamMember.planner,
            output=planning_output,
            name="planner"
        ))
        
        # Review planning
        approved, feedback = await review_output(
            planning_output,
            "planning",
            target_agent="planner_agent"
        )
        
        # Design phase
        design_input = f"Plan:\n{planning_output}\n\nRequirements: {input_data.requirements}"
        design_result = await run_team_member(
            "designer_agent",
            design_input)
        design_output = str(design_result)
        results.append(TeamMemberResult(
            team_member=TeamMember.designer,
            output=design_output,
            name="designer"
        ))
        
        # Review design
        approved, feedback = await review_output(
            design_output,
            "design",
            target_agent="designer_agent"
        )
        
        # Test Writing phase
        test_input = f"Design:\n{design_output}\n\nRequirements: {input_data.requirements}"
        test_result = await run_team_member(
            "test_writer_agent",
            test_input)
        test_output = str(test_result)
        results.append(TeamMemberResult(
            team_member=TeamMember.test_writer,
            output=test_output,
            name="test_writer"
        ))
        
        # Review tests
        approved, feedback = await review_output(
            test_output,
            "test_writing",
            target_agent="test_writer_agent"
        )
        
        # Implementation phase
        impl_input = f"Plan:\n{planning_output}\n\nDesign:\n{design_output}\n\nTests:\n{test_output}\n\nRequirements: {input_data.requirements}"
        impl_result = await run_team_member(
            "coder_agent",
            impl_input)
        impl_output = str(impl_result)
        results.append(TeamMemberResult(
            team_member=TeamMember.coder,
            output=impl_output,
            name="coder"
        ))
        
        # Execution phase (if executor is in team members)
        if hasattr(input_data, 'team_members') and input_data.team_members and TeamMember.executor in input_data.team_members:
            session_id = generate_session_id()
            
            # Prepare execution input with session ID
            execution_input = f"""SESSION_ID: {session_id}

Execute the following tests and code:

TESTS:
{test_output}

CODE:
{impl_output}
"""
            
            execution_result = await run_team_member(
                "executor_agent",
                execution_input)
            execution_output = str(execution_result)
            
            # Add execution results to the results list
            results.append(TeamMemberResult(
                team_member=TeamMember.executor,
                output=execution_output,
                name="executor"
            ))
        
        # Final review
        review_input = f"Requirements: {input_data.requirements}\n\nPlan:\n{planning_output}\n\nDesign:\n{design_output}\n\nTests:\n{test_output}\n\nImplementation:\n{impl_output}"
        review_result = await run_team_member(
            "reviewer_agent",
            review_input)
        review_output = str(review_result)
        results.append(TeamMemberResult(
            team_member=TeamMember.reviewer,
            output=review_output,
            name="reviewer"
        ))
        
        return results
        
    except Exception as e:
        print(f"Error in TDD workflow: {str(e)}")
        raise