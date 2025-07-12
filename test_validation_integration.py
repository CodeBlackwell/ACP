"""
Integration test for the post-workflow validation feature.
"""
import asyncio
from shared.data_models import CodingTeamInput, TeamMember
from workflows.workflow_manager import execute_workflow


async def test_validation_integration():
    """Test the complete validation flow with a simple web server"""
    print("=== Testing Post-Workflow Validation ===\n")
    
    # Create input with validation enabled
    input_data = CodingTeamInput(
        requirements="""
Create a simple Node.js web server that:
1. Uses Express framework
2. Has a root endpoint that returns "Hello World"
3. Has a /health endpoint that returns {"status": "ok"}
4. Listens on port 3000
5. Logs when the server starts

Include a package.json file with necessary dependencies.
""",
        workflow_type="full",
        team_members=[TeamMember.planner, TeamMember.designer, TeamMember.coder],
        validate_output=True,  # Enable validation
        validation_config={
            "timeout": 30,
            "port_check": True,
            "health_endpoint": "/health"
        }
    )
    
    print("Input configuration:")
    print(f"- Workflow: {input_data.workflow_type}")
    print(f"- Validation enabled: {input_data.validate_output}")
    print(f"- Validation config: {input_data.validation_config}")
    print()
    
    # Execute workflow with validation
    try:
        results = await execute_workflow(input_data)
        
        print(f"\nWorkflow completed with {len(results)} results")
        
        # Check if validation was performed
        validation_result = None
        for result in results:
            if result.name == "validator":
                validation_result = result
                break
        
        if validation_result:
            print("\n=== VALIDATION RESULT ===")
            print(validation_result.output)
        else:
            print("\nNo validation result found!")
        
        # Print summary of all results
        print("\n=== ALL RESULTS SUMMARY ===")
        for i, result in enumerate(results):
            print(f"{i+1}. {result.name}: {len(result.output)} characters")
            
    except Exception as e:
        print(f"Error during workflow execution: {str(e)}")
        import traceback
        traceback.print_exc()


async def test_validation_with_python_app():
    """Test validation with a Python Flask application"""
    print("\n\n=== Testing Validation with Python App ===\n")
    
    input_data = CodingTeamInput(
        requirements="""
Create a simple Python Flask web application that:
1. Uses Flask framework
2. Has a root endpoint that returns JSON: {"message": "Hello from Flask"}
3. Has a /status endpoint that returns {"status": "running", "version": "1.0"}
4. Runs on port 5000
5. Includes proper error handling

Include a requirements.txt file with Flask dependency.
""",
        workflow_type="full",
        team_members=[TeamMember.planner, TeamMember.designer, TeamMember.coder],
        validate_output=True,
        validation_config={
            "timeout": 45,
            "health_endpoint": "/status"
        }
    )
    
    try:
        results = await execute_workflow(input_data)
        
        # Find validation result
        for result in results:
            if result.name == "validator":
                print("\n=== PYTHON APP VALIDATION ===")
                print(result.output)
                break
                
    except Exception as e:
        print(f"Error: {str(e)}")


async def test_validation_disabled():
    """Test that validation is skipped when disabled"""
    print("\n\n=== Testing with Validation Disabled ===\n")
    
    input_data = CodingTeamInput(
        requirements="Create a simple calculator function that adds two numbers",
        workflow_type="full",
        team_members=[TeamMember.planner, TeamMember.coder],
        validate_output=False  # Validation disabled
    )
    
    try:
        results = await execute_workflow(input_data)
        
        # Check that no validation was performed
        has_validator = any(r.name == "validator" for r in results)
        
        if has_validator:
            print("ERROR: Validation was performed even though it was disabled!")
        else:
            print("SUCCESS: No validation performed (as expected)")
            print(f"Received {len(results)} results from workflow")
            
    except Exception as e:
        print(f"Error: {str(e)}")


async def main():
    """Run all validation tests"""
    # Test 1: Node.js app with validation
    await test_validation_integration()
    
    # Test 2: Python app with validation
    await test_validation_with_python_app()
    
    # Test 3: Validation disabled
    await test_validation_disabled()
    
    print("\n\n=== All tests completed ===")


if __name__ == "__main__":
    asyncio.run(main())