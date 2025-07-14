"""
Logging configuration for workflow execution tracking.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class LoggingConfig:
    """Configuration for execution logging"""
    
    # Enable/disable logging
    enabled: bool = True
    
    # Log levels
    log_agent_exchanges: bool = True
    log_command_executions: bool = True
    log_errors: bool = True
    log_metrics: bool = True
    log_validation_results: bool = True
    
    # Output settings
    log_directory: Path = field(default_factory=lambda: Path("./logs"))
    max_log_size_mb: int = 100  # Maximum size of log files
    retention_days: int = 30  # How long to keep logs
    
    # Performance settings
    buffer_size: int = 100  # Number of entries to buffer before writing
    async_write: bool = True  # Write logs asynchronously
    
    # Data truncation
    max_input_length: int = 1000000  # Maximum length of input data to log
    max_output_length: int = 1000000  # Maximum length of output data to log
    truncate_commands: bool = False  # Truncate long commands
    
    # Export settings
    auto_export_on_completion: bool = True  # Automatically export logs when workflow completes
    export_formats: list = field(default_factory=lambda: ["csv"])  # JSON export disabled due to hanging issue
    include_summary_report: bool = True
    
    # Privacy settings
    redact_sensitive_data: bool = True  # Redact potential sensitive information
    sensitive_patterns: list = field(default_factory=lambda: [
        r"api[_-]?key",
        r"password",
        r"secret",
        r"token",
        r"auth",
        r"credential"
    ])
    
    @classmethod
    def from_env(cls) -> "LoggingConfig":
        """Create configuration from environment variables"""
        config = cls()
        
        # Override from environment
        if os.getenv("WORKFLOW_LOGGING_ENABLED") is not None:
            config.enabled = os.getenv("WORKFLOW_LOGGING_ENABLED").lower() == "true"
        
        if os.getenv("WORKFLOW_LOG_DIR"):
            config.log_directory = Path(os.getenv("WORKFLOW_LOG_DIR"))
        
        if os.getenv("WORKFLOW_LOG_RETENTION_DAYS"):
            config.retention_days = int(os.getenv("WORKFLOW_LOG_RETENTION_DAYS"))
        
        if os.getenv("WORKFLOW_LOG_REDACT_SENSITIVE"):
            config.redact_sensitive_data = os.getenv("WORKFLOW_LOG_REDACT_SENSITIVE").lower() == "true"
        
        return config
    
    @classmethod
    def minimal(cls) -> "LoggingConfig":
        """Create minimal logging configuration (errors only)"""
        return cls(
            log_agent_exchanges=True,
            log_command_executions=True,
            log_errors=True,
            log_metrics=True,
            log_validation_results=True,
            auto_export_on_completion=True
        )
    
    @classmethod
    def verbose(cls) -> "LoggingConfig":
        """Create verbose logging configuration (everything)"""
        return cls(
            log_agent_exchanges=True,
            log_command_executions=True,
            log_errors=True,
            log_metrics=True,
            log_validation_results=True,
            max_input_length=1000000,
            max_output_length=1000000,
            truncate_commands=False
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "enabled": self.enabled,
            "log_levels": {
                "agent_exchanges": self.log_agent_exchanges,
                "command_executions": self.log_command_executions,
                "errors": self.log_errors,
                "metrics": self.log_metrics,
                "validation_results": self.log_validation_results
            },
            "output": {
                "directory": str(self.log_directory),
                "max_size_mb": self.max_log_size_mb,
                "retention_days": self.retention_days
            },
            "performance": {
                "buffer_size": self.buffer_size,
                "async_write": self.async_write
            },
            "data": {
                "max_input_length": self.max_input_length,
                "max_output_length": self.max_output_length,
                "truncate_commands": self.truncate_commands
            },
            "export": {
                "auto_export": self.auto_export_on_completion,
                "formats": self.export_formats,
                "include_summary": self.include_summary_report
            },
            "privacy": {
                "redact_sensitive": self.redact_sensitive_data,
                "patterns": self.sensitive_patterns
            }
        }


# Global configuration instance
_global_config: Optional[LoggingConfig] = None


def get_logging_config() -> LoggingConfig:
    """Get the global logging configuration"""
    global _global_config
    if _global_config is None:
        _global_config = LoggingConfig.from_env()
    return _global_config


def set_logging_config(config: LoggingConfig) -> None:
    """Set the global logging configuration"""
    global _global_config
    _global_config = config


def reset_logging_config() -> None:
    """Reset logging configuration to defaults"""
    global _global_config
    _global_config = None