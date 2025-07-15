"""
Full workflow implementation with comprehensive monitoring.
"""
from typing import List, Optional, Tuple
import asyncio
from shared.data_models import (
    TeamMember, WorkflowStep, CodingTeamInput, CodingTeamResult, TeamMemberResult
)
from workflows.workflow_config import MAX_REVIEW_RETRIES
from workflows.incremental.feature_orchestrator import run_incremental_coding_phase
# Import executor components
from agents.executor.executor_agent import generate_session_id
from workflows.message_utils import extract_message_content
from workflows.execution_logger import ExecutionLogger
import re

async def execute_full_workflow(input_data: CodingTeamInput) -> List[TeamMemberResult]:
    """
    Execute the full workflow.
    
    Args:
        input_data: The input data containing requirements and workflow configuration
        
    Returns:
        List of team member results
    """
    try:
        # Execute the workflow - include executor if it's in input_data.team_members
        team_members = ["planner", "designer", "coder", "reviewer"]
        if hasattr(input_data, 'team_members') and input_data.team_members and TeamMember.executor in input_data.team_members:
            team_members.append("executor")
        results = await run_full_workflow(input_data.requirements, team_members)
        return results
    except Exception as e:
        # Handle exceptions
        error_msg = f"Full workflow error: {extract_message_content(e)}"
        print(f"ERROR: {error_msg}")
        raise


