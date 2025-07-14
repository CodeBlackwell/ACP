"""
Log Exporter for generating execution reports in CSV and JSON formats.
Provides enhanced formatting and analysis capabilities.
"""

import csv
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from collections import defaultdict

from shared.data_models import WorkflowExecutionLog, AgentExchange, CommandExecution
from workflows.execution_logger import ExecutionLogger


class LogExporter:
    """
    Export execution logs to various formats with analysis and formatting.
    """
    
    def __init__(self, log_dir: Path = None):
        """
        Initialize the log exporter.
        
        Args:
            log_dir: Directory to save exported files (defaults to ./logs)
        """
        self.log_dir = log_dir or Path("./logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def export_from_logger(self, logger: ExecutionLogger, 
                          base_filename: Optional[str] = None,
                          additional_dir: Optional[Path] = None) -> Tuple[Path, Path]:
        """
        Export logs from ExecutionLogger instance to both CSV and JSON.
        
        Args:
            logger: ExecutionLogger instance with execution data
            base_filename: Base filename without extension (defaults to execution_report_<session_id>)
            additional_dir: Optional additional directory to save copies (e.g., generated code dir)
            
        Returns:
            Tuple of (csv_path, json_path)
        """
        if not base_filename:
            base_filename = f"execution_report_{logger.session_id}"
        
        from workflows.logging_config import get_logging_config
        config = get_logging_config()
        
        csv_path = None
        json_path = None
        
        if "csv" in config.export_formats:
            print(f"DEBUG: Starting CSV export...")
            csv_path = logger.export_csv(f"{base_filename}.csv", additional_dir)
            print(f"DEBUG: CSV export completed: {csv_path}")
        
        if "json" in config.export_formats:
            print(f"DEBUG: Starting JSON export...")
            try:
                json_path = logger.export_json(f"{base_filename}.json", additional_dir)
                print(f"DEBUG: JSON export completed: {json_path}")
            except Exception as e:
                print(f"WARNING: JSON export failed: {str(e)}")
                json_path = None
        
        # Return paths, using placeholder if format not exported
        csv_path = csv_path or Path("no_csv_export")
        json_path = json_path or Path("no_json_export")
        
        return csv_path, json_path
    
    def export_from_workflow_log(self, workflow_log: WorkflowExecutionLog,
                               base_filename: Optional[str] = None) -> Tuple[Path, Path]:
        """
        Export logs from WorkflowExecutionLog to both CSV and JSON.
        
        Args:
            workflow_log: WorkflowExecutionLog instance
            base_filename: Base filename without extension
            
        Returns:
            Tuple of (csv_path, json_path)
        """
        if not base_filename:
            base_filename = f"execution_report_{workflow_log.session_id}"
        
        csv_path = self._export_workflow_csv(workflow_log, f"{base_filename}.csv")
        json_path = self._export_workflow_json(workflow_log, f"{base_filename}.json")
        
        return csv_path, json_path
    
    def _export_workflow_csv(self, log: WorkflowExecutionLog, filename: str) -> Path:
        """Export WorkflowExecutionLog to CSV format"""
        filepath = self.log_dir / filename
        
        headers = [
            "timestamp", "session_id", "entry_type", "agent_name", "action",
            "input_data", "output_data", "duration_ms", "status", "error_message",
            "command", "return_code", "working_directory"
        ]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            
            # Write workflow start
            writer.writerow([
                log.start_timestamp,
                log.session_id,
                "workflow_start",
                "",
                "workflow_initiated",
                log.original_request[:500],  # Truncate long requests
                "",
                "",
                "started",
                "",
                "",
                "",
                ""
            ])
            
            # Write agent exchanges
            for exchange in log.agent_exchanges:
                writer.writerow([
                    exchange.start_timestamp,
                    log.session_id,
                    "agent_request",
                    exchange.agent_name,
                    "agent_call",
                    self._truncate(exchange.input_data),
                    "",
                    "",
                    "pending",
                    "",
                    "",
                    "",
                    ""
                ])
                
                if exchange.output_data:
                    writer.writerow([
                        exchange.end_timestamp or exchange.start_timestamp,
                        log.session_id,
                        "agent_response",
                        exchange.agent_name,
                        "agent_response",
                        "",
                        self._truncate(exchange.output_data),
                        exchange.duration_ms or "",
                        exchange.status,
                        exchange.error_message or "",
                        "",
                        "",
                        ""
                    ])
            
            # Write command executions
            for cmd in log.command_executions:
                writer.writerow([
                    cmd.timestamp,
                    log.session_id,
                    "command_execution",
                    "",
                    "command_execution",
                    cmd.command,
                    self._truncate(cmd.output),
                    cmd.duration_ms,
                    "success" if cmd.return_code == 0 else "failed",
                    cmd.error_output or "",
                    cmd.command,
                    cmd.return_code,
                    cmd.working_directory or ""
                ])
            
            # Write errors
            for error in log.errors:
                writer.writerow([
                    error.get("timestamp", log.start_timestamp),
                    log.session_id,
                    "error",
                    "",
                    error.get("type", "error_occurred"),
                    "",
                    "",
                    "",
                    "error",
                    error.get("message", ""),
                    "",
                    "",
                    ""
                ])
            
            # Write workflow end
            if log.end_timestamp:
                writer.writerow([
                    log.end_timestamp,
                    log.session_id,
                    "workflow_end",
                    "",
                    "workflow_completed",
                    "",
                    json.dumps(log.get_statistics()),
                    log.total_duration_ms or "",
                    log.status,
                    "",
                    "",
                    "",
                    ""
                ])
        
        return filepath
    
    def _export_workflow_json(self, log: WorkflowExecutionLog, filename: str) -> Path:
        """Export WorkflowExecutionLog to enhanced JSON format"""
        filepath = self.log_dir / filename
        
        # Build hierarchical structure
        report = {
            "session_id": log.session_id,
            "workflow_type": log.workflow_type,
            "original_request": log.original_request,
            "timestamps": {
                "start": log.start_timestamp,
                "end": log.end_timestamp,
                "duration_ms": log.total_duration_ms
            },
            "status": log.status,
            "statistics": log.get_statistics(),
            "execution_timeline": self._build_timeline(log),
            "agent_interactions": self._group_agent_interactions(log),
            "command_executions": [self._format_command(cmd) for cmd in log.command_executions],
            "errors": log.errors,
            "metrics": log.metrics
        }
        
        with open(filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump(report, jsonfile, indent=2, default=str)
        
        return filepath
    
    def _build_timeline(self, log: WorkflowExecutionLog) -> List[Dict[str, Any]]:
        """Build a chronological timeline of all events"""
        events = []
        
        # Add workflow start
        events.append({
            "timestamp": log.start_timestamp,
            "type": "workflow_start",
            "description": f"Started {log.workflow_type} workflow"
        })
        
        # Add agent interactions
        for exchange in log.agent_exchanges:
            events.append({
                "timestamp": exchange.start_timestamp,
                "type": "agent_request",
                "agent": exchange.agent_name,
                "description": f"Called {exchange.agent_name}"
            })
            
            if exchange.end_timestamp:
                events.append({
                    "timestamp": exchange.end_timestamp,
                    "type": "agent_response",
                    "agent": exchange.agent_name,
                    "description": f"{exchange.agent_name} responded",
                    "duration_ms": exchange.duration_ms,
                    "status": exchange.status
                })
        
        # Add command executions
        for cmd in log.command_executions:
            events.append({
                "timestamp": cmd.timestamp,
                "type": "command_execution",
                "command": cmd.command.split()[0] if cmd.command else "unknown",
                "description": f"Executed: {cmd.command[:50]}...",
                "duration_ms": cmd.duration_ms,
                "status": "success" if cmd.return_code == 0 else "failed"
            })
        
        # Add errors
        for error in log.errors:
            events.append({
                "timestamp": error.get("timestamp", log.start_timestamp),
                "type": "error",
                "description": error.get("message", "Unknown error")
            })
        
        # Add workflow end
        if log.end_timestamp:
            events.append({
                "timestamp": log.end_timestamp,
                "type": "workflow_end",
                "description": f"Completed with status: {log.status}",
                "total_duration_ms": log.total_duration_ms
            })
        
        # Sort by timestamp
        events.sort(key=lambda x: x["timestamp"])
        
        return events
    
    def _group_agent_interactions(self, log: WorkflowExecutionLog) -> Dict[str, List[Dict[str, Any]]]:
        """Group agent interactions by agent name"""
        grouped = defaultdict(list)
        
        for exchange in log.agent_exchanges:
            interaction = {
                "request_id": exchange.request_id,
                "timestamps": {
                    "start": exchange.start_timestamp,
                    "end": exchange.end_timestamp
                },
                "duration_ms": exchange.duration_ms,
                "status": exchange.status,
                "input_preview": exchange.input_data[:200] + "..." if len(exchange.input_data) > 200 else exchange.input_data,
                "output_preview": (exchange.output_data[:200] + "..." if len(exchange.output_data) > 200 else exchange.output_data) if exchange.output_data else None,
                "error": exchange.error_message
            }
            grouped[exchange.agent_name].append(interaction)
        
        return dict(grouped)
    
    def _format_command(self, cmd: CommandExecution) -> Dict[str, Any]:
        """Format command execution for JSON output"""
        return {
            "timestamp": cmd.timestamp,
            "command": cmd.command,
            "working_directory": cmd.working_directory,
            "duration_ms": cmd.duration_ms,
            "return_code": cmd.return_code,
            "status": "success" if cmd.return_code == 0 else "failed",
            "output_preview": cmd.output[:200] + "..." if len(cmd.output) > 200 else cmd.output,
            "error_output": cmd.error_output
        }
    
    def _truncate(self, text: str, max_length: int = 500) -> str:
        """Truncate text for CSV output if needed"""
        if not text:
            return ""
        
        # Check logging config to see if truncation should be disabled
        from workflows.logging_config import get_logging_config
        config = get_logging_config()
        
        # Don't truncate if configured for no truncation
        if not config.truncate_commands or (config.max_input_length > 10000 and config.max_output_length > 10000):
            # Still need to escape for CSV - replace newlines and quotes
            return text.replace('\n', '\\n').replace('"', '""')
            
        if len(text) > max_length:
            return text[:max_length] + "... [truncated]"
        return text
    
    def generate_summary_report(self, logger: ExecutionLogger) -> str:
        """
        Generate a human-readable summary report.
        
        Args:
            logger: ExecutionLogger instance
            
        Returns:
            Formatted summary report string
        """
        stats = logger.get_statistics()
        
        report = f"""
EXECUTION SUMMARY REPORT
========================
Session ID: {logger.session_id}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

OVERVIEW
--------
Total Duration: {stats['total_duration_seconds']:.2f} seconds
Total Agent Calls: {stats['total_agent_calls']}
Total Commands Executed: {stats['total_commands']}
Total Errors: {stats['total_errors']}

AGENT PERFORMANCE
-----------------
"""
        
        for agent, perf in stats.get('agent_average_durations', {}).items():
            report += f"{agent}:\n"
            report += f"  - Calls: {perf['total_calls']}\n"
            report += f"  - Total Time: {perf['total_ms']:.0f}ms\n"
            report += f"  - Average Time: {perf['avg_ms']:.0f}ms\n\n"
        
        if stats.get('command_count_by_type'):
            report += "COMMAND BREAKDOWN\n"
            report += "-----------------\n"
            for cmd_type, count in sorted(stats['command_count_by_type'].items(), 
                                        key=lambda x: x[1], reverse=True):
                report += f"  {cmd_type}: {count}\n"
        
        if stats['total_errors'] > 0:
            report += f"\n⚠️  WARNING: {stats['total_errors']} errors occurred during execution\n"
        
        report += "\nEXPORTED FILES\n"
        report += "--------------\n"
        report += f"CSV Report: execution_report_{logger.session_id}.csv\n"
        report += f"JSON Report: execution_report_{logger.session_id}.json\n"
        
        return report