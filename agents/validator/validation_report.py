"""
Validation report generator for creating detailed reports.
"""
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import os

from shared.data_models import ValidationResult, TeamMemberResult


class ValidationReportGenerator:
    """Generates validation reports in various formats"""
    
    def __init__(self, report_dir: str = "./validation_reports"):
        self.report_dir = report_dir
        os.makedirs(report_dir, exist_ok=True)
    
    def generate_report(self, 
                       validation_result: ValidationResult,
                       workflow_results: List[TeamMemberResult],
                       session_id: str) -> Dict[str, str]:
        """
        Generate validation reports in multiple formats.
        
        Args:
            validation_result: The validation result
            workflow_results: Original workflow results
            session_id: Unique session identifier
            
        Returns:
            Dict mapping report type to file path
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"validation_{session_id}_{timestamp}"
        
        reports = {}
        
        # Generate JSON report
        json_path = self._generate_json_report(
            validation_result, workflow_results, base_name
        )
        reports['json'] = json_path
        
        # Generate Markdown report
        md_path = self._generate_markdown_report(
            validation_result, workflow_results, base_name
        )
        reports['markdown'] = md_path
        
        # Generate CSV summary
        csv_path = self._generate_csv_summary(
            validation_result, base_name
        )
        reports['csv'] = csv_path
        
        return reports
    
    def _generate_json_report(self,
                            validation_result: ValidationResult,
                            workflow_results: List[TeamMemberResult],
                            base_name: str) -> str:
        """Generate detailed JSON report"""
        report_data = {
            'session_id': base_name,
            'timestamp': datetime.now().isoformat(),
            'validation_result': {
                'success': validation_result.success,
                'project_type': validation_result.project_type,
                'duration_seconds': validation_result.duration_seconds,
                'port_listening': validation_result.port_listening,
                'health_check_passed': validation_result.health_check_passed,
                'recommendations': validation_result.recommendations,
            },
            'logs': {
                'installation': validation_result.installation_log,
                'execution': validation_result.execution_log,
                'errors': validation_result.error_log,
            },
            'workflow_summary': {
                'total_agents': len(workflow_results),
                'agents': [
                    {
                        'name': result.name or result.team_member.value,
                        'output_length': len(result.output),
                        'output_preview': result.output[:200] + '...' if len(result.output) > 200 else result.output
                    }
                    for result in workflow_results
                ]
            }
        }
        
        file_path = os.path.join(self.report_dir, f"{base_name}.json")
        with open(file_path, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        return file_path
    
    def _generate_markdown_report(self,
                                validation_result: ValidationResult,
                                workflow_results: List[TeamMemberResult],
                                base_name: str) -> str:
        """Generate human-readable Markdown report"""
        content = []
        
        # Header
        content.append(f"# Validation Report")
        content.append(f"\n**Session:** {base_name}")
        content.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        content.append(f"**Status:** {'✅ SUCCESS' if validation_result.success else '❌ FAILED'}")
        
        # Summary
        content.append("\n## Summary")
        content.append(f"- **Project Type:** {validation_result.project_type}")
        content.append(f"- **Duration:** {validation_result.duration_seconds:.2f} seconds")
        content.append(f"- **Port Listening:** {validation_result.port_listening or 'None detected'}")
        content.append(f"- **Health Check:** {'✅ Passed' if validation_result.health_check_passed else '❌ Failed'}")
        
        # Recommendations
        if validation_result.recommendations:
            content.append("\n## Recommendations")
            for rec in validation_result.recommendations:
                content.append(f"- {rec}")
        
        # Installation Log
        content.append("\n## Installation Log")
        content.append("```")
        content.append(validation_result.installation_log[:1000])
        if len(validation_result.installation_log) > 1000:
            content.append("... (truncated)")
        content.append("```")
        
        # Execution Log
        content.append("\n## Execution Log")
        content.append("```")
        content.append(validation_result.execution_log[:1000])
        if len(validation_result.execution_log) > 1000:
            content.append("... (truncated)")
        content.append("```")
        
        # Error Log
        if validation_result.error_log:
            content.append("\n## Error Log")
            content.append("```")
            content.append(validation_result.error_log)
            content.append("```")
        
        # Workflow Results Summary
        content.append("\n## Workflow Results Summary")
        for result in workflow_results:
            agent_name = result.name or result.team_member.value
            content.append(f"\n### {agent_name}")
            content.append(f"Output length: {len(result.output)} characters")
            
            # Check for generated files
            files = self._extract_files_from_output(result.output)
            if files:
                content.append("\nGenerated files:")
                for file_path in files:
                    content.append(f"- `{file_path}`")
        
        file_path = os.path.join(self.report_dir, f"{base_name}.md")
        with open(file_path, 'w') as f:
            f.write('\n'.join(content))
        
        return file_path
    
    def _generate_csv_summary(self,
                            validation_result: ValidationResult,
                            base_name: str) -> str:
        """Generate CSV summary for easy tracking"""
        file_path = os.path.join(self.report_dir, "validation_summary.csv")
        
        # Check if file exists to determine if we need headers
        file_exists = os.path.exists(file_path)
        
        with open(file_path, 'a', newline='') as f:
            writer = csv.writer(f)
            
            # Write headers if new file
            if not file_exists:
                writer.writerow([
                    'Session ID',
                    'Timestamp',
                    'Success',
                    'Project Type',
                    'Duration (s)',
                    'Port',
                    'Health Check',
                    'Recommendations Count',
                    'Error'
                ])
            
            # Write data row
            writer.writerow([
                base_name,
                datetime.now().isoformat(),
                validation_result.success,
                validation_result.project_type,
                f"{validation_result.duration_seconds:.2f}",
                validation_result.port_listening or '',
                validation_result.health_check_passed,
                len(validation_result.recommendations),
                'Yes' if validation_result.error_log else 'No'
            ])
        
        return file_path
    
    def _extract_files_from_output(self, output: str) -> List[str]:
        """Extract file paths from agent output"""
        files = []
        
        # Look for FILENAME: patterns
        lines = output.split('\n')
        for line in lines:
            if line.strip().startswith('FILENAME:'):
                file_path = line.split('FILENAME:', 1)[1].strip()
                files.append(file_path)
        
        return files
    
    def generate_summary_report(self, report_dir: Optional[str] = None) -> str:
        """Generate a summary report of all validations"""
        if report_dir:
            self.report_dir = report_dir
        
        # Read all JSON reports
        json_files = list(Path(self.report_dir).glob("validation_*.json"))
        
        summary = {
            'total_validations': len(json_files),
            'successful': 0,
            'failed': 0,
            'by_project_type': {},
            'common_recommendations': {},
            'average_duration': 0,
        }
        
        total_duration = 0
        
        for json_file in json_files:
            with open(json_file) as f:
                data = json.load(f)
            
            validation = data['validation_result']
            
            if validation['success']:
                summary['successful'] += 1
            else:
                summary['failed'] += 1
            
            # Track by project type
            ptype = validation['project_type']
            if ptype not in summary['by_project_type']:
                summary['by_project_type'][ptype] = {'success': 0, 'failed': 0}
            
            if validation['success']:
                summary['by_project_type'][ptype]['success'] += 1
            else:
                summary['by_project_type'][ptype]['failed'] += 1
            
            # Track recommendations
            for rec in validation['recommendations']:
                if rec not in summary['common_recommendations']:
                    summary['common_recommendations'][rec] = 0
                summary['common_recommendations'][rec] += 1
            
            total_duration += validation['duration_seconds']
        
        if json_files:
            summary['average_duration'] = total_duration / len(json_files)
        
        # Sort recommendations by frequency
        summary['common_recommendations'] = dict(
            sorted(summary['common_recommendations'].items(), 
                  key=lambda x: x[1], reverse=True)
        )
        
        # Write summary
        summary_path = os.path.join(self.report_dir, "validation_summary.json")
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        return summary_path