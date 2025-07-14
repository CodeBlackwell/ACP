#!/usr/bin/env python3
"""
Test logger directly without importing through workflows package.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("Testing logger without workflows package...")

# Import directly, not through workflows package
try:
    print("1. Importing ExecutionLogger...")
    import workflows.execution_logger
    ExecutionLogger = workflows.execution_logger.ExecutionLogger
    print("   - Success")
except Exception as e:
    print(f"   - Failed: {e}")
    sys.exit(1)

print("\n2. Creating logger...")
logger = ExecutionLogger("test_direct")
print(f"   - Created with session_id: {logger.session_id}")

print("\n3. Adding entry...")
logger.log_workflow_start()
print(f"   - Added. Entries: {len(logger.entries)}")

print("\n4. Exporting CSV...")
try:
    csv_path = logger.export_csv()
    print(f"   - Success: {csv_path}")
except Exception as e:
    print(f"   - Failed: {e}")

print("\n5. Exporting JSON...")
try:
    json_path = logger.export_json()
    print(f"   - Success: {json_path}")
except Exception as e:
    print(f"   - Failed: {e}")
    import traceback
    traceback.print_exc()

print("\nDone!")