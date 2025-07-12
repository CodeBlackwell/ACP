"""
Tests for the validation report generator.
"""
import pytest
import json
import os
import tempfile
from pathlib import Path
from datetime import datetime

from agents.validator.validation_report import ValidationReportGenerator
from shared.data_models import ValidationResult, TeamMemberResult, TeamMember


class TestValidationReportGenerator:
    """Test cases for ValidationReportGenerator"""
    
    @pytest.fixture
    def report_gen(self):
        """Create a report generator with temp directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield ValidationReportGenerator(temp_dir)
    
    @pytest.fixture
    def validation_result(self):
        """Create a sample validation result"""
        return ValidationResult(
            success=True,
            project_type="node",
            installation_log="npm install successful",
            execution_log="Server started on port 3000",
            error_log=None,
            port_listening=3000,
            health_check_passed=True,
            recommendations=["Add error handling", "Include tests"],
            duration_seconds=45.5,
            environment_path="/tmp/test_env"
        )
    
    @pytest.fixture
    def workflow_results(self):
        """Create sample workflow results"""
        return [
            TeamMemberResult(
                team_member=TeamMember.planner,
                output="Created project plan",
                name="planner"
            ),
            TeamMemberResult(
                team_member=TeamMember.coder,
                output="FILENAME: server.js\nconst express = require('express');\n// ... code",
                name="coder"
            )
        ]
    
    def test_generate_json_report(self, report_gen, validation_result, workflow_results):
        """Test JSON report generation"""
        reports = report_gen.generate_report(
            validation_result,
            workflow_results,
            "test_session_123"
        )
        
        assert 'json' in reports
        json_path = reports['json']
        assert os.path.exists(json_path)
        
        # Verify JSON content
        with open(json_path) as f:
            data = json.load(f)
        
        assert data['validation_result']['success'] is True
        assert data['validation_result']['project_type'] == "node"
        assert data['validation_result']['port_listening'] == 3000
        assert len(data['validation_result']['recommendations']) == 2
        assert data['workflow_summary']['total_agents'] == 2
    
    def test_generate_markdown_report(self, report_gen, validation_result, workflow_results):
        """Test Markdown report generation"""
        reports = report_gen.generate_report(
            validation_result,
            workflow_results,
            "test_session_123"
        )
        
        assert 'markdown' in reports
        md_path = reports['markdown']
        assert os.path.exists(md_path)
        
        # Verify Markdown content
        content = Path(md_path).read_text()
        assert "# Validation Report" in content
        assert "✅ SUCCESS" in content
        assert "Project Type: node" in content
        assert "Port Listening: 3000" in content
        assert "## Recommendations" in content
        assert "Add error handling" in content
    
    def test_generate_markdown_report_failure(self, report_gen, workflow_results):
        """Test Markdown report for failed validation"""
        failed_result = ValidationResult(
            success=False,
            project_type="python",
            installation_log="pip install failed",
            execution_log="",
            error_log="ModuleNotFoundError: No module named 'flask'",
            recommendations=["Install missing dependencies"],
            duration_seconds=10.0
        )
        
        reports = report_gen.generate_report(
            failed_result,
            workflow_results,
            "test_fail_session"
        )
        
        content = Path(reports['markdown']).read_text()
        assert "❌ FAILED" in content
        assert "## Error Log" in content
        assert "ModuleNotFoundError" in content
    
    def test_generate_csv_summary(self, report_gen, validation_result, workflow_results):
        """Test CSV summary generation"""
        reports = report_gen.generate_report(
            validation_result,
            workflow_results,
            "test_session_123"
        )
        
        assert 'csv' in reports
        csv_path = reports['csv']
        assert os.path.exists(csv_path)
        
        # Verify CSV content
        content = Path(csv_path).read_text()
        lines = content.strip().split('\n')
        assert len(lines) >= 2  # Header + data
        assert "Session ID" in lines[0]
        assert "test_session_123" in lines[-1]
    
    def test_extract_files_from_output(self, report_gen):
        """Test file extraction from agent output"""
        output = """
Some planning text
FILENAME: app.py
from flask import Flask
app = Flask(__name__)

FILENAME: requirements.txt
flask==2.3.0
gunicorn==20.1.0
"""
        
        files = report_gen._extract_files_from_output(output)
        assert len(files) == 2
        assert 'app.py' in files
        assert 'requirements.txt' in files
    
    def test_generate_summary_report(self, report_gen, validation_result, workflow_results):
        """Test summary report generation"""
        # Generate multiple reports
        for i in range(3):
            report_gen.generate_report(
                validation_result if i < 2 else ValidationResult(
                    success=False,
                    project_type="python",
                    installation_log="Failed",
                    execution_log="",
                    error_log="Error",
                    recommendations=["Fix error"],
                    duration_seconds=5.0
                ),
                workflow_results,
                f"session_{i}"
            )
        
        # Generate summary
        summary_path = report_gen.generate_summary_report()
        assert os.path.exists(summary_path)
        
        with open(summary_path) as f:
            summary = json.load(f)
        
        assert summary['total_validations'] == 3
        assert summary['successful'] == 2
        assert summary['failed'] == 1
        assert 'node' in summary['by_project_type']
        assert 'python' in summary['by_project_type']
        assert summary['average_duration'] > 0
    
    def test_multiple_report_generation(self, report_gen, validation_result, workflow_results):
        """Test that multiple reports don't conflict"""
        reports1 = report_gen.generate_report(
            validation_result,
            workflow_results,
            "session_1"
        )
        
        reports2 = report_gen.generate_report(
            validation_result,
            workflow_results,
            "session_2"
        )
        
        # Ensure different files were created
        assert reports1['json'] != reports2['json']
        assert reports1['markdown'] != reports2['markdown']
        
        # Both should exist
        assert os.path.exists(reports1['json'])
        assert os.path.exists(reports2['json'])