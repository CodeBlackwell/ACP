"""
Test runner agent for executing and reporting on test suites.
Detects test frameworks, runs tests, and generates structured test reports.
"""
import os
import asyncio
import subprocess
import json
import time
import tempfile
import shutil
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

from shared.data_models import TestResult, TestRunResult


class TestRunnerAgent:
    """Agent responsible for running test suites and collecting results"""
    
    def __init__(self, timeout: int = 300):
        self.timeout = timeout
        self.test_framework_detectors = {
            'pytest': self._detect_pytest,
            'unittest': self._detect_unittest,
            'jest': self._detect_jest,
            'mocha': self._detect_mocha,
            'go': self._detect_go_test,
            'cargo': self._detect_cargo_test,
        }
        
        self.test_commands = {
            'pytest': ['pytest', '-v', '--tb=short', '--junit-xml=test_results.xml'],
            'unittest': ['python', '-m', 'unittest', 'discover', '-v'],
            'jest': ['npm', 'test', '--', '--json', '--outputFile=test_results.json'],
            'mocha': ['npm', 'test'],
            'go': ['go', 'test', '-v', './...', '-json'],
            'cargo': ['cargo', 'test', '--', '--format=json'],
        }
        
    async def run_tests(self, 
                       project_path: str,
                       test_config: Optional[Dict[str, Any]] = None,
                       session_id: Optional[str] = None) -> TestRunResult:
        """
        Run tests in the specified project.
        
        Args:
            project_path: Path to the project containing tests
            test_config: Optional configuration for test execution
            session_id: Optional session identifier
            
        Returns:
            TestRunResult with detailed test information
        """
        start_time = time.time()
        config = test_config or {}
        timeout = config.get('timeout', self.timeout)
        
        try:
            # Detect test framework
            test_framework = self._detect_test_framework(project_path)
            
            if test_framework == "unknown":
                # Try to run tests based on file existence
                test_framework = self._detect_by_test_files(project_path)
            
            # Get test command
            test_command = config.get('test_command')
            if not test_command:
                test_command = self.test_commands.get(test_framework, ['echo', 'No tests found'])
            
            # Execute tests
            output_log, error_log, return_code = await self._execute_tests(
                project_path, test_command, timeout
            )
            
            # Parse test results based on framework
            test_results = await self._parse_test_results(
                project_path, test_framework, output_log, error_log
            )
            
            # Calculate statistics
            total_tests = len(test_results)
            passed = sum(1 for t in test_results if t.status == 'passed')
            failed = sum(1 for t in test_results if t.status == 'failed')
            skipped = sum(1 for t in test_results if t.status == 'skipped')
            
            execution_time = time.time() - start_time
            
            return TestRunResult(
                success=failed == 0 and total_tests > 0,
                total_tests=total_tests,
                passed=passed,
                failed=failed,
                skipped=skipped,
                test_results=test_results,
                execution_time=execution_time,
                test_command=' '.join(test_command) if isinstance(test_command, list) else test_command,
                output_log=output_log,
                test_framework=test_framework,
                project_path=project_path,
                session_id=session_id
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return TestRunResult(
                success=False,
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                test_results=[],
                execution_time=execution_time,
                test_command="",
                output_log=str(e),
                test_framework="unknown",
                project_path=project_path,
                session_id=session_id
            )
    
    def _detect_test_framework(self, project_path: str) -> str:
        """Detect the test framework used in the project"""
        for framework, detector in self.test_framework_detectors.items():
            if detector(project_path):
                return framework
        return "unknown"
    
    def _detect_pytest(self, project_path: str) -> bool:
        """Detect if project uses pytest"""
        indicators = ['pytest.ini', 'pyproject.toml', 'conftest.py', 'setup.cfg']
        if any((Path(project_path) / ind).exists() for ind in indicators):
            return True
        
        # Check for pytest in requirements
        req_files = ['requirements.txt', 'requirements-dev.txt', 'test-requirements.txt']
        for req_file in req_files:
            req_path = Path(project_path) / req_file
            if req_path.exists():
                content = req_path.read_text()
                if 'pytest' in content:
                    return True
        
        return False
    
    def _detect_unittest(self, project_path: str) -> bool:
        """Detect if project uses unittest"""
        # Look for test files that import unittest
        test_patterns = ['test_*.py', '*_test.py']
        for pattern in test_patterns:
            for test_file in Path(project_path).rglob(pattern):
                content = test_file.read_text()
                if 'import unittest' in content or 'from unittest' in content:
                    return True
        return False
    
    def _detect_jest(self, project_path: str) -> bool:
        """Detect if project uses Jest"""
        package_json = Path(project_path) / 'package.json'
        if package_json.exists():
            with open(package_json) as f:
                data = json.load(f)
                # Check devDependencies and dependencies
                deps = {**data.get('dependencies', {}), **data.get('devDependencies', {})}
                if 'jest' in deps:
                    return True
                # Check test script
                scripts = data.get('scripts', {})
                if 'test' in scripts and 'jest' in scripts['test']:
                    return True
        
        # Check for jest config files
        jest_configs = ['jest.config.js', 'jest.config.json', 'jest.config.ts']
        return any((Path(project_path) / config).exists() for config in jest_configs)
    
    def _detect_mocha(self, project_path: str) -> bool:
        """Detect if project uses Mocha"""
        package_json = Path(project_path) / 'package.json'
        if package_json.exists():
            with open(package_json) as f:
                data = json.load(f)
                deps = {**data.get('dependencies', {}), **data.get('devDependencies', {})}
                if 'mocha' in deps:
                    return True
                scripts = data.get('scripts', {})
                if 'test' in scripts and 'mocha' in scripts['test']:
                    return True
        
        # Check for mocha config files
        mocha_configs = ['mocha.opts', '.mocharc.js', '.mocharc.json']
        return any((Path(project_path) / config).exists() for config in mocha_configs)
    
    def _detect_go_test(self, project_path: str) -> bool:
        """Detect if project uses Go testing"""
        # Check for go.mod and test files
        if (Path(project_path) / 'go.mod').exists():
            return any(Path(project_path).rglob('*_test.go'))
        return False
    
    def _detect_cargo_test(self, project_path: str) -> bool:
        """Detect if project uses Cargo test"""
        return (Path(project_path) / 'Cargo.toml').exists()
    
    def _detect_by_test_files(self, project_path: str) -> str:
        """Detect framework by test file patterns"""
        # Python test files
        if list(Path(project_path).rglob('test_*.py')) or list(Path(project_path).rglob('*_test.py')):
            return 'pytest'  # Default to pytest for Python
        
        # JavaScript test files
        if list(Path(project_path).rglob('*.test.js')) or list(Path(project_path).rglob('*.spec.js')):
            return 'jest'  # Default to jest for JS
        
        # Go test files
        if list(Path(project_path).rglob('*_test.go')):
            return 'go'
        
        return 'unknown'
    
    async def _execute_tests(self, 
                           project_path: str, 
                           test_command: List[str],
                           timeout: int) -> Tuple[str, str, int]:
        """Execute the test command and return output"""
        try:
            process = await asyncio.create_subprocess_exec(
                *test_command,
                cwd=project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=timeout
            )
            
            output = stdout.decode() if stdout else ""
            error = stderr.decode() if stderr else ""
            
            return output, error, process.returncode or 0
            
        except asyncio.TimeoutError:
            return "", f"Test execution timed out after {timeout} seconds", -1
        except Exception as e:
            return "", f"Failed to execute tests: {str(e)}", -1
    
    async def _parse_test_results(self,
                                project_path: str,
                                test_framework: str,
                                output_log: str,
                                error_log: str) -> List[TestResult]:
        """Parse test results based on the framework"""
        if test_framework == 'pytest':
            return self._parse_pytest_results(project_path, output_log)
        elif test_framework == 'jest':
            return self._parse_jest_results(project_path)
        elif test_framework == 'unittest':
            return self._parse_unittest_results(output_log)
        elif test_framework == 'mocha':
            return self._parse_mocha_results(output_log)
        elif test_framework == 'go':
            return self._parse_go_test_results(output_log)
        elif test_framework == 'cargo':
            return self._parse_cargo_test_results(output_log)
        else:
            return self._parse_generic_results(output_log)
    
    def _parse_pytest_results(self, project_path: str, output_log: str) -> List[TestResult]:
        """Parse pytest results from JUnit XML if available, otherwise from output"""
        test_results = []
        xml_path = Path(project_path) / 'test_results.xml'
        
        if xml_path.exists():
            try:
                tree = ET.parse(xml_path)
                root = tree.getroot()
                
                for testcase in root.findall('.//testcase'):
                    classname = testcase.get('classname', '')
                    name = testcase.get('name', '')
                    time = float(testcase.get('time', 0)) * 1000  # Convert to ms
                    
                    # Determine status
                    failure = testcase.find('failure')
                    error = testcase.find('error')
                    skipped = testcase.find('skipped')
                    
                    if failure is not None:
                        status = 'failed'
                        error_msg = failure.get('message', '')
                    elif error is not None:
                        status = 'failed'
                        error_msg = error.get('message', '')
                    elif skipped is not None:
                        status = 'skipped'
                        error_msg = skipped.get('message', '')
                    else:
                        status = 'passed'
                        error_msg = None
                    
                    test_results.append(TestResult(
                        test_file=classname.replace('.', '/') + '.py' if classname else 'unknown',
                        test_name=name,
                        status=status,
                        duration_ms=time,
                        error_message=error_msg,
                        test_framework='pytest',
                        test_suite=classname
                    ))
                
                # Clean up XML file
                xml_path.unlink()
                
            except Exception:
                # Fall back to parsing output
                pass
        
        # If no XML results, parse from output
        if not test_results:
            test_results = self._parse_pytest_output(output_log)
        
        return test_results
    
    def _parse_pytest_output(self, output: str) -> List[TestResult]:
        """Parse pytest results from console output"""
        test_results = []
        
        # Regex patterns for pytest output
        test_pattern = re.compile(r'(.*?)::(.*?) (PASSED|FAILED|SKIPPED|XFAIL|XPASS|ERROR)')
        time_pattern = re.compile(r'\[(\d+)%\].*?(\d+\.\d+)s')
        
        for line in output.split('\n'):
            match = test_pattern.search(line)
            if match:
                test_file = match.group(1)
                test_name = match.group(2)
                status_map = {
                    'PASSED': 'passed',
                    'FAILED': 'failed', 
                    'SKIPPED': 'skipped',
                    'XFAIL': 'skipped',
                    'XPASS': 'passed',
                    'ERROR': 'failed'
                }
                status = status_map.get(match.group(3), 'unknown')
                
                # Try to extract time
                time_match = time_pattern.search(line)
                duration = float(time_match.group(2)) * 1000 if time_match else 0
                
                test_results.append(TestResult(
                    test_file=test_file,
                    test_name=test_name,
                    status=status,
                    duration_ms=duration,
                    error_message=None,  # Would need more parsing for error details
                    test_framework='pytest'
                ))
        
        return test_results
    
    def _parse_jest_results(self, project_path: str) -> List[TestResult]:
        """Parse Jest results from JSON output"""
        test_results = []
        json_path = Path(project_path) / 'test_results.json'
        
        if json_path.exists():
            try:
                with open(json_path) as f:
                    data = json.load(f)
                
                for test_result in data.get('testResults', []):
                    test_file = test_result.get('name', 'unknown')
                    
                    for assertion in test_result.get('assertionResults', []):
                        test_results.append(TestResult(
                            test_file=test_file,
                            test_name=assertion.get('title', 'unknown'),
                            status=assertion.get('status', 'unknown'),
                            duration_ms=assertion.get('duration', 0),
                            error_message=assertion.get('failureMessages', [None])[0],
                            test_framework='jest',
                            test_suite=assertion.get('ancestorTitles', [None])[0]
                        ))
                
                # Clean up JSON file
                json_path.unlink()
                
            except Exception:
                pass
        
        return test_results
    
    def _parse_unittest_results(self, output: str) -> List[TestResult]:
        """Parse unittest results from console output"""
        test_results = []
        
        # Patterns for unittest output
        test_pattern = re.compile(r'(test_\w+) \((.*?)\) \.\.\. (ok|FAIL|ERROR|skipped)')
        
        for line in output.split('\n'):
            match = test_pattern.search(line)
            if match:
                test_name = match.group(1)
                test_class = match.group(2)
                status_map = {
                    'ok': 'passed',
                    'FAIL': 'failed',
                    'ERROR': 'failed',
                    'skipped': 'skipped'
                }
                status = status_map.get(match.group(3), 'unknown')
                
                # Extract file from class name
                test_file = test_class.replace('.', '/') + '.py' if '.' in test_class else 'unknown'
                
                test_results.append(TestResult(
                    test_file=test_file,
                    test_name=test_name,
                    status=status,
                    duration_ms=0,  # unittest doesn't provide timing in standard output
                    error_message=None,
                    test_framework='unittest',
                    test_suite=test_class
                ))
        
        return test_results
    
    def _parse_mocha_results(self, output: str) -> List[TestResult]:
        """Parse Mocha results from console output"""
        test_results = []
        
        # Patterns for mocha output
        pass_pattern = re.compile(r'✓ (.+?) \((\d+)ms\)')
        fail_pattern = re.compile(r'\d+\) (.+)')
        
        current_suite = None
        
        for line in output.split('\n'):
            # Track test suites
            if line.strip() and not line.strip().startswith('✓') and not line.strip()[0].isdigit():
                current_suite = line.strip()
            
            # Passing tests
            pass_match = pass_pattern.search(line)
            if pass_match:
                test_results.append(TestResult(
                    test_file='unknown',  # Mocha doesn't show file in output
                    test_name=pass_match.group(1),
                    status='passed',
                    duration_ms=float(pass_match.group(2)),
                    error_message=None,
                    test_framework='mocha',
                    test_suite=current_suite
                ))
            
            # Failing tests
            fail_match = fail_pattern.search(line)
            if fail_match:
                test_results.append(TestResult(
                    test_file='unknown',
                    test_name=fail_match.group(1),
                    status='failed',
                    duration_ms=0,
                    error_message='Test failed',  # Would need more parsing for details
                    test_framework='mocha',
                    test_suite=current_suite
                ))
        
        return test_results
    
    def _parse_go_test_results(self, output: str) -> List[TestResult]:
        """Parse Go test results from JSON output"""
        test_results = []
        
        for line in output.split('\n'):
            if not line.strip():
                continue
            
            try:
                data = json.loads(line)
                if data.get('Action') == 'pass' or data.get('Action') == 'fail':
                    test_name = data.get('Test', 'unknown')
                    if test_name != 'unknown':
                        test_results.append(TestResult(
                            test_file=data.get('Package', 'unknown'),
                            test_name=test_name,
                            status='passed' if data['Action'] == 'pass' else 'failed',
                            duration_ms=data.get('Elapsed', 0) * 1000,
                            error_message=None,
                            test_framework='go',
                            test_suite=data.get('Package')
                        ))
            except json.JSONDecodeError:
                # Not JSON, try regex parsing
                match = re.search(r'(PASS|FAIL):\s+(\S+)\s+\((\d+\.\d+)s\)', line)
                if match:
                    status = 'passed' if match.group(1) == 'PASS' else 'failed'
                    test_results.append(TestResult(
                        test_file='unknown',
                        test_name=match.group(2),
                        status=status,
                        duration_ms=float(match.group(3)) * 1000,
                        error_message=None,
                        test_framework='go'
                    ))
        
        return test_results
    
    def _parse_cargo_test_results(self, output: str) -> List[TestResult]:
        """Parse Cargo test results from output"""
        test_results = []
        
        # Pattern for cargo test output
        test_pattern = re.compile(r'test (\S+) \.\.\. (ok|FAILED|ignored)')
        
        for line in output.split('\n'):
            match = test_pattern.search(line)
            if match:
                test_name = match.group(1)
                status_map = {
                    'ok': 'passed',
                    'FAILED': 'failed',
                    'ignored': 'skipped'
                }
                status = status_map.get(match.group(2), 'unknown')
                
                test_results.append(TestResult(
                    test_file='unknown',  # Cargo doesn't show file in standard output
                    test_name=test_name,
                    status=status,
                    duration_ms=0,  # Would need --nocapture and parsing for timing
                    error_message=None,
                    test_framework='cargo'
                ))
        
        return test_results
    
    def _parse_generic_results(self, output: str) -> List[TestResult]:
        """Generic test result parsing for unknown frameworks"""
        test_results = []
        
        # Look for common patterns
        patterns = [
            re.compile(r'(\w+)\s+(passed|PASSED|success|SUCCESS)'),
            re.compile(r'(\w+)\s+(failed|FAILED|failure|FAILURE)'),
            re.compile(r'Test\s+(\w+):\s+(PASS|FAIL)')
        ]
        
        for pattern in patterns:
            for match in pattern.finditer(output):
                test_name = match.group(1)
                status = 'passed' if 'pass' in match.group(2).lower() else 'failed'
                
                test_results.append(TestResult(
                    test_file='unknown',
                    test_name=test_name,
                    status=status,
                    duration_ms=0,
                    error_message=None,
                    test_framework='unknown'
                ))
        
        return test_results