"""
Test report generator for creating detailed test reports with CSV output.
"""
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import os

from shared.data_models import TestResult, TestRunResult, TeamMemberResult


class TestReportGenerator:
    """Generates test reports in various formats with primary focus on CSV"""
    
    def __init__(self, report_dir: str = "./test_reports"):
        self.report_dir = report_dir
        os.makedirs(report_dir, exist_ok=True)
    
    def generate_report(self, 
                       test_run_result: TestRunResult,
                       workflow_results: Optional[List[TeamMemberResult]] = None,
                       session_id: Optional[str] = None) -> Dict[str, str]:
        """
        Generate test reports in multiple formats.
        
        Args:
            test_run_result: The test run result
            workflow_results: Optional workflow results for context
            session_id: Unique session identifier
            
        Returns:
            Dict mapping report type to file path
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_id = session_id or test_run_result.session_id or "unknown"
        base_name = f"test_run_{session_id}_{timestamp}"
        
        reports = {}
        
        # Generate primary CSV report
        csv_path = self._generate_csv_report(test_run_result, base_name)
        reports['csv'] = csv_path
        
        # Generate JSON report for detailed data
        json_path = self._generate_json_report(
            test_run_result, workflow_results, base_name
        )
        reports['json'] = json_path
        
        # Generate Markdown summary report
        md_path = self._generate_markdown_report(
            test_run_result, workflow_results, base_name
        )
        reports['markdown'] = md_path
        
        # Generate test_results.csv specifically (the main output)
        main_csv_path = self._generate_main_csv_results(test_run_result)
        reports['test_results_csv'] = main_csv_path
        
        return reports
    
    def _generate_main_csv_results(self, test_run_result: TestRunResult) -> str:
        """Generate the main test_results.csv file"""
        file_path = os.path.join(self.report_dir, "test_results.csv")
        
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Write headers
            writer.writerow([
                'timestamp',
                'session_id',
                'test_file',
                'test_name',
                'status',
                'duration_ms',
                'error_message',
                'test_framework',
                'test_suite'
            ])
            
            # Write test results
            timestamp = datetime.now().isoformat()
            session_id = test_run_result.session_id or "unknown"
            
            for test in test_run_result.test_results:
                writer.writerow([
                    timestamp,
                    session_id,
                    test.test_file,
                    test.test_name,
                    test.status,
                    f"{test.duration_ms:.2f}",
                    test.error_message or '',
                    test.test_framework,
                    test.test_suite or ''
                ])
        
        return file_path
    
    def _generate_csv_report(self, test_run_result: TestRunResult, base_name: str) -> str:
        """Generate detailed CSV report with test results"""
        file_path = os.path.join(self.report_dir, f"{base_name}_detailed.csv")
        
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Write summary section
            writer.writerow(['Test Run Summary'])
            writer.writerow(['Field', 'Value'])
            writer.writerow(['Session ID', test_run_result.session_id or base_name])
            writer.writerow(['Timestamp', datetime.now().isoformat()])
            writer.writerow(['Success', test_run_result.success])
            writer.writerow(['Total Tests', test_run_result.total_tests])
            writer.writerow(['Passed', test_run_result.passed])
            writer.writerow(['Failed', test_run_result.failed])
            writer.writerow(['Skipped', test_run_result.skipped])
            writer.writerow(['Execution Time (s)', f"{test_run_result.execution_time:.2f}"])
            writer.writerow(['Test Framework', test_run_result.test_framework])
            writer.writerow(['Test Command', test_run_result.test_command])
            writer.writerow(['Project Path', test_run_result.project_path])
            writer.writerow([])  # Empty row
            
            # Write individual test results
            writer.writerow(['Individual Test Results'])
            writer.writerow([
                'Test File',
                'Test Name',
                'Status',
                'Duration (ms)',
                'Error Message',
                'Test Suite'
            ])
            
            for test in test_run_result.test_results:
                writer.writerow([
                    test.test_file,
                    test.test_name,
                    test.status,
                    f"{test.duration_ms:.2f}",
                    test.error_message or '',
                    test.test_suite or ''
                ])
        
        return file_path
    
    def _generate_json_report(self,
                            test_run_result: TestRunResult,
                            workflow_results: Optional[List[TeamMemberResult]],
                            base_name: str) -> str:
        """Generate detailed JSON report"""
        report_data = {
            'session_id': test_run_result.session_id or base_name,
            'timestamp': datetime.now().isoformat(),
            'test_run_result': {
                'success': test_run_result.success,
                'total_tests': test_run_result.total_tests,
                'passed': test_run_result.passed,
                'failed': test_run_result.failed,
                'skipped': test_run_result.skipped,
                'execution_time': test_run_result.execution_time,
                'test_framework': test_run_result.test_framework,
                'test_command': test_run_result.test_command,
                'project_path': test_run_result.project_path,
            },
            'test_results': [
                {
                    'test_file': test.test_file,
                    'test_name': test.test_name,
                    'status': test.status,
                    'duration_ms': test.duration_ms,
                    'error_message': test.error_message,
                    'test_suite': test.test_suite
                }
                for test in test_run_result.test_results
            ],
            'output_log': test_run_result.output_log[:5000] if len(test_run_result.output_log) > 5000 else test_run_result.output_log
        }
        
        if workflow_results:
            report_data['workflow_summary'] = {
                'total_agents': len(workflow_results),
                'agents': [
                    {
                        'name': result.name or result.team_member.value,
                        'output_length': len(result.output)
                    }
                    for result in workflow_results
                ]
            }
        
        file_path = os.path.join(self.report_dir, f"{base_name}.json")
        with open(file_path, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        return file_path
    
    def _generate_markdown_report(self,
                                test_run_result: TestRunResult,
                                workflow_results: Optional[List[TeamMemberResult]],
                                base_name: str) -> str:
        """Generate human-readable Markdown report"""
        content = []
        
        # Header
        content.append(f"# Test Execution Report")
        content.append(f"\n**Session:** {test_run_result.session_id or base_name}")
        content.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        content.append(f"**Status:** {'✅ SUCCESS' if test_run_result.success else '❌ FAILED'}")
        
        # Summary
        content.append("\n## Summary")
        content.append(f"- **Total Tests:** {test_run_result.total_tests}")
        content.append(f"- **Passed:** {test_run_result.passed} ✅")
        content.append(f"- **Failed:** {test_run_result.failed} ❌")
        content.append(f"- **Skipped:** {test_run_result.skipped} ⏭️")
        content.append(f"- **Success Rate:** {(test_run_result.passed / test_run_result.total_tests * 100) if test_run_result.total_tests > 0 else 0:.1f}%")
        content.append(f"- **Execution Time:** {test_run_result.execution_time:.2f} seconds")
        content.append(f"- **Test Framework:** {test_run_result.test_framework}")
        content.append(f"- **Test Command:** `{test_run_result.test_command}`")
        
        # Failed Tests
        failed_tests = [t for t in test_run_result.test_results if t.status == 'failed']
        if failed_tests:
            content.append("\n## Failed Tests")
            for test in failed_tests[:10]:  # Show first 10 failed tests
                content.append(f"\n### ❌ {test.test_name}")
                content.append(f"- **File:** `{test.test_file}`")
                if test.test_suite:
                    content.append(f"- **Suite:** {test.test_suite}")
                if test.error_message:
                    content.append(f"- **Error:** {test.error_message}")
            
            if len(failed_tests) > 10:
                content.append(f"\n... and {len(failed_tests) - 10} more failed tests")
        
        # Test Results Table
        content.append("\n## Test Results")
        content.append("\n| Test File | Test Name | Status | Duration (ms) |")
        content.append("|-----------|-----------|--------|---------------|")
        
        # Show first 20 tests
        for test in test_run_result.test_results[:20]:
            status_icon = {
                'passed': '✅',
                'failed': '❌',
                'skipped': '⏭️'
            }.get(test.status, '❓')
            
            # Truncate long names
            test_name = test.test_name[:40] + '...' if len(test.test_name) > 40 else test.test_name
            test_file = test.test_file.split('/')[-1] if '/' in test.test_file else test.test_file
            
            content.append(f"| {test_file} | {test_name} | {status_icon} {test.status} | {test.duration_ms:.1f} |")
        
        if test_run_result.total_tests > 20:
            content.append(f"\n*... and {test_run_result.total_tests - 20} more tests*")
        
        # Output Log Sample
        if test_run_result.output_log:
            content.append("\n## Test Output (Sample)")
            content.append("```")
            content.append(test_run_result.output_log[:1000])
            if len(test_run_result.output_log) > 1000:
                content.append("... (truncated)")
            content.append("```")
        
        # Workflow Results Summary (if provided)
        if workflow_results:
            content.append("\n## Workflow Context")
            for result in workflow_results:
                agent_name = result.name or result.team_member.value
                content.append(f"- **{agent_name}:** Generated {len(result.output)} characters of output")
        
        file_path = os.path.join(self.report_dir, f"{base_name}.md")
        with open(file_path, 'w') as f:
            f.write('\n'.join(content))
        
        return file_path
    
    def generate_summary_csv(self, report_dir: Optional[str] = None) -> str:
        """Generate a summary CSV of all test runs"""
        if report_dir:
            self.report_dir = report_dir
        
        summary_path = os.path.join(self.report_dir, "test_runs_summary.csv")
        
        # Read all JSON reports to build summary
        json_files = list(Path(self.report_dir).glob("test_run_*.json"))
        
        with open(summary_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Write headers
            writer.writerow([
                'Session ID',
                'Timestamp',
                'Success',
                'Total Tests',
                'Passed',
                'Failed',
                'Skipped',
                'Success Rate (%)',
                'Execution Time (s)',
                'Test Framework',
                'Test Command'
            ])
            
            # Process each JSON report
            for json_file in sorted(json_files):
                try:
                    with open(json_file) as jf:
                        data = json.load(jf)
                    
                    test_data = data['test_run_result']
                    total = test_data['total_tests']
                    passed = test_data['passed']
                    success_rate = (passed / total * 100) if total > 0 else 0
                    
                    writer.writerow([
                        data['session_id'],
                        data['timestamp'],
                        test_data['success'],
                        total,
                        passed,
                        test_data['failed'],
                        test_data['skipped'],
                        f"{success_rate:.1f}",
                        f"{test_data['execution_time']:.2f}",
                        test_data['test_framework'],
                        test_data['test_command']
                    ])
                except Exception:
                    # Skip invalid files
                    continue
        
        return summary_path
    
    def append_to_history_csv(self, test_run_result: TestRunResult) -> str:
        """Append test run to historical CSV file"""
        history_path = os.path.join(self.report_dir, "test_history.csv")
        
        # Check if file exists to determine if we need headers
        file_exists = os.path.exists(history_path)
        
        with open(history_path, 'a', newline='') as f:
            writer = csv.writer(f)
            
            # Write headers if new file
            if not file_exists:
                writer.writerow([
                    'Timestamp',
                    'Session ID',
                    'Project Path',
                    'Test Framework',
                    'Total Tests',
                    'Passed',
                    'Failed',
                    'Skipped',
                    'Success Rate (%)',
                    'Execution Time (s)',
                    'Test Command'
                ])
            
            # Calculate success rate
            success_rate = (test_run_result.passed / test_run_result.total_tests * 100) if test_run_result.total_tests > 0 else 0
            
            # Write data row
            writer.writerow([
                datetime.now().isoformat(),
                test_run_result.session_id or 'unknown',
                test_run_result.project_path,
                test_run_result.test_framework,
                test_run_result.total_tests,
                test_run_result.passed,
                test_run_result.failed,
                test_run_result.skipped,
                f"{success_rate:.1f}",
                f"{test_run_result.execution_time:.2f}",
                test_run_result.test_command
            ])
        
        return history_path