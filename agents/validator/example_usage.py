"""
Example usage of the refactored Test Runner Agent

This script demonstrates how to use the TestRunnerAgent to execute tests
and generate CSV reports.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.validator import TestRunnerAgent, TestReportGenerator


async def run_tests_for_project(project_path: str):
    """Run tests for a given project and generate reports"""
    
    print(f"🧪 Running tests for project: {project_path}")
    print("-" * 50)
    
    # Initialize agents
    test_runner = TestRunnerAgent(timeout=300)
    report_generator = TestReportGenerator(report_dir="./test_reports")
    
    # Run tests
    print("⚙️  Detecting test framework...")
    test_result = await test_runner.run_tests(
        project_path=project_path,
        session_id="example_run"
    )
    
    # Display results
    print(f"\n📊 Test Results:")
    print(f"   Framework: {test_result.test_framework}")
    print(f"   Total Tests: {test_result.total_tests}")
    print(f"   ✅ Passed: {test_result.passed}")
    print(f"   ❌ Failed: {test_result.failed}")
    print(f"   ⏭️  Skipped: {test_result.skipped}")
    print(f"   ⏱️  Execution Time: {test_result.execution_time:.2f}s")
    print(f"   Command: {test_result.test_command}")
    
    # Generate reports
    print("\n📝 Generating reports...")
    reports = report_generator.generate_report(test_result)
    
    print("\n✅ Reports generated:")
    for report_type, path in reports.items():
        print(f"   - {report_type}: {path}")
    
    # Show some failed tests if any
    if test_result.failed > 0:
        print("\n❌ Failed Tests:")
        failed_tests = [t for t in test_result.test_results if t.status == 'failed']
        for test in failed_tests[:5]:  # Show first 5
            print(f"   - {test.test_file}::{test.test_name}")
            if test.error_message:
                print(f"     Error: {test.error_message}")
    
    print("\n✨ Test run complete!")
    print(f"📄 Main CSV output: {reports['test_results_csv']}")
    
    return test_result


async def main():
    """Main function"""
    # Example 1: Run tests in current directory
    if len(sys.argv) > 1:
        project_path = sys.argv[1]
    else:
        project_path = "."
    
    await run_tests_for_project(project_path)


if __name__ == "__main__":
    asyncio.run(main())