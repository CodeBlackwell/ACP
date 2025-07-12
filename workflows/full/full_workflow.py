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
        error_msg = f"Full workflow error: {str(e)}"
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
    from orchestrator.orchestrator_agent import run_team_member_with_tracking

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
        planning_result = await run_team_member_with_tracking("planner_agent", requirements, "full_planning")
        plan_output = str(planning_result)
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
            design_result = await run_team_member_with_tracking("designer_agent", design_input, "full_design")
            design_output = str(design_result)
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
                        max_retries=3
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
                        
                        execution_result = await run_team_member_with_tracking("executor_agent", execution_input, "full_execution")
                        execution_output = str(execution_result)
                        
                        
                        # Add execution results to the results list
                        results.append(TeamMemberResult(
                            team_member=TeamMember.executor,
                            output=execution_output,
                            name="executor"
                        ))
                    
                except Exception as e:
                    error_msg = f"Incremental coding phase error: {str(e)}"
                    print(f"❌ {error_msg}")
                    # Fall back to standard coder implementation
                    print("⚠️ Falling back to standard implementation...")
                    
                    code_input = f"Plan:\n{plan_output}\n\nDesign:\n{design_output}\n\nRequirements: {requirements}"
                    code_result = await run_team_member_with_tracking("coder_agent", code_input, "full_coding")
                    code_output = str(code_result)
                    
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
                        
                        execution_result = await run_team_member_with_tracking("executor_agent", execution_input, "full_execution_fallback")
                        execution_output = str(execution_result)
                        
                        
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
                    review_result = await run_team_member_with_tracking("reviewer_agent", review_input, "full_final_review")
                    review_result_output = str(review_result)
                    results.append(TeamMemberResult(
                        team_member=TeamMember.reviewer,
                        output=review_result_output,
                        name="reviewer"
                    ))
    
    return results