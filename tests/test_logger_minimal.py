#!/usr/bin/env python3
"""
Minimal test to identify where the logger is hanging.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("Starting minimal logger test...")

print("1. Importing modules...")
from workflows.execution_logger import ExecutionLogger
print("   - ExecutionLogger imported")

from workflows.log_exporter import LogExporter
print("   - LogExporter imported")

print("\n2. Creating logger...")
logger = ExecutionLogger("test_minimal")
print(f"   - Logger created with session_id: {logger.session_id}")

print("\n3. Adding one entry...")
logger.log_workflow_start()
print(f"   - Entry added. Total entries: {len(logger.entries)}")

print("\n4. Testing CSV export directly...")
try:
    csv_path = logger.export_csv()
    print(f"   - CSV exported to: {csv_path}")
except Exception as e:
    print(f"   - CSV export failed: {str(e)}")

print("\n5. Testing JSON export directly...")
try:
    json_path = logger.export_json()
    print(f"   - JSON exported to: {json_path}")
except Exception as e:
    print(f"   - JSON export failed: {str(e)}")

print("\nTest completed!")