async def run_full_workflow(requirements: str, team_members: List[str]) -> List[TeamMemberResult]:
    """
    Run full workflow: planner -> designer -> coder -> reviewer
    
    Args:
        requirements: The project requirements
        team_members: Team members to involve in the process
        
    Returns:
        List of team member results
    """
    # Import run_team_member dynamically to avoid circular imports
    from orchestrator.orchestrator_agent import run_team_member
    
    # Generate a session ID for this workflow run
    workflow_session_id = generate_session_id()
    print(f"🔗 Workflow Session ID: {workflow_session_id}")
    
    # Initialize ExecutionLogger
    logger = ExecutionLogger(workflow_session_id)
    logger.log_metric("workflow_type", "full")
    logger.log_metric("requirements_length", len(requirements))

    # Import review_output from the renamed workflow_utils.py file
    from workflows import workflow_utils
    # Use the review_output function from the module
    review_output = workflow_utils.review_output
    
    results = []
    max_retries = MAX_REVIEW_RETRIES
    
    print(f"🔄 Starting full workflow for: {requirements[:50]}...")
    
    # Step 1: Planning
    if "planner" in team_members:
        print("📋 Planning phase...")
        # Log agent request
        request_id = logger.log_agent_request("planner_agent", requirements)
        
        planning_result = await run_team_member("planner_agent", requirements)
        plan_output = extract_message_content(planning_result)
        
        # Log agent response
        logger.log_agent_response("planner_agent", request_id, plan_output)
        
        results.append(TeamMemberResult(
            team_member=TeamMember.planner,
            output=plan_output,
            name="planner"
        ))
        
        # Review the plan
        approved, feedback = await review_output(
            plan_output, 
            "planning", 
            target_agent="planner_agent"
        )
        
        # Step 2: Design
        if "designer" in team_members:
            print("🎨 Design phase...")
            design_input = f"Plan:\n{plan_output}\n\nRequirements: {requirements}"
            
            # Log agent request
            request_id = logger.log_agent_request("designer_agent", design_input)
            
            design_result = await run_team_member("designer_agent", design_input)
            design_output = extract_message_content(design_result)
            
            # Log agent response
            logger.log_agent_response("designer_agent", request_id, design_output)
            
            results.append(TeamMemberResult(
                team_member=TeamMember.designer,
                output=design_output,
                name="designer"
            ))
            
            # Review the design
            approved, feedback = await review_output(
                design_output, 
                "design", 
                target_agent="designer_agent"
            )
            
            # Step 3: Implementation
            if "coder" in team_members:
                print("💻 Implementation phase...")
                
                # Use incremental feature orchestrator instead of direct coder_agent call
                try:
                    code_output, execution_metrics = await run_incremental_coding_phase(
                        designer_output=design_output,
                        requirements=requirements,
                        tests=None,  # No tests in full workflow
                        max_retries=3,
                        session_id=workflow_session_id  # Pass session ID
                    )
                    
                    
                    # Log feature execution stats
                    print(f"✅ Completed {execution_metrics['completed_features']}/{execution_metrics['total_features']} features")
                    print(f"📊 Success rate: {execution_metrics['success_rate']:.1f}%")
                    
                    
                    # The incremental orchestrator already returns a TeamMemberResult for the coder
                    # so we don't need to create one here, just add it to our results list
                    coder_result = TeamMemberResult(
                        team_member=TeamMember.coder,
                        output=code_output,
                        name="coder"
                    )
                    results.append(coder_result)
                    
                    # Execute tests and code if executor is in team members
                    if "executor" in team_members:
                        print("🐳 Executing code in Docker container...")
                        session_id = generate_session_id()
                        
                        
                        # Prepare execution input with session ID
                        execution_input = f"""SESSION_ID: {session_id}

Execute the following code:

{code_output}
"""
                        
                        execution_result = await run_team_member("executor_agent", execution_input)
                        execution_output = extract_message_content(execution_result)
                        
                        
                        # Add execution results to the results list
                        results.append(TeamMemberResult(
                            team_member=TeamMember.executor,
                            output=execution_output,
                            name="executor"
                        ))
                    
                except Exception as e:
                    error_msg = f"Incremental coding phase error: {extract_message_content(e)}"
                    print(f"❌ {error_msg}")
                    # Fall back to standard coder implementation
                    print("⚠️ Falling back to standard implementation...")
                    
                    code_input = f"SESSION_ID: {workflow_session_id}\n\nPlan:\n{plan_output}\n\nDesign:\n{design_output}\n\nRequirements: {requirements}"
                    
                    # Log agent request
                    request_id = logger.log_agent_request("coder_agent", code_input)
                    
                    code_result = await run_team_member("coder_agent", code_input)
                    code_output = extract_message_content(code_result)
                    
                    # Log agent response
                    logger.log_agent_response("coder_agent", request_id, code_output)
                    
                    # Extract generated app path from coder output
                    path_match = re.search(r'📁 Location: ([^\n]+)', code_output)
                    if path_match:
                        generated_app_path = path_match.group(1).strip()
                        logger.set_generated_app_path(generated_app_path)
                        logger.log_metric("generated_app_path", generated_app_path)
                    
                    results.append(TeamMemberResult(
                        team_member=TeamMember.coder,
                        output=code_output,
                        name="coder"
                    ))
                    
                    # Execute tests and code in fallback path if executor is in team members
                    if "executor" in team_members:
                        print("🐳 Executing code in Docker container (fallback path)...")
                        session_id = generate_session_id()
                        
                        
                        # Prepare execution input with session ID
                        execution_input = f"""SESSION_ID: {session_id}

Execute the following code:

{code_output}
"""
                        
                        execution_result = await run_team_member("executor_agent", execution_input)
                        execution_output = extract_message_content(execution_result)
                        
                        
                        # Add execution results to the results list
                        results.append(TeamMemberResult(
                            team_member=TeamMember.executor,
                            output=execution_output,
                            name="executor"
                        ))
                
                # Step 4: Final Review
                if "reviewer" in team_members:
                    print("🔍 Final review phase...")
                    review_input = f"Requirements: {requirements}\n\nPlan:\n{plan_output}\n\nDesign:\n{design_output}\n\nImplementation:\n{code_output}"
                    
                    # Log agent request
                    request_id = logger.log_agent_request("reviewer_agent", review_input)
                    
                    review_result = await run_team_member("reviewer_agent", review_input)
                    review_result_output = extract_message_content(review_result)
                    
                    # Log agent response
                    logger.log_agent_response("reviewer_agent", request_id, review_result_output)
                    
                    results.append(TeamMemberResult(
                        team_member=TeamMember.reviewer,
                        output=review_result_output,
                        name="reviewer"
                    ))
    
    # Log workflow completion and export logs
    logger.log_workflow_end(status="completed")
    
    # Export logs
    csv_path = logger.export_csv()
    json_path = logger.export_json()
    
    print(f"\n📄 Execution logs exported:")
    print(f"   CSV: {csv_path}")
    print(f"   JSON: {json_path}")
    
    # Print summary
    print(logger.get_summary())
    
    return results