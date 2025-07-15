#!/usr/bin/env python3
"""
Test script to verify execution report generation when running test_workflows.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from test_workflows import ModernWorkflowTester, TEST_SCENARIOS, TestComplexity


async def test_execution_report():
    """Test that execution reports are generated correctly"""
    print("\n🧪 Testing Execution Report Generation\n")
    
    # Create test runner
    tester = ModernWorkflowTester()
    
    # Run a minimal test
    result = await tester.run_test(
        workflow_type="tdd",
        scenario=TEST_SCENARIOS[TestComplexity.MINIMAL],
        save_artifacts=True,
        run_tests=False  # Skip actual test execution for speed
    )
    
    print(f"\n📊 Test Result:")
    print(f"   • Status: {result.status}")
    print(f"   • Duration: {result.metrics.duration:.2f}s")
    print(f"   • Agents involved: {', '.join(result.observations.agents_involved)}")
    
    # Check if execution reports were generated
    if result.artifacts_path:
        csv_report = result.artifacts_path / f"execution_report_{result.test_id}.csv"
        json_report = result.artifacts_path / f"execution_report_{result.test_id}.json"
        
        print(f"\n📁 Checking for execution reports in: {result.artifacts_path}")
        print(f"   • CSV report exists: {csv_report.exists()}")
        print(f"   • JSON report exists: {json_report.exists()}")
        
        if csv_report.exists():
            # Read and display first few lines of CSV
            with open(csv_report, 'r') as f:
                lines = f.readlines()
                print(f"\n📄 CSV Report Preview (first 5 lines):")
                for line in lines[:5]:
                    print(f"   {line.strip()}")
                print(f"   ... ({len(lines)} total lines)")
    
    # Check notable events for execution report path
    print(f"\n📌 Notable Events:")
    for event in result.observations.notable_events:
        if "Execution report" in event:
            print(f"   • {event}")
    
    print("\n✅ Execution report test complete!\n")


if __name__ == "__main__":
    asyncio.run(test_execution_report())