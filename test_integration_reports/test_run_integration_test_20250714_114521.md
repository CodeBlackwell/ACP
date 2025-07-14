# Test Execution Report

**Session:** integration_test
**Date:** 2025-07-14 11:45:21
**Status:** ❌ FAILED

## Summary
- **Total Tests:** 0
- **Passed:** 0 ✅
- **Failed:** 0 ❌
- **Skipped:** 0 ⏭️
- **Success Rate:** 0.0%
- **Execution Time:** 2.00 seconds
- **Test Framework:** unittest
- **Test Command:** `python -m unittest discover -v`

## Test Results

| Test File | Test Name | Status | Duration (ms) |
|-----------|-----------|--------|---------------|

## Test Output (Sample)
```
Testing imports...
✅ dotenv imported successfully
✅ Environment variables loaded
⚠️  Warning: acp_sdk already imported. Compatibility patches may not work correctly.
   Please import utils.acp_sdk_compat before importing acp_sdk
❌ Import error: cannot import name 'AppRunnerAgent' from 'agents.validator' (/Users/lechristopherblackwell/Desktop/Ground_up/rebuild/agents/validator/__init__.py)
Testing imports...
✅ dotenv imported successfully
✅ Environment variables loaded
✅ designer_agent imported successfully
✅ ACP types imported successfully
Testing imports...
✅ dotenv imported successfully
✅ Environment variables loaded
✅ planner_agent imported successfully
✅ ACP types imported successfully
Testing imports...
✅ dotenv imported successfully
✅ Environment variables loaded
✅ reviewer_agent imported successfully
✅ ACP types imported successfully
Testing imports...
✅ dotenv imported successfully
✅ Environment variables loaded
✅ test_writer_agent imported successfully
✅ ACP types imported suc
... (truncated)
```