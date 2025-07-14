# Test Runner Agent

The Test Runner Agent (formerly Validator Agent) is a comprehensive test execution and reporting tool that automatically detects test frameworks, runs tests, and generates structured test reports with a primary focus on CSV output.

## Features

- **Automatic Test Framework Detection**: Supports pytest, unittest, Jest, Mocha, Go test, and Cargo test
- **Test Execution**: Runs tests with appropriate commands for each framework
- **Result Parsing**: Extracts individual test results from various output formats
- **CSV Reporting**: Generates `test_results.csv` with detailed test information
- **Multiple Report Formats**: CSV, JSON, and Markdown reports
- **Environment Management**: Creates isolated test environments
- **Session Tracking**: Maintains test history across runs

## Components

### TestRunnerAgent
The main agent responsible for:
- Detecting test frameworks
- Executing test commands
- Parsing test output
- Collecting test results

### TestReportGenerator
Generates reports in multiple formats:
- **test_results.csv**: Primary output with individual test results
- **Detailed CSV**: Comprehensive test run information
- **JSON**: Machine-readable detailed results
- **Markdown**: Human-readable summary report

### EnvironmentManager
Manages isolated test environments for clean test execution.

## Usage

### Basic Example

```python
import asyncio
from agents.validator import TestRunnerAgent, TestReportGenerator

async def run_tests():
    # Initialize agents
    runner = TestRunnerAgent()
    reporter = TestReportGenerator()
    
    # Run tests
    result = await runner.run_tests(
        project_path="/path/to/project",
        session_id="my_test_run"
    )
    
    # Generate reports
    reports = reporter.generate_report(result)
    
    # Access CSV report
    print(f"Test results saved to: {reports['test_results_csv']}")

asyncio.run(run_tests())
```

### CSV Output Format

The primary `test_results.csv` contains the following columns:
- `timestamp`: When the test was run
- `session_id`: Unique identifier for the test run
- `test_file`: File containing the test
- `test_name`: Name of the test
- `status`: passed/failed/skipped
- `duration_ms`: Test execution time in milliseconds
- `error_message`: Error details for failed tests
- `test_framework`: Detected test framework
- `test_suite`: Test suite/class name (if applicable)

### Supported Test Frameworks

| Framework | Detection | Command |
|-----------|-----------|---------|
| pytest | pytest.ini, conftest.py, requirements.txt | `pytest -v --tb=short --junit-xml=test_results.xml` |
| unittest | import unittest in test files | `python -m unittest discover -v` |
| Jest | package.json with jest dependency | `npm test -- --json --outputFile=test_results.json` |
| Mocha | package.json with mocha dependency | `npm test` |
| Go test | go.mod and *_test.go files | `go test -v ./... -json` |
| Cargo test | Cargo.toml | `cargo test -- --format=json` |

### Configuration Options

```python
test_config = {
    'timeout': 600,  # Test execution timeout in seconds
    'test_command': ['custom', 'test', 'command']  # Override detected command
}

result = await runner.run_tests(project_path, test_config)
```

## Example Output

### test_results.csv
```csv
timestamp,session_id,test_file,test_name,status,duration_ms,error_message,test_framework,test_suite
2025-07-14T10:00:00,abc123,test_auth.py,test_login_success,passed,125.50,,pytest,TestAuthentication
2025-07-14T10:00:01,abc123,test_auth.py,test_login_invalid,failed,89.20,AssertionError: Expected 401,pytest,TestAuthentication
```

### Console Output
```
🧪 Running tests for project: /path/to/project
--------------------------------------------------
⚙️  Detecting test framework...

📊 Test Results:
   Framework: pytest
   Total Tests: 15
   ✅ Passed: 13
   ❌ Failed: 2
   ⏭️  Skipped: 0
   ⏱️  Execution Time: 2.35s
   Command: pytest -v --tb=short --junit-xml=test_results.xml

📝 Generating reports...

✅ Reports generated:
   - csv: ./test_reports/test_run_abc123_20250714_100000_detailed.csv
   - json: ./test_reports/test_run_abc123_20250714_100000.json
   - markdown: ./test_reports/test_run_abc123_20250714_100000.md
   - test_results_csv: ./test_reports/test_results.csv

✨ Test run complete!
📄 Main CSV output: ./test_reports/test_results.csv
```

## Integration with Workflows

The Test Runner Agent can be integrated into existing workflows to automatically run tests after code generation:

```python
from workflows import execute_workflow
from agents.validator import TestRunnerAgent, TestReportGenerator

# Generate code using workflow
workflow_result = await execute_workflow(...)

# Extract generated files
generated_files = extract_files_from_workflow(workflow_result)

# Run tests on generated code
runner = TestRunnerAgent()
test_result = await runner.run_tests(generated_files_path)

# Generate test report
reporter = TestReportGenerator()
reports = reporter.generate_report(test_result, workflow_result.results)
```

## Advanced Features

### Test History Tracking
The agent maintains a `test_history.csv` file that tracks all test runs over time:

```python
reporter.append_to_history_csv(test_result)
```

### Summary Reports
Generate summary reports across multiple test runs:

```python
summary_path = reporter.generate_summary_csv()
```

### Custom Test Parsers
Extend the agent to support additional test frameworks by adding new detection and parsing methods:

```python
class CustomTestRunner(TestRunnerAgent):
    def _detect_custom_framework(self, project_path):
        # Custom detection logic
        pass
    
    def _parse_custom_results(self, output):
        # Custom parsing logic
        pass
```

## Troubleshooting

### No Tests Found
- Ensure test files follow naming conventions (test_*.py, *.test.js, etc.)
- Check that the test framework is installed
- Verify the project path is correct

### Test Command Fails
- Use the `test_command` configuration to override the detected command
- Check that all dependencies are installed
- Ensure the test framework is properly configured

### Parsing Issues
- The agent falls back to generic parsing if specific parsers fail
- Check the JSON report for raw output logs
- Consider implementing a custom parser for unsupported frameworks