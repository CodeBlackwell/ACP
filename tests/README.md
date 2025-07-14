# Workflow Testing Framework

A comprehensive testing framework for validating AI agent workflows and generated code quality.

## Quick Start

```bash
# Test a specific workflow with minimal complexity
python tests/test_workflows.py --workflow full --complexity minimal --run-tests

# Run all workflows with standard complexity
python tests/test_workflows.py --workflow all --complexity standard --run-tests

# List available tests without running
python tests/test_workflows.py --list
```

## Features

- **Automated Workflow Testing**: Tests various AI agent workflows (TDD, Full, Planning, Design, Implementation)
- **Code Generation Validation**: Verifies that generated code works correctly
- **Test Execution**: Automatically runs tests on generated applications
- **Comprehensive Reporting**: Generates detailed test results in CSV format

## Command Line Options

### Basic Usage

```bash
python tests/test_workflows.py [OPTIONS]
```

### Options

- `--workflow, -w`: Specific workflow type to test
  - `tdd`: Test-Driven Development workflow
  - `full`: Complete development workflow (Planning → Design → Implementation → Review)
  - `planning`: Planning phase only
  - `design`: Design phase only
  - `implementation`: Implementation phase only
  - `all`: Run all workflow types (default)

- `--complexity, -c`: Test complexity level
  - `minimal`: Basic "Hello World" API (default)
  - `standard`: TODO List API with CRUD operations
  - `complex`: Full e-commerce platform
  - `stress`: Microservices architecture
  - `all`: Run all complexity levels

- `--run-tests, -t`: Run pytest on generated code and create test reports

- `--list, -l`: List available tests without running them

## What to Expect

### During Execution

1. **Session Initialization**: Creates a unique session ID and output directory
2. **Workflow Execution**: Runs the selected workflow with progress indicators
3. **Code Generation**: AI agents generate application code based on requirements
4. **Test Execution** (if --run-tests): Runs pytest on generated code
5. **Report Generation**: Creates comprehensive test reports

### Output Structure

```
tests/outputs/
└── session_YYYYMMDD_HHMMSS/
    ├── workflow_complexity/
    │   ├── test_observations.json
    │   └── agent_outputs/
    │       ├── 1_planner.txt
    │       ├── 2_designer.txt
    │       ├── 3_coder.txt
    │       └── 4_reviewer.txt
    └── session_report.json

generated/
└── app_session_exec_YYYYMMDD_HHMMSS_XXXXXX/
    ├── app.py
    ├── test_app.py
    ├── requirements.txt
    ├── README.md
    └── test_results.csv  # Generated when using --run-tests
```

### Test Results CSV

When using `--run-tests`, a `test_results.csv` file is generated directly in the application directory containing:
- Timestamp of test execution
- Session ID
- Test file name
- Individual test names
- Pass/fail status
- Execution time in milliseconds
- Error messages (if any)
- Test framework used
- Test suite information

## Example Workflows

### 1. Quick Test of Full Workflow
```bash
python tests/test_workflows.py --workflow full --complexity minimal --run-tests
```
Generates a simple "Hello World" API and runs tests on it.

### 2. Test All Workflows
```bash
python tests/test_workflows.py --workflow all --complexity minimal --run-tests
```
Tests all workflow types with minimal complexity.

### 3. Stress Test with Complex Application
```bash
python tests/test_workflows.py --workflow full --complexity complex --run-tests
```
Generates a full e-commerce platform with multiple features.

## Understanding the Output

### Console Output
- 🚀 **Workflow Start**: Shows which workflow is being tested
- ✅ **Success Indicators**: Green checkmarks show successful steps
- ❌ **Failures**: Red X marks indicate failures with error details
- 📊 **Metrics**: Displays execution time, success rates, and agent performance
- 🧪 **Test Results**: Shows test framework, total tests, passed/failed counts

### Test Observations
Each test run generates detailed observations including:
- Agent participation and interaction patterns
- Review approval rates
- Retry patterns and reasons
- Performance metrics per agent
- Notable events during execution

## Troubleshooting

### Common Issues

1. **"Command not found" errors**: Ensure you're running the command as a single line without breaks
2. **Module import errors**: Run from the project root directory
3. **Timeout errors**: Increase timeout or use simpler complexity levels
4. **Test failures**: Check generated code in `generated/` directory for issues

### Debug Mode
For detailed debug output, the framework automatically logs workflow execution details including:
- Input data validation
- Workflow step progression
- Agent result processing
- Session ID tracking

## Advanced Usage

### Custom Test Scenarios
Modify `TEST_SCENARIOS` in `test_workflows.py` to add custom test cases:

```python
TEST_SCENARIOS[TestComplexity.CUSTOM] = TestScenario(
    name="Your Custom API",
    complexity=TestComplexity.CUSTOM,
    requirements="Your detailed requirements here",
    timeout=300
)
```

### Batch Testing
Run multiple complexity levels for specific workflows:

```bash
# Test TDD workflow with all complexities
python tests/test_workflows.py --workflow tdd --complexity all --run-tests
```

## Integration with CI/CD

The test framework can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run Workflow Tests
  run: |
    python tests/test_workflows.py --workflow full --complexity minimal --run-tests
    
- name: Check Test Results
  run: |
    if [ -f generated/*/test_results.csv ]; then
      echo "Tests passed successfully"
    else
      echo "Test execution failed"
      exit 1
    fi
```

## Best Practices

1. **Start Simple**: Begin with minimal complexity to verify setup
2. **Use --run-tests**: Always validate generated code works correctly
3. **Review Outputs**: Check agent outputs in `tests/outputs/` for insights
4. **Monitor Performance**: Track execution times across runs
5. **Save Important Results**: Archive successful test sessions for reference

## Contributing

When adding new features or workflows:
1. Update test scenarios in `TEST_SCENARIOS`
2. Add appropriate complexity levels
3. Ensure proper error handling
4. Document new options in this README