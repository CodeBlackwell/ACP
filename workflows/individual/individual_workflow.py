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
# Import logging components
from workflows.execution_logger import ExecutionLogger
from workflows.message_utils import extract_message_content
import re

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
    from orchestrator.orchestrator_agent import run_team_member
    
    # Generate session ID for this workflow
    workflow_session_id = generate_session_id()
    print(f"🔗 Individual Workflow Session ID: {workflow_session_id}")
    
    # Initialize ExecutionLogger
    logger = ExecutionLogger(workflow_session_id)
    logger.log_metric("workflow_type", "individual")
    logger.log_metric("step_type", step_type)
    logger.log_metric("requirements_length", len(requirements))
    
    results = []
    
    if step_type == "planning":
        print("📋 Planning step...")
        # Log agent request
        request_id = logger.log_agent_request("planner_agent", requirements)
        
        result = await run_team_member("planner_agent", requirements)
        output = extract_message_content(result)
        
        # Log agent response
        logger.log_agent_response("planner_agent", request_id, output)
        
        results.append(TeamMemberResult(
            team_member=TeamMember.planner,
            output=output,
            name="planner"
        ))
        
    elif step_type == "design":
        print("🎨 Design step...")
        # Log agent request
        request_id = logger.log_agent_request("designer_agent", requirements)
        
        result = await run_team_member("designer_agent", requirements)
        output = extract_message_content(result)
        
        # Log agent response
        logger.log_agent_response("designer_agent", request_id, output)
        
        results.append(TeamMemberResult(
            team_member=TeamMember.designer,
            output=output,
            name="designer"
        ))
        
    elif step_type == "test_writing":
        print("🧪 Test writing step...")
        # Log agent request
        request_id = logger.log_agent_request("test_writer_agent", requirements)
        
        result = await run_team_member("test_writer_agent", requirements)
        output = extract_message_content(result)
        
        # Log agent response
        logger.log_agent_response("test_writer_agent", request_id, output)
        
        results.append(TeamMemberResult(
            team_member=TeamMember.test_writer,
            output=output,
            name="test_writer"
        ))
        
    elif step_type == "implementation":
        print("💻 Implementation step...")
        # Add session ID to requirements for coder
        coder_input = f"SESSION_ID: {workflow_session_id}\n\n{requirements}"
        
        # Log agent request
        request_id = logger.log_agent_request("coder_agent", coder_input)
        
        result = await run_team_member("coder_agent", coder_input)
        # Extract message content if it's a Message object
        from workflows.message_utils import extract_message_content
        output = extract_message_content(result)
        
        # Log agent response
        logger.log_agent_response("coder_agent", request_id, output)
        
        # Extract generated app path from coder output
        # Debug: print first 200 chars of output to see format
        print(f"DEBUG: Coder output preview: {output[:200]}...")
        
        path_match = re.search(r'Location: ([^\n]+)', output)
        if path_match:
            generated_app_path = path_match.group(1).strip()
            print(f"DEBUG: Extracted path: {generated_app_path}")
            logger.set_generated_app_path(generated_app_path)
            logger.log_metric("generated_app_path", generated_app_path)
        else:
            print("DEBUG: No path match found in coder output")
        
        results.append(TeamMemberResult(
            team_member=TeamMember.coder,
            output=output,
            name="coder"
        ))
        
    elif step_type == "review":
        print("🔍 Review step...")
        # Log agent request
        request_id = logger.log_agent_request("reviewer_agent", requirements)
        
        result = await run_team_member("reviewer_agent", requirements)
        output = extract_message_content(result)
        
        # Log agent response
        logger.log_agent_response("reviewer_agent", request_id, output)
        
        results.append(TeamMemberResult(
            team_member=TeamMember.reviewer,
            output=output,
            name="reviewer"
        ))
        
    elif step_type == "execution":
        print("🚀 Execution step...")
        # Generate session ID for execution
        session_id = generate_session_id()
        
        # Prepare execution input with session ID
        execution_input = f"""SESSION_ID: {session_id}

Execute the following code:

{requirements}
"""
        
        # Log agent request
        request_id = logger.log_agent_request("executor_agent", execution_input)
        
        result = await run_team_member("executor_agent", execution_input)
        output = extract_message_content(result)
        
        # Log agent response
        logger.log_agent_response("executor_agent", request_id, output)
        
        results.append(TeamMemberResult(
            team_member=TeamMember.executor,
            output=output,
            name="executor"
        ))
        
    else:
        raise ValueError(f"Unknown step type: {step_type}")
    
    # Log workflow completion and export logs
    logger.log_workflow_end(status="completed")
    
    # Export logs
    csv_path = logger.export_csv()
    json_path = logger.export_json()
    
    print(f"\n📄 Individual workflow logs exported:")
    print(f"   CSV: {csv_path}")
    print(f"   JSON: {json_path}")
    
    # Print summary
    print(logger.get_summary())
    
    return results