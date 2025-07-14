"""
Workflow manager for coordinating different workflow implementations.
"""
from typing import List, Dict, Any, Optional, Tuple
import asyncio
import traceback
import importlib
import sys
import time

# Import verification function
def verify_imports():
    """Verify all imports are working correctly and print diagnostics"""
    print("\n===== WORKFLOW IMPORT VERIFICATION =====")
    
    import_checks = {
        "shared.data_models": ["TeamMember", "TeamMemberResult", "CodingTeamInput", "WorkflowStep"],
        "workflows.tdd.tdd_workflow": ["execute_tdd_workflow"],
        "workflows.full.full_workflow": ["execute_full_workflow"],
        "workflows.individual.individual_workflow": ["execute_individual_workflow"],
    }
    
    all_imports_successful = True
    
    for module_name, items in import_checks.items():
        try:
            module = importlib.import_module(module_name)
            print(f"✅ Successfully imported {module_name}")
            
            # Check if each expected item exists in the module
            for item in items:
                if hasattr(module, item):
                    print(f"  ✅ Found {item} in {module_name}")
                else:
                    print(f"  ❌ ERROR: {item} not found in {module_name}")
                    all_imports_successful = False
                    
        except Exception as e:
            print(f"❌ ERROR importing {module_name}: {str(e)}")
            all_imports_successful = False
    
    if all_imports_successful:
        print("✅ All imports verified successfully")
    else:
        print("❌ Some imports failed - workflow may not function correctly")
    
    return all_imports_successful

# Run import verification
# verify_imports()

# Import shared data models
from shared.data_models import (
    TeamMember, 
    TeamMemberResult, 
    WorkflowStep, 
    CodingTeamInput,
    ValidationResult
)

# Import workflow implementations
from workflows.tdd.tdd_workflow import execute_tdd_workflow
from workflows.full.full_workflow import execute_full_workflow
from workflows.individual.individual_workflow import execute_individual_workflow

# Import validation components
from agents.validator import AppRunnerAgent, ValidationReportGenerator


async def execute_workflow(input_data: CodingTeamInput) -> List[TeamMemberResult]:
    """
    Execute a workflow based on the specified type.
    
    Args:
        input_data: The input data containing workflow type and requirements
        
    Returns:
        List of team member results
    """
    print("\n===== WORKFLOW DEBUG: Starting execute_workflow =====")
    print(f"Input data type: {type(input_data)}")
    print(f"Input data attributes: {dir(input_data)}")
    
    # Extract workflow type properly
    workflow_type = None
    
    # First check workflow_type field (new style)
    if hasattr(input_data, 'workflow_type') and input_data.workflow_type:
        workflow_type = input_data.workflow_type.lower()
        print(f"DEBUG: Found workflow_type attribute: {workflow_type}")
    # Then check workflow field (legacy style with enum)
    elif hasattr(input_data, 'workflow') and input_data.workflow:
        # Handle enum value
        if hasattr(input_data.workflow, 'value'):
            workflow_type = input_data.workflow.value.replace('_workflow', '').lower()
            print(f"DEBUG: Found workflow enum with value: {workflow_type}")
        else:
            workflow_type = str(input_data.workflow).replace('_workflow', '').lower()
            print(f"DEBUG: Found workflow string: {workflow_type}")
    
    # Validate workflow type
    if not workflow_type:
        print("ERROR: No workflow type specified in input data")
        raise ValueError("No workflow type specified in input data")
    
    # Normalize workflow type
    workflow_type = workflow_type.strip().lower()
    print(f"DEBUG: Normalized workflow type: {workflow_type}")
    
    
    try:
        # Log workflow start
        print(f" Executing {workflow_type} workflow...")
        
        # Execute the appropriate workflow with monitoring
        if workflow_type == "tdd" or workflow_type == "tdd_workflow":
            print(f"DEBUG: Executing TDD workflow")
            results = await execute_tdd_workflow(input_data)
            print(f"DEBUG: TDD workflow completed, results type: {type(results)}")
        elif workflow_type == "full" or workflow_type == "full_workflow":
            print(f"DEBUG: Executing full workflow")
            results = await execute_full_workflow(input_data)
            print(f"DEBUG: Full workflow completed, results type: {type(results)}")
        elif workflow_type in ["individual", "planning", "design", "test_writing", "implementation", "review"]:
            # For individual workflows, set the step type if not already set
            if workflow_type != "individual" and not input_data.step_type:
                print(f"DEBUG: Setting step_type to {workflow_type} for individual workflow")
                input_data.step_type = workflow_type
            print(f"DEBUG: Executing individual workflow")
            results = await execute_individual_workflow(input_data)
            print(f"DEBUG: Individual workflow completed, results type: {type(results)}")
        else:
            error_msg = f"Unknown workflow type: {workflow_type}. Valid types are: tdd, full, individual, planning, design, test_writing, implementation, review"
            print(f"ERROR: {error_msg}")
            raise ValueError(error_msg)
        
        print(f"DEBUG: Raw results: {results}")
        
        # Ensure results is a list
        if not isinstance(results, list):
            print(f"DEBUG: Converting single result to list")
            results = [results] if results else []
        
        # Ensure all results are TeamMemberResult objects
        validated_results = []
        print(f"DEBUG: Processing {len(results)} results")
        for i, result in enumerate(results):
            print(f"DEBUG: Processing result {i}, type: {type(result)}")
            if isinstance(result, TeamMemberResult):
                print(f"DEBUG: Result {i} is already TeamMemberResult")
                validated_results.append(result)
            elif isinstance(result, tuple) and len(result) == 2:
                # Handle (results, report) tuple from new workflow implementations
                print(f"DEBUG: Result {i} is a tuple")
                if isinstance(result[0], list):
                    print(f"DEBUG: Result {i}[0] is a list with {len(result[0])} items")
                    validated_results.extend(result[0])
                else:
                    print(f"DEBUG: Adding single result {i}[0]")
                    validated_results.append(result[0])
            elif hasattr(result, 'output'):
                # Convert to TeamMemberResult if it has output attribute
                print(f"DEBUG: Converting result {i} with output attribute")
                validated_results.append(TeamMemberResult(
                    team_member=TeamMember.planner,  # Default, should be overridden
                    output=str(result.output),
                    name="unknown"
                ))
            else:
                # Convert raw output to TeamMemberResult
                print(f"DEBUG: Converting raw result {i}")
                validated_results.append(TeamMemberResult(
                    team_member=TeamMember.planner,  # Default, should be overridden
                    output=str(result),
                    name="unknown"
                ))
        
        print(f"DEBUG: Processed {len(validated_results)} validated results")
        
        # Run validation if requested
        if input_data.validate_output:
            print("\n===== POST-WORKFLOW VALIDATION =====")
            validated_results = await _run_validation(validated_results, input_data)
        
        print(f"DEBUG: Returning {len(validated_results)} validated results")
        return validated_results
        
    except asyncio.TimeoutError:
        error_msg = f"Workflow execution timed out for {workflow_type}"
        print(f" ERROR: {error_msg}")
        raise
        
    except Exception as e:
        print(f"ERROR in execute_workflow: {str(e)}")
        print(f"ERROR traceback: {traceback.format_exc()}")
        raise


# Legacy support functions
async def run_workflow(workflow_type: str, requirements: str, 
                      team_members: Optional[List[str]] = None) -> List[TeamMemberResult]:
    """
    Legacy function for backward compatibility.
    
    Args:
        workflow_type: Type of workflow to execute
        requirements: Project requirements
        team_members: Optional list of team members
        
    Returns:
        List of team member results
    """
    print("\n===== WORKFLOW DEBUG: Starting run_workflow =====")
    print(f"workflow_type: {workflow_type}")
    print(f"requirements: {requirements[:100]}...")  # Show first 100 chars
    print(f"team_members: {team_members}")
    
    # Convert string team members to TeamMember enums
    member_enums = []
    if team_members:
        print(f"DEBUG: Converting {len(team_members)} team members to enums")
        for member in team_members:
            try:
                # Try to find matching enum
                found = False
                for tm in TeamMember:
                    if tm.value == member or tm.name.lower() == member.lower():
                        member_enums.append(tm)
                        print(f"DEBUG: Converted '{member}' to enum {tm}")
                        found = True
                        break
                if not found:
                    print(f"DEBUG: Could not convert '{member}' to enum")
            except Exception as e:
                print(f"DEBUG: Error converting '{member}' to enum: {str(e)}")
    
    print(f"DEBUG: Final member_enums: {member_enums}")
    
    # Create input data
    input_data = CodingTeamInput(
        requirements=requirements,
        workflow_type=workflow_type,
        team_members=member_enums if member_enums else None
    )
    print(f"DEBUG: Created CodingTeamInput, attributes: {dir(input_data)}")
    
    # Execute workflow
    print(f"DEBUG: Calling execute_workflow")
    try:
        results = await execute_workflow(input_data)
        print(f"DEBUG: execute_workflow completed, got {len(results)} results")
        return results
    except Exception as e:
        print(f"ERROR in run_workflow: {str(e)}")
        print(f"ERROR traceback: {traceback.format_exc()}")
        raise


# Utility functions for workflow management
def get_available_workflows() -> List[str]:
    """Get list of available workflow types."""
    return ["tdd", "full", "individual", "planning", "design", "test_writing", "implementation", "review", "execution"]


def get_workflow_description(workflow_type: str) -> str:
    """Get description of a workflow type."""
    descriptions = {
        "tdd": "Test-Driven Development workflow: Planning → Design → Test Writing → Implementation → Execution → Review",
        "full": "Full development workflow: Planning → Design → Implementation → Execution → Review",
        "individual": "Execute a single workflow step",
        "planning": "Execute only the planning phase",
        "design": "Execute only the design phase",
        "test_writing": "Execute only the test writing phase",
        "implementation": "Execute only the implementation phase",
        "execution": "Execute only the code execution phase with Docker container",
        "review": "Execute only the review phase"
    }
    return descriptions.get(workflow_type, f"Unknown workflow type: {workflow_type}")


def validate_workflow_input(input_data: CodingTeamInput) -> Tuple[bool, Optional[str]]:
    """
    Validate workflow input data.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not input_data.requirements:
        return False, "Requirements cannot be empty"
    
    # Extract workflow type
    workflow_type = None
    if hasattr(input_data, 'workflow_type') and input_data.workflow_type:
        workflow_type = input_data.workflow_type
    elif hasattr(input_data, 'workflow') and input_data.workflow:
        if hasattr(input_data.workflow, 'value'):
            workflow_type = input_data.workflow.value.replace('_workflow', '')
    
    if not workflow_type:
        return False, "No workflow type specified"
    
    # Validate workflow type
    valid_workflows = get_available_workflows()
    if workflow_type.lower() not in valid_workflows:
        return False, f"Invalid workflow type: {workflow_type}. Valid types are: {', '.join(valid_workflows)}"
    
    # Validate team members if specified
    if hasattr(input_data, 'team_members') and input_data.team_members:
        for member in input_data.team_members:
            if not isinstance(member, TeamMember):
                return False, f"Invalid team member: {member}. Must be a TeamMember enum"
    
    return True, None


async def _run_validation(results: List[TeamMemberResult], 
                         input_data: CodingTeamInput) -> List[TeamMemberResult]:
    """
    Run post-workflow validation on generated code.
    
    Args:
        results: Workflow results containing generated code
        input_data: Original input data with validation config
        
    Returns:
        Updated results with validation report appended
    """
    print("Starting post-workflow validation...")
    
    try:
        # Extract generated files from results
        generated_files = _extract_generated_files(results)
        
        if not generated_files:
            print("No generated files found to validate")
            return results
        
        print(f"Found {len(generated_files)} files to validate")
        
        # Run validation
        runner = AppRunnerAgent(
            timeout=input_data.validation_config.get('timeout', 60) 
            if input_data.validation_config else 60
        )
        
        validation_result = await runner.validate_application(
            generated_files,
            input_data.validation_config
        )
        
        # Generate report
        session_id = f"validation_{int(time.time())}"
        report_gen = ValidationReportGenerator()
        reports = report_gen.generate_report(
            validation_result,
            results,
            session_id
        )
        
        print(f"Validation {'PASSED' if validation_result.success else 'FAILED'}")
        print(f"Reports generated: {', '.join(reports.values())}")
        
        # Add validation result to results
        validation_output = f"""
VALIDATION REPORT
================

Status: {'✅ SUCCESS' if validation_result.success else '❌ FAILED'}
Project Type: {validation_result.project_type}
Duration: {validation_result.duration_seconds:.2f} seconds
Port: {validation_result.port_listening or 'Not detected'}
Health Check: {'✅ Passed' if validation_result.health_check_passed else '❌ Failed'}

Recommendations:
{chr(10).join('- ' + rec for rec in validation_result.recommendations)}

Reports saved to:
{chr(10).join(f'- {k}: {v}' for k, v in reports.items())}
"""
        
        # Create validation result as TeamMemberResult
        validation_member_result = TeamMemberResult(
            team_member=TeamMember.executor,
            output=validation_output,
            name="validator"
        )
        
        results.append(validation_member_result)
        
    except Exception as e:
        print(f"Validation error: {str(e)}")
        error_result = TeamMemberResult(
            team_member=TeamMember.executor,
            output=f"Validation failed with error: {str(e)}",
            name="validator"
        )
        results.append(error_result)
    
    return results


def _extract_generated_files(results: List[TeamMemberResult]) -> Dict[str, str]:
    """Extract generated files from workflow results"""
    files = {}
    
    for result in results:
        # Look for FILENAME: patterns in output
        lines = result.output.split('\n')
        current_file = None
        current_content = []
        in_code_block = False
        code_block_lang = None
        
        for line in lines:
            if line.strip().startswith('FILENAME:'):
                # Save previous file if any
                if current_file and current_content:
                    # Clean up content - remove empty lines at start/end
                    content = '\n'.join(current_content)
                    content = content.strip()
                    files[current_file] = content
                
                # Start new file
                current_file = line.split('FILENAME:', 1)[1].strip()
                current_content = []
                in_code_block = False
                code_block_lang = None
            elif current_file:
                # Check for code block markers
                if line.strip().startswith('```'):
                    if not in_code_block:
                        # Starting a code block
                        in_code_block = True
                        code_block_lang = line.strip()[3:]
                    else:
                        # Ending a code block
                        in_code_block = False
                        code_block_lang = None
                else:
                    # Only accumulate content that's not the code block markers
                    current_content.append(line)
        
        # Save last file if any
        if current_file and current_content:
            content = '\n'.join(current_content)
            content = content.strip()
            files[current_file] = content
    
    return files