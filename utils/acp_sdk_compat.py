"""
ACP SDK Compatibility Module

This module provides compatibility fixes for acp_sdk when used with modern versions of uvicorn.
The acp_sdk package expects certain attributes in uvicorn.config that don't exist in newer versions.
"""
import sys
import importlib


def patch_uvicorn_for_acp_sdk():
    """
    Apply compatibility patches to uvicorn.config module for acp_sdk compatibility.
    
    This function must be called before importing acp_sdk.
    """
    # Import necessary modules
    import uvicorn.config
    import configparser
    from typing import IO, Any
    
    # Apply patches for missing attributes that acp_sdk expects
    if not hasattr(uvicorn.config, 'RawConfigParser'):
        uvicorn.config.RawConfigParser = configparser.RawConfigParser
    
    if not hasattr(uvicorn.config, 'IO'):
        uvicorn.config.IO = IO
    
    print("✅ Applied uvicorn compatibility patches for acp_sdk")


def ensure_compatibility():
    """
    Ensure compatibility between acp_sdk and uvicorn.
    This should be called at the very beginning of your application.
    """
    # Check if acp_sdk has already been imported
    if 'acp_sdk' in sys.modules:
        print("⚠️  Warning: acp_sdk already imported. Compatibility patches may not work correctly.")
        print("   Please import utils.acp_sdk_compat before importing acp_sdk")
        return
    
    # Apply the patches
    patch_uvicorn_for_acp_sdk()