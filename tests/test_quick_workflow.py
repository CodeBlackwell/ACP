#!/usr/bin/env python3
"""
Quick test to debug workflow execution logging.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.data_models import CodingTeamInput
from workflows.workflow_manager import execute_workflow
from workflows.logging_config import LoggingConfig, set_logging_config


async def quick_test():
    """Quick test of workflow execution."""
    
    print("\n" + "="*60)
    print("🧪 QUICK WORKFLOW TEST")
    print("="*60 + "\n")
    
    # Simple logging config
    config = LoggingConfig(
        enabled=True,
        log_agent_exchanges=True,
        log_command_executions=True,
        log_errors=True,
        log_metrics=True,
        auto_export_on_completion=False,  # Disable auto export
        export_formats=["csv"],  # Only CSV for now
        include_summary_report=False,  # Skip summary to be faster
        max_input_length=10000,
        max_output_length=10000,
        truncate_commands=False
    )
    set_logging_config(config)
    
    # Minimal input
    input_data = CodingTeamInput(
        requirements="Create a simple hello world function in Python",
        workflow_type="full",  # Use full workflow
        max_retries=1,
        timeout_seconds=120
    )
    
    try:
        print("🚀 Starting workflow...")
        results = await execute_workflow(input_data)
        print(f"\n✅ Workflow completed with {len(results)} results")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(quick_test())