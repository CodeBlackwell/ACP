"""
Environment manager for creating isolated test environments for test execution.
"""
import os
import tempfile
import shutil
import asyncio
from pathlib import Path
from typing import Dict, Optional, List
import subprocess


class EnvironmentManager:
    """Manages isolated environments for application testing"""
    
    def __init__(self):
        self.active_environments: Dict[str, str] = {}
        
    async def create_test_environment(self, 
                                    session_id: str,
                                    base_path: Optional[str] = None) -> str:
        """
        Create an isolated test environment.
        
        Args:
            session_id: Unique session identifier
            base_path: Optional base path for the environment
            
        Returns:
            Path to the created environment
        """
        if base_path:
            env_path = os.path.join(base_path, f"test_env_{session_id}")
            os.makedirs(env_path, exist_ok=True)
        else:
            # Create temporary directory
            env_path = tempfile.mkdtemp(prefix=f"test_env_{session_id}_")
        
        self.active_environments[session_id] = env_path
        
        # Set up basic environment
        await self._setup_environment(env_path)
        
        return env_path
    
    async def _setup_environment(self, env_path: str):
        """Set up the basic test environment"""
        # Create common directories
        for dir_name in ['src', 'tests', 'config']:
            os.makedirs(os.path.join(env_path, dir_name), exist_ok=True)
    
    def cleanup_environment(self, session_id: str):
        """Clean up a test environment"""
        if session_id in self.active_environments:
            env_path = self.active_environments[session_id]
            
            try:
                if os.path.exists(env_path):
                    shutil.rmtree(env_path)
                del self.active_environments[session_id]
            except Exception as e:
                print(f"Warning: Failed to cleanup environment {env_path}: {e}")
    
    def cleanup_all_environments(self):
        """Clean up all active environments"""
        session_ids = list(self.active_environments.keys())
        for session_id in session_ids:
            self.cleanup_environment(session_id)
    
    async def setup_virtual_environment(self, env_path: str, python_version: str = "python3"):
        """Set up a Python virtual environment"""
        venv_path = os.path.join(env_path, "venv")
        
        try:
            # Create virtual environment
            process = await asyncio.create_subprocess_exec(
                python_version, "-m", "venv", venv_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"Failed to create venv: {stderr.decode()}")
            
            return venv_path
            
        except Exception as e:
            print(f"Error setting up virtual environment: {e}")
            return None
    
    async def install_node_modules(self, env_path: str):
        """Initialize node_modules in the environment"""
        try:
            # Initialize npm if package.json exists
            package_json = os.path.join(env_path, "package.json")
            if os.path.exists(package_json):
                process = await asyncio.create_subprocess_exec(
                    "npm", "install",
                    cwd=env_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                await process.communicate()
                
        except Exception as e:
            print(f"Error installing node modules: {e}")
    
    def copy_files_to_environment(self, 
                                 env_path: str, 
                                 files: Dict[str, str]):
        """
        Copy files to the test environment.
        
        Args:
            env_path: Path to the environment
            files: Dict mapping relative paths to content
        """
        for file_path, content in files.items():
            full_path = os.path.join(env_path, file_path)
            
            # Create parent directories
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Write file
            with open(full_path, 'w') as f:
                f.write(content)
    
    def get_environment_info(self, session_id: str) -> Optional[Dict]:
        """Get information about an environment"""
        if session_id not in self.active_environments:
            return None
        
        env_path = self.active_environments[session_id]
        
        if not os.path.exists(env_path):
            return None
        
        # Gather environment info
        info = {
            'path': env_path,
            'size_mb': self._get_directory_size(env_path) / (1024 * 1024),
            'file_count': sum(1 for _ in Path(env_path).rglob('*') if _.is_file()),
            'has_venv': os.path.exists(os.path.join(env_path, 'venv')),
            'has_node_modules': os.path.exists(os.path.join(env_path, 'node_modules')),
        }
        
        return info
    
    def _get_directory_size(self, path: str) -> int:
        """Get total size of directory in bytes"""
        total = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total += os.path.getsize(filepath)
                except:
                    pass
        return total
    
    async def create_isolated_container(self, 
                                      session_id: str,
                                      image: str = "python:3.9-slim") -> Optional[str]:
        """
        Create an isolated Docker container for testing.
        
        Args:
            session_id: Unique session identifier
            image: Docker image to use
            
        Returns:
            Container ID if successful
        """
        try:
            # Create container
            process = await asyncio.create_subprocess_exec(
                "docker", "create", "-it", "--name", f"test_{session_id}", image,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                container_id = stdout.decode().strip()
                return container_id
            
        except Exception as e:
            print(f"Error creating container: {e}")
        
        return None