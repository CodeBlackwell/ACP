#!/usr/bin/env python3
"""
Test the ExecutionLogger directly to see if export is the issue.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from workflows.execution_logger import ExecutionLogger
from workflows.log_exporter import LogExporter
from workflows.logging_config import LoggingConfig, set_logging_config


def test_logger():
    """Test logger export directly."""
    
    print("\n" + "="*60)
    print("🧪 TESTING LOGGER DIRECTLY")
    print("="*60 + "\n")
    
    # Configure logging
    config = LoggingConfig(
        enabled=True,
        max_input_length=100000,
        max_output_length=100000,
        truncate_commands=False
    )
    set_logging_config(config)
    
    # Create logger
    logger = ExecutionLogger("test_session_123")
    
    # Add some test data
    print("Adding test data...")
    
    # Log workflow start
    logger.log_workflow_start({"test": "data"})
    
    # Log some agent exchanges
    for i in range(3):
        agent_name = f"agent_{i}"
        
        # Log request
        request_id = logger.log_agent_request(
            agent_name=agent_name,
            input_data=f"Test input for {agent_name} - " + "X" * 1000  # 1KB of data
        )
        
        # Log response
        logger.log_agent_response(
            agent_name=agent_name,
            request_id=request_id,
            output_data=f"Test output from {agent_name} - " + "Y" * 2000,  # 2KB of data
            status="success"
        )
        
        print(f"  - Added exchange for {agent_name}")
    
    # Log workflow end
    logger.log_workflow_end(status="completed")
    
    print(f"\nLogger has {len(logger.entries)} entries")
    
    # Test export
    print("\nTesting export...")
    exporter = LogExporter()
    
    try:
        csv_path, json_path = exporter.export_from_logger(logger)
        print(f"\n✅ Export successful!")
        print(f"  - CSV: {csv_path} ({csv_path.stat().st_size} bytes)")
        if json_path.exists():
            print(f"  - JSON: {json_path} ({json_path.stat().st_size} bytes)")
        else:
            print(f"  - JSON: Failed to export")
            
    except Exception as e:
        print(f"\n❌ Export failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_logger()