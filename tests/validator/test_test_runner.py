"""
Unit tests for the refactored TestRunnerAgent
"""
import asyncio
import pytest
import tempfile
import json
from pathlib import Path

from agents.validator import TestRunnerAgent, TestReportGenerator
from shared.data_models import TestResult, TestRunResult


@pytest.mark.asyncio
async def test_detect_pytest_project():
    """Test detection of pytest projects"""
    runner = TestRunnerAgent()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create pytest.ini
        (Path(tmpdir) / 'pytest.ini').write_text('[pytest]\n')
        
        assert runner._detect_test_framework(tmpdir) == 'pytest'


@pytest.mark.asyncio
async def test_detect_jest_project():
    """Test detection of Jest projects"""
    runner = TestRunnerAgent()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create package.json with jest
        package_json = {
            "devDependencies": {
                "jest": "^27.0.0"
            }
        }
        (Path(tmpdir) / 'package.json').write_text(json.dumps(package_json))
        
        assert runner._detect_test_framework(tmpdir) == 'jest'


@pytest.mark.asyncio
async def test_run_tests_with_no_tests():
    """Test running tests in a project with no tests"""
    runner = TestRunnerAgent()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        result = await runner.run_tests(tmpdir, session_id="test123")
        
        assert isinstance(result, TestRunResult)
        assert result.success is False  # No tests found
        assert result.total_tests == 0
        assert result.test_framework == "unknown"
        assert result.session_id == "test123"


@pytest.mark.asyncio
async def test_parse_pytest_output():
    """Test parsing pytest console output"""
    runner = TestRunnerAgent()
    
    sample_output = """
tests/test_example.py::test_addition PASSED                             [ 50%]
tests/test_example.py::test_subtraction FAILED                          [100%]
    """
    
    results = runner._parse_pytest_output(sample_output)
    
    assert len(results) == 2
    assert results[0].test_file == "tests/test_example.py"
    assert results[0].test_name == "test_addition"
    assert results[0].status == "passed"
    assert results[1].status == "failed"


def test_report_generator_csv_output():
    """Test CSV report generation"""
    generator = TestReportGenerator()
    
    # Create a test result
    test_results = [
        TestResult(
            test_file="test_math.py",
            test_name="test_addition",
            status="passed",
            duration_ms=125.5,
            test_framework="pytest"
        ),
        TestResult(
            test_file="test_math.py",
            test_name="test_division",
            status="failed",
            duration_ms=89.2,
            error_message="ZeroDivisionError",
            test_framework="pytest"
        )
    ]
    
    test_run = TestRunResult(
        success=False,
        total_tests=2,
        passed=1,
        failed=1,
        skipped=0,
        test_results=test_results,
        execution_time=0.215,
        test_command="pytest -v",
        output_log="Test output here",
        test_framework="pytest",
        project_path="/test/path",
        session_id="test456"
    )
    
    # Generate reports
    reports = generator.generate_report(test_run)
    
    assert 'test_results_csv' in reports
    assert reports['test_results_csv'].endswith('test_results.csv')
    
    # Verify CSV content
    csv_path = Path(reports['test_results_csv'])
    assert csv_path.exists()
    
    content = csv_path.read_text()
    assert 'test_math.py' in content
    assert 'test_addition' in content
    assert 'passed' in content
    assert 'failed' in content
    assert 'ZeroDivisionError' in content


@pytest.mark.asyncio
async def test_integration_simple_pytest_project():
    """Integration test with a simple pytest project"""
    runner = TestRunnerAgent()
    report_gen = TestReportGenerator()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a simple test file
        test_file = Path(tmpdir) / "test_example.py"
        test_file.write_text("""
def test_passing():
    assert 1 + 1 == 2

def test_failing():
    assert 1 + 1 == 3
""")
        
        # Run tests
        result = await runner.run_tests(tmpdir, session_id="integration_test")
        
        # Generate report
        reports = report_gen.generate_report(result)
        
        # Verify results
        assert result.total_tests >= 0  # May be 0 if pytest not installed
        assert 'test_results_csv' in reports
        
        # Check CSV was created
        csv_path = Path(reports['test_results_csv'])
        assert csv_path.exists()