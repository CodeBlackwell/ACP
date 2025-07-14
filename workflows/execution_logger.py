"""
Execution Logger for tracking all workflow commands, agent exchanges, and metrics.
Provides comprehensive logging with CSV and JSON export capabilities.
"""

import json
import csv
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
import threading


class LogEntryType(Enum):
    """Types of log entries"""
    WORKFLOW_START = "workflow_start"
    WORKFLOW_END = "workflow_end"
    AGENT_REQUEST = "agent_request"
    AGENT_RESPONSE = "agent_response"
    COMMAND_EXECUTION = "command_execution"
    ERROR = "error"
    METRIC = "metric"
    VALIDATION = "validation"


@dataclass
class LogEntry:
    """Individual log entry with all execution details"""
    timestamp: str
    session_id: str
    entry_type: LogEntryType
    agent_name: Optional[str] = None
    action: Optional[str] = None
    input_data: Optional[str] = None
    output_data: Optional[str] = None
    duration_ms: Optional[float] = None
    status: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        try:
            # Manually build dict to avoid potential circular references
            data = {
                'timestamp': self.timestamp,
                'session_id': self.session_id,
                'entry_type': self.entry_type.value,
                'agent_name': self.agent_name,
                'action': self.action,
                'input_data': self.input_data,
                'output_data': self.output_data,
                'duration_ms': self.duration_ms,
                'status': self.status,
                'error_message': self.error_message,
                'metadata': dict(self.metadata) if self.metadata else {}
            }
            return data
        except Exception as e:
            print(f"ERROR in LogEntry.to_dict(): {str(e)}")
            # Return minimal data on error
            return {
                'timestamp': self.timestamp,
                'session_id': self.session_id,
                'entry_type': self.entry_type.value,
                'error': f"Serialization error: {str(e)}"
            }
    
    def to_csv_row(self) -> List[str]:
        """Convert to CSV row format"""
        return [
            self.timestamp,
            self.session_id,
            self.entry_type.value,
            self.agent_name or "",
            self.action or "",
            self.input_data or "",
            self.output_data or "",
            str(self.duration_ms) if self.duration_ms else "",
            self.status or "",
            self.error_message or "",
            json.dumps(self.metadata) if self.metadata else ""
        ]


class ExecutionLogger:
    """
    Main execution logger that tracks all workflow activities.
    Thread-safe implementation for concurrent agent operations.
    """
    
    CSV_HEADERS = [
        "timestamp", "session_id", "entry_type", "agent_name", "action",
        "input_data", "output_data", "duration_ms", "status", "error_message", "metadata"
    ]
    
    def __init__(self, session_id: str, log_dir: Optional[Path] = None):
        """
        Initialize the execution logger.
        
        Args:
            session_id: Unique identifier for this execution session
            log_dir: Directory to store log files (defaults to ./logs)
        """
        self.session_id = session_id
        self.log_dir = log_dir or Path("./logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.entries: List[LogEntry] = []
        self._lock = threading.Lock()
        self._timers: Dict[str, float] = {}
        
        # Track statistics
        self.stats = {
            "start_time": time.time(),
            "end_time": None,
            "total_agent_calls": 0,
            "total_commands": 0,
            "total_errors": 0,
            "agent_durations": {},
            "command_count_by_type": {}
        }
        
        # Log workflow start
        self.log_workflow_start()
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        return datetime.now().isoformat()
    
    def start_timer(self, timer_id: str) -> None:
        """Start a timer for measuring duration"""
        with self._lock:
            self._timers[timer_id] = time.time()
    
    def get_duration(self, timer_id: str) -> Optional[float]:
        """Get duration in milliseconds since timer started"""
        with self._lock:
            if timer_id in self._timers:
                return (time.time() - self._timers[timer_id]) * 1000
        return None
    
    def log_workflow_start(self, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log the start of a workflow execution"""
        entry = LogEntry(
            timestamp=self._get_timestamp(),
            session_id=self.session_id,
            entry_type=LogEntryType.WORKFLOW_START,
            action="workflow_initiated",
            status="started",
            metadata=metadata or {}
        )
        self._add_entry(entry)
    
    def log_workflow_end(self, status: str = "completed", error: Optional[str] = None) -> None:
        """Log the end of a workflow execution"""
        self.stats["end_time"] = time.time()
        duration = (self.stats["end_time"] - self.stats["start_time"]) * 1000
        
        entry = LogEntry(
            timestamp=self._get_timestamp(),
            session_id=self.session_id,
            entry_type=LogEntryType.WORKFLOW_END,
            action="workflow_completed",
            status=status,
            duration_ms=duration,
            error_message=error,
            metadata={"statistics": self.stats}
        )
        self._add_entry(entry)
    
    def log_agent_request(self, agent_name: str, input_data: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Log an agent request and return a request ID for tracking.
        
        Args:
            agent_name: Name of the agent being called
            input_data: Input sent to the agent
            metadata: Additional metadata
            
        Returns:
            Request ID for tracking the response
        """
        request_id = f"{agent_name}_{time.time()}"
        self.start_timer(request_id)
        
        entry = LogEntry(
            timestamp=self._get_timestamp(),
            session_id=self.session_id,
            entry_type=LogEntryType.AGENT_REQUEST,
            agent_name=agent_name,
            action="agent_call",
            input_data=self._truncate_data(input_data),
            status="pending",
            metadata={**(metadata or {}), "request_id": request_id}
        )
        self._add_entry(entry)
        
        with self._lock:
            self.stats["total_agent_calls"] += 1
        
        return request_id
    
    def log_agent_response(self, agent_name: str, request_id: str, output_data: str,
                          status: str = "success", error: Optional[str] = None) -> None:
        """Log an agent response"""
        duration = self.get_duration(request_id)
        
        entry = LogEntry(
            timestamp=self._get_timestamp(),
            session_id=self.session_id,
            entry_type=LogEntryType.AGENT_RESPONSE,
            agent_name=agent_name,
            action="agent_response",
            output_data=self._truncate_data(output_data),
            duration_ms=duration,
            status=status,
            error_message=error,
            metadata={"request_id": request_id}
        )
        self._add_entry(entry)
        
        # Update statistics
        with self._lock:
            if agent_name not in self.stats["agent_durations"]:
                self.stats["agent_durations"][agent_name] = []
            if duration:
                self.stats["agent_durations"][agent_name].append(duration)
            if status != "success":
                self.stats["total_errors"] += 1
    
    def log_command_execution(self, command: str, output: str, duration_ms: float,
                            status: str = "success", error: Optional[str] = None) -> None:
        """Log a command execution (e.g., subprocess call)"""
        entry = LogEntry(
            timestamp=self._get_timestamp(),
            session_id=self.session_id,
            entry_type=LogEntryType.COMMAND_EXECUTION,
            action="command_execution",
            input_data=command,
            output_data=self._truncate_data(output),
            duration_ms=duration_ms,
            status=status,
            error_message=error
        )
        self._add_entry(entry)
        
        with self._lock:
            self.stats["total_commands"] += 1
            # Track command types (first word of command)
            cmd_type = command.split()[0] if command else "unknown"
            self.stats["command_count_by_type"][cmd_type] = \
                self.stats["command_count_by_type"].get(cmd_type, 0) + 1
    
    def log_error(self, error_message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log an error occurrence"""
        entry = LogEntry(
            timestamp=self._get_timestamp(),
            session_id=self.session_id,
            entry_type=LogEntryType.ERROR,
            action="error_occurred",
            status="error",
            error_message=error_message,
            metadata=context or {}
        )
        self._add_entry(entry)
        
        with self._lock:
            self.stats["total_errors"] += 1
    
    def log_metric(self, metric_name: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log a custom metric"""
        entry = LogEntry(
            timestamp=self._get_timestamp(),
            session_id=self.session_id,
            entry_type=LogEntryType.METRIC,
            action=metric_name,
            output_data=str(value),
            metadata=metadata or {}
        )
        self._add_entry(entry)
    
    def _add_entry(self, entry: LogEntry) -> None:
        """Thread-safe addition of log entry"""
        with self._lock:
            self.entries.append(entry)
    
    def _truncate_data(self, data: str, max_length: int = 1000) -> str:
        """Truncate long data for logging if configured to do so"""
        from workflows.logging_config import get_logging_config
        config = get_logging_config()
        
        # Don't truncate if configured for verbose logging or if max lengths are set high
        if config.max_input_length > 10000 and config.max_output_length > 10000:
            return data
            
        if len(data) > max_length:
            return data[:max_length] + "... [truncated]"
        return data
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get current execution statistics"""
        with self._lock:
            stats = self.stats.copy()
            
            # Calculate average durations
            avg_durations = {}
            for agent, durations in stats["agent_durations"].items():
                if durations:
                    avg_durations[agent] = {
                        "avg_ms": sum(durations) / len(durations),
                        "total_calls": len(durations),
                        "total_ms": sum(durations)
                    }
            stats["agent_average_durations"] = avg_durations
            
            # Calculate total duration if ended
            if stats["end_time"]:
                stats["total_duration_seconds"] = stats["end_time"] - stats["start_time"]
            else:
                stats["total_duration_seconds"] = time.time() - stats["start_time"]
            
            return stats
    
    def export_csv(self, filename: Optional[str] = None, additional_dir: Optional[Path] = None) -> Path:
        """
        Export logs to CSV format.
        
        Args:
            filename: Optional custom filename (defaults to execution_report_<session_id>.csv)
            additional_dir: Optional additional directory to save a copy
            
        Returns:
            Path to the exported CSV file
        """
        print(f"DEBUG: export_csv called with filename={filename}")
        
        if not filename:
            filename = f"execution_report_{self.session_id}.csv"
        
        filepath = self.log_dir / filename
        print(f"DEBUG: CSV export path: {filepath}")
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(self.CSV_HEADERS)
            
            with self._lock:
                for entry in self.entries:
                    writer.writerow(entry.to_csv_row())
        
        # Save a copy to additional directory if provided
        if additional_dir:
            additional_dir = Path(additional_dir)
            if additional_dir.exists():
                additional_filepath = additional_dir / filename
                import shutil
                shutil.copy2(filepath, additional_filepath)
                print(f"📋 CSV report also saved to: {additional_filepath}")
        
        return filepath
    
    def export_json(self, filename: Optional[str] = None, additional_dir: Optional[Path] = None) -> Path:
        """
        Export logs to JSON format with hierarchical structure.
        
        Args:
            filename: Optional custom filename (defaults to execution_report_<session_id>.json)
            additional_dir: Optional additional directory to save a copy
            
        Returns:
            Path to the exported JSON file
        """
        print(f"DEBUG: export_json called with filename={filename}")
        
        if not filename:
            filename = f"execution_report_{self.session_id}.json"
        
        filepath = self.log_dir / filename
        print(f"DEBUG: JSON export path: {filepath}")
        
        try:
            with self._lock:
                print(f"DEBUG: Building report with {len(self.entries)} entries")
                
                # Build entries list with debug info
                entries_list = []
                for i, entry in enumerate(self.entries):
                    print(f"DEBUG: Processing entry {i+1}/{len(self.entries)}: {entry.entry_type.value}")
                    try:
                        entry_dict = entry.to_dict()
                        entries_list.append(entry_dict)
                    except Exception as e:
                        print(f"ERROR: Failed to serialize entry {i+1}: {str(e)}")
                        entries_list.append({"error": f"Entry {i+1} serialization failed"})
                
                print(f"DEBUG: Getting statistics...")
                stats = self.get_statistics()
                
                report = {
                    "session_id": self.session_id,
                    "statistics": stats,
                    "entries": entries_list
                }
                print(f"DEBUG: Report built successfully")
            
            print(f"DEBUG: Writing JSON to file...")
            with open(filepath, 'w', encoding='utf-8') as jsonfile:
                json.dump(report, jsonfile, indent=2, default=str)
            print(f"DEBUG: JSON written successfully")
        except Exception as e:
            print(f"ERROR in export_json: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
        
        # Save a copy to additional directory if provided
        if additional_dir:
            additional_dir = Path(additional_dir)
            if additional_dir.exists():
                additional_filepath = additional_dir / filename
                import shutil
                shutil.copy2(filepath, additional_filepath)
                print(f"📋 JSON report also saved to: {additional_filepath}")
        
        return filepath
    
    def get_summary(self) -> str:
        """Get a human-readable summary of the execution"""
        stats = self.get_statistics()
        
        summary = f"""
Execution Summary - Session: {self.session_id}
{'=' * 60}
Duration: {stats['total_duration_seconds']:.2f} seconds
Total Agent Calls: {stats['total_agent_calls']}
Total Commands: {stats['total_commands']}
Total Errors: {stats['total_errors']}

Agent Performance:
"""
        for agent, perf in stats.get('agent_average_durations', {}).items():
            summary += f"  - {agent}: {perf['total_calls']} calls, avg {perf['avg_ms']:.0f}ms\n"
        
        if stats.get('command_count_by_type'):
            summary += "\nCommand Types:\n"
            for cmd, count in stats['command_count_by_type'].items():
                summary += f"  - {cmd}: {count}\n"
        
        return summary