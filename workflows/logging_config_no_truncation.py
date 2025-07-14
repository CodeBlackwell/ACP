"""
Logging configuration with no truncation for full debugging.
"""

from workflows.logging_config import LoggingConfig, set_logging_config

def setup_no_truncation_logging():
    """
    Set up logging configuration with no truncation.
    All agent inputs and outputs will be logged in full.
    """
    config = LoggingConfig(
        # Enable all logging
        enabled=True,
        log_agent_exchanges=True,
        log_command_executions=True,
        log_errors=True,
        log_metrics=True,
        log_validation_results=True,
        
        # No truncation - set very high limits
        max_input_length=1000000,  # 1MB
        max_output_length=1000000,  # 1MB
        truncate_commands=False,
        
        # Export settings
        auto_export_on_completion=True,
        export_formats=["csv", "json"],
        include_summary_report=True,
        
        # Performance settings
        buffer_size=1000,  # Larger buffer for more data
        async_write=True,
        
        # Privacy settings
        redact_sensitive_data=False  # Disable for full debugging
    )
    
    set_logging_config(config)
    print("📝 Logging configured with NO TRUNCATION")
    print("   - Max input length: 1MB")
    print("   - Max output length: 1MB")
    print("   - Command truncation: Disabled")
    print("   - Sensitive data redaction: Disabled")
    
    return config

if __name__ == "__main__":
    # Example usage
    setup_no_truncation_logging()