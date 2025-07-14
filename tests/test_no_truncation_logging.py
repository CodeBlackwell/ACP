#!/usr/bin/env python3
"""
Test workflow execution with no truncation in logs.
This ensures all agent exchanges are logged in full.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import required components
from shared.data_models import CodingTeamInput
from workflows.workflow_manager import execute_workflow
from workflows.logging_config_no_truncation import setup_no_truncation_logging
from workflows.log_exporter import LogExporter
from workflows.execution_logger import ExecutionLogger


async def test_full_logging():
    """Test workflow with full logging enabled."""
    
    print("\n" + "="*80)
    print("🧪 TESTING WORKFLOW WITH NO TRUNCATION LOGGING")
    print("="*80 + "\n")
    
    # Set up no-truncation logging
    config = setup_no_truncation_logging()
    
    # Create workflow input
    input_data = CodingTeamInput(
        requirements="Create a basic 'Hello World' REST API endpoint that returns a JSON response. **Only Use Python**",
        workflow_type="full",
        max_retries=3,
        timeout_seconds=300
    )
    
    print("\n🚀 Executing workflow...")
    
    try:
        # Execute workflow
        results = await execute_workflow(input_data)
        
        print(f"\n✅ Workflow completed!")
        print(f"   - Results count: {len(results)}")
        print(f"   - Agents involved: {[r.name or r.team_member.value for r in results]}")
        
        # Find the latest log file
        logs_dir = Path("./logs")
        csv_files = list(logs_dir.glob("execution_report_*.csv"))
        if csv_files:
            latest_csv = max(csv_files, key=lambda p: p.stat().st_mtime)
            
            print(f"\n📄 Latest log file: {latest_csv.name}")
            print(f"   - Size: {latest_csv.stat().st_size:,} bytes")
            
            # Check if data is truncated
            with open(latest_csv, 'r') as f:
                content = f.read()
                truncated_count = content.count('[truncated]')
                print(f"   - Truncation markers found: {truncated_count}")
                
                # Count agent exchanges
                agent_request_count = content.count('agent_request')
                agent_response_count = content.count('agent_response')
                print(f"   - Agent requests: {agent_request_count}")
                print(f"   - Agent responses: {agent_response_count}")
                
                # Check for full output
                if '[truncated]' not in content:
                    print("   ✅ No truncation detected - full logs preserved!")
                else:
                    print("   ⚠️  Some truncation still occurring")
                    
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🚀 Starting no-truncation logging test...")
    asyncio.run(test_full_logging())