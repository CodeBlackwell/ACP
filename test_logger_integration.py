#!/usr/bin/env python3
"""
Test the ExecutionLogger integration with workflows.
This script tests that logs are properly saved to the generated app directory.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from shared.data_models import CodingTeamInput
from workflows import execute_workflow

async def test_logger_integration():
    """Test the ExecutionLogger integration with a simple workflow"""
    print("Testing ExecutionLogger integration with workflow...")
    print("=" * 60)
    
    # Create a simple test input
    test_input = CodingTeamInput(
        requirements="Create a simple Hello World Python script that prints 'Hello from the test!'",
        workflow_type="implementation"  # Use individual workflow for faster test
    )
    
    try:
        # Execute the workflow
        print("\n🚀 Executing workflow...")
        results = await execute_workflow(test_input)
        
        print(f"\n✅ Workflow completed with {len(results)} results")
        
        # Check if coder output contains the generated app path
        for result in results:
            if result.name == "coder" and "Location:" in result.output:
                # Extract the generated app path
                import re
                path_match = re.search(r'Location: (.+?)(?:\n|$)', result.output)
                if path_match:
                    app_path = path_match.group(1).strip()
                    print(f"\n📁 Generated app path: {app_path}")
                    
                    # Check if logs were saved there
                    app_dir = Path(app_path)
                    if app_dir.exists():
                        csv_files = list(app_dir.glob("execution_report_*.csv"))
                        json_files = list(app_dir.glob("execution_report_*.json"))
                        
                        print(f"\n📄 Log files in generated app directory:")
                        print(f"   CSV files: {len(csv_files)}")
                        for csv in csv_files:
                            print(f"     - {csv.name}")
                        print(f"   JSON files: {len(json_files)}")
                        for json_file in json_files:
                            print(f"     - {json_file.name}")
                        
                        # Also check the backup in logs directory
                        logs_dir = Path("./logs")
                        if logs_dir.exists():
                            backup_csvs = list(logs_dir.glob("execution_report_*.csv"))
                            backup_jsons = list(logs_dir.glob("execution_report_*.json"))
                            print(f"\n📄 Backup log files in ./logs:")
                            print(f"   CSV files: {len(backup_csvs)}")
                            print(f"   JSON files: {len(backup_jsons)}")
                        
                        # Read a sample from the CSV to verify content
                        if csv_files:
                            print(f"\n📊 Sample from {csv_files[0].name}:")
                            with open(csv_files[0], 'r') as f:
                                lines = f.readlines()[:5]  # First 5 lines
                                for line in lines:
                                    print(f"   {line.strip()}")
                    else:
                        print(f"⚠️  Generated app directory not found: {app_path}")
                    break
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🧪 ExecutionLogger Integration Test")
    print("=" * 60)
    asyncio.run(test_logger_integration())