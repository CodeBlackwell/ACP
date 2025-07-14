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
    # For now, no patches are needed
    # This function is kept as a placeholder in case future compatibility issues arise
    pass


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