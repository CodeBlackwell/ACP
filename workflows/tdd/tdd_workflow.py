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
# Import logging components
from workflows.execution_logger import ExecutionLogger
import re


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
    
    # Generate session ID for this workflow
    workflow_session_id = generate_session_id()
    print(f"🔗 TDD Workflow Session ID: {workflow_session_id}")
    
    # Initialize ExecutionLogger
    logger = ExecutionLogger(workflow_session_id)
    logger.log_metric("workflow_type", "tdd")
    logger.log_metric("requirements_length", len(input_data.requirements))
    
    # Initialize results list
    results = []
    
    try:
        # Planning phase
        print("📋 Planning phase...")
        # Log agent request
        request_id = logger.log_agent_request("planner_agent", input_data.requirements)
        
        planning_result = await run_team_member(
            "planner_agent",
            input_data.requirements)
        planning_output = str(planning_result)
        
        # Log agent response
        logger.log_agent_response("planner_agent", request_id, planning_output)
        
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
        print("🎨 Design phase...")
        design_input = f"Plan:\n{planning_output}\n\nRequirements: {input_data.requirements}"
        
        # Log agent request
        request_id = logger.log_agent_request("designer_agent", design_input)
        
        design_result = await run_team_member(
            "designer_agent",
            design_input)
        design_output = str(design_result)
        
        # Log agent response
        logger.log_agent_response("designer_agent", request_id, design_output)
        
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
        print("🧪 Test writing phase...")
        test_input = f"Design:\n{design_output}\n\nRequirements: {input_data.requirements}"
        
        # Log agent request
        request_id = logger.log_agent_request("test_writer_agent", test_input)
        
        test_result = await run_team_member(
            "test_writer_agent",
            test_input)
        test_output = str(test_result)
        
        # Log agent response
        logger.log_agent_response("test_writer_agent", request_id, test_output)
        
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
        print("💻 Implementation phase...")
        impl_input = f"SESSION_ID: {workflow_session_id}\n\nPlan:\n{planning_output}\n\nDesign:\n{design_output}\n\nTests:\n{test_output}\n\nRequirements: {input_data.requirements}"
        
        # Log agent request
        request_id = logger.log_agent_request("coder_agent", impl_input)
        
        impl_result = await run_team_member(
            "coder_agent",
            impl_input)
        impl_output = str(impl_result)
        
        # Log agent response
        logger.log_agent_response("coder_agent", request_id, impl_output)
        
        # Extract generated app path from coder output
        path_match = re.search(r'📁 Location: ([^\n]+)', impl_output)
        if path_match:
            generated_app_path = path_match.group(1).strip()
            logger.set_generated_app_path(generated_app_path)
            logger.log_metric("generated_app_path", generated_app_path)
        
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
        print("🔍 Final review phase...")
        review_input = f"Requirements: {input_data.requirements}\n\nPlan:\n{planning_output}\n\nDesign:\n{design_output}\n\nTests:\n{test_output}\n\nImplementation:\n{impl_output}"
        
        # Log agent request
        request_id = logger.log_agent_request("reviewer_agent", review_input)
        
        review_result = await run_team_member(
            "reviewer_agent",
            review_input)
        review_output = str(review_result)
        
        # Log agent response
        logger.log_agent_response("reviewer_agent", request_id, review_output)
        
        results.append(TeamMemberResult(
            team_member=TeamMember.reviewer,
            output=review_output,
            name="reviewer"
        ))
        
        # Log workflow completion and export logs
        logger.log_workflow_end(status="completed")
        
        # Export logs
        csv_path = logger.export_csv()
        json_path = logger.export_json()
        
        print(f"\n📄 TDD Execution logs exported:")
        print(f"   CSV: {csv_path}")
        print(f"   JSON: {json_path}")
        
        # Print summary
        print(logger.get_summary())
        
        return results
        
    except Exception as e:
        error_msg = f"Error in TDD workflow: {str(e)}"
        print(error_msg)
        
        # Log error if logger exists
        if 'logger' in locals():
            logger.log_error(error_msg)
            logger.log_workflow_end(status="failed", error=error_msg)
            # Still try to export logs on error
            try:
                logger.export_csv()
                logger.export_json()
            except:
                pass
        
        raise