"""
Application runner agent for post-workflow validation.
Installs dependencies and attempts to run generated applications.
"""
import os
import asyncio
import subprocess
import json
import time
import tempfile
import shutil
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import re

from shared.data_models import ValidationResult


class AppRunnerAgent:
    """Agent responsible for running generated applications"""
    
    def __init__(self, timeout: int = 60):
        self.timeout = timeout
        self.project_detectors = {
            'node': self._detect_node_project,
            'python': self._detect_python_project,
            'rust': self._detect_rust_project,
            'go': self._detect_go_project,
        }
        
    async def validate_application(self, 
                                 generated_files: Dict[str, str], 
                                 validation_config: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Validate generated application by installing and running it.
        
        Args:
            generated_files: Dict mapping file paths to content
            validation_config: Optional configuration for validation
            
        Returns:
            ValidationResult with detailed information
        """
        start_time = time.time()
        config = validation_config or {}
        timeout = config.get('timeout', self.timeout)
        
        # Create temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Write generated files to temp directory
                for file_path, content in generated_files.items():
                    full_path = Path(temp_dir) / file_path
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(content)
                
                # Detect project type
                project_type = self._detect_project_type(temp_dir)
                
                # Install dependencies
                install_log = await self._install_dependencies(temp_dir, project_type, timeout)
                
                # Run application
                execution_log, error_log, port = await self._run_application(
                    temp_dir, project_type, config, timeout
                )
                
                # Health check if configured
                health_passed = False
                if port and config.get('health_endpoint'):
                    health_passed = await self._check_health(port, config['health_endpoint'])
                
                # Generate recommendations
                recommendations = self._generate_recommendations(
                    project_type, install_log, execution_log, error_log
                )
                
                duration = time.time() - start_time
                
                return ValidationResult(
                    success=bool(port) or (error_log is None),
                    project_type=project_type,
                    installation_log=install_log,
                    execution_log=execution_log,
                    error_log=error_log,
                    port_listening=port,
                    health_check_passed=health_passed,
                    recommendations=recommendations,
                    duration_seconds=duration,
                    environment_path=temp_dir
                )
                
            except Exception as e:
                duration = time.time() - start_time
                return ValidationResult(
                    success=False,
                    project_type="unknown",
                    installation_log="",
                    execution_log="",
                    error_log=str(e),
                    recommendations=["Fix the error: " + str(e)],
                    duration_seconds=duration
                )
    
    def _detect_project_type(self, project_dir: str) -> str:
        """Detect the type of project based on files present"""
        for project_type, detector in self.project_detectors.items():
            if detector(project_dir):
                return project_type
        return "unknown"
    
    def _detect_node_project(self, project_dir: str) -> bool:
        """Detect if this is a Node.js project"""
        indicators = ['package.json', 'index.js', 'app.js', 'server.js']
        return any((Path(project_dir) / ind).exists() for ind in indicators)
    
    def _detect_python_project(self, project_dir: str) -> bool:
        """Detect if this is a Python project"""
        indicators = ['requirements.txt', 'setup.py', 'pyproject.toml', 'main.py', 'app.py']
        return any((Path(project_dir) / ind).exists() for ind in indicators)
    
    def _detect_rust_project(self, project_dir: str) -> bool:
        """Detect if this is a Rust project"""
        return (Path(project_dir) / 'Cargo.toml').exists()
    
    def _detect_go_project(self, project_dir: str) -> bool:
        """Detect if this is a Go project"""
        indicators = ['go.mod', 'main.go']
        return any((Path(project_dir) / ind).exists() for ind in indicators)
    
    async def _install_dependencies(self, project_dir: str, project_type: str, timeout: int) -> str:
        """Install project dependencies"""
        install_commands = {
            'node': ['npm', 'install'],
            'python': ['pip', 'install', '-r', 'requirements.txt'],
            'rust': ['cargo', 'build'],
            'go': ['go', 'mod', 'download'],
        }
        
        if project_type not in install_commands:
            return f"No install command for project type: {project_type}"
        
        # Special handling for Python without requirements.txt
        if project_type == 'python' and not (Path(project_dir) / 'requirements.txt').exists():
            return "No requirements.txt found, skipping dependency installation"
        
        cmd = install_commands[project_type]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=project_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=timeout
            )
            
            output = stdout.decode() if stdout else ""
            error = stderr.decode() if stderr else ""
            
            return f"STDOUT:\n{output}\n\nSTDERR:\n{error}"
            
        except asyncio.TimeoutError:
            return f"Installation timed out after {timeout} seconds"
        except Exception as e:
            return f"Installation failed: {str(e)}"
    
    async def _run_application(self, 
                             project_dir: str, 
                             project_type: str,
                             config: Dict[str, Any],
                             timeout: int) -> Tuple[str, Optional[str], Optional[int]]:
        """Run the application and return logs and port if detected"""
        run_commands = {
            'node': self._get_node_run_command,
            'python': self._get_python_run_command,
            'rust': lambda d: ['cargo', 'run'],
            'go': lambda d: ['go', 'run', '.'],
        }
        
        if project_type not in run_commands:
            return "", f"No run command for project type: {project_type}", None
        
        cmd = run_commands[project_type](project_dir)
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=project_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Give the app time to start
            await asyncio.sleep(2)
            
            # Check if process is still running
            if process.returncode is not None:
                stdout, stderr = await process.communicate()
                return stdout.decode(), stderr.decode(), None
            
            # Try to detect listening port
            port = await self._detect_listening_port(process.pid)
            
            # Collect some output
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=5  # Short timeout to get initial output
                )
                output = stdout.decode() if stdout else ""
                error = stderr.decode() if stderr else ""
            except asyncio.TimeoutError:
                # Process still running, which is good
                output = "Application started successfully"
                error = None
                
                # Terminate the process
                process.terminate()
                await process.wait()
            
            return output, error, port
            
        except Exception as e:
            return "", f"Failed to run application: {str(e)}", None
    
    def _get_node_run_command(self, project_dir: str) -> List[str]:
        """Get the appropriate run command for a Node.js project"""
        package_json_path = Path(project_dir) / 'package.json'
        
        if package_json_path.exists():
            try:
                with open(package_json_path) as f:
                    package_data = json.load(f)
                    
                scripts = package_data.get('scripts', {})
                if 'start' in scripts:
                    return ['npm', 'start']
                elif 'dev' in scripts:
                    return ['npm', 'run', 'dev']
            except:
                pass
        
        # Default commands
        if (Path(project_dir) / 'index.js').exists():
            return ['node', 'index.js']
        elif (Path(project_dir) / 'app.js').exists():
            return ['node', 'app.js']
        elif (Path(project_dir) / 'server.js').exists():
            return ['node', 'server.js']
        
        return ['npm', 'start']
    
    def _get_python_run_command(self, project_dir: str) -> List[str]:
        """Get the appropriate run command for a Python project"""
        if (Path(project_dir) / 'main.py').exists():
            return ['python', 'main.py']
        elif (Path(project_dir) / 'app.py').exists():
            return ['python', 'app.py']
        elif (Path(project_dir) / 'server.py').exists():
            return ['python', 'server.py']
        
        return ['python', 'main.py']
    
    async def _detect_listening_port(self, pid: int) -> Optional[int]:
        """Detect which port the process is listening on"""
        try:
            # Use lsof to find listening ports
            process = await asyncio.create_subprocess_shell(
                f"lsof -P -n -i -a -p {pid} | grep LISTEN",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, _ = await process.communicate()
            output = stdout.decode()
            
            # Parse port from lsof output
            for line in output.splitlines():
                match = re.search(r':(\d+)\s+\(LISTEN\)', line)
                if match:
                    return int(match.group(1))
                    
        except:
            pass
        
        return None
    
    async def _check_health(self, port: int, endpoint: str) -> bool:
        """Check if health endpoint responds"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                url = f"http://localhost:{port}{endpoint}"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    return resp.status == 200
        except:
            return False
    
    def _generate_recommendations(self, 
                                project_type: str,
                                install_log: str,
                                execution_log: str,
                                error_log: Optional[str]) -> List[str]:
        """Generate recommendations based on validation results"""
        recommendations = []
        
        if error_log:
            if "command not found" in error_log:
                recommendations.append(f"Ensure {project_type} runtime is installed")
            if "Module not found" in error_log or "Cannot find module" in error_log:
                recommendations.append("Check that all required dependencies are listed")
            if "Permission denied" in error_log:
                recommendations.append("Check file permissions")
            if "address already in use" in error_log:
                recommendations.append("The port is already in use, consider making it configurable")
        
        if "error" in install_log.lower():
            recommendations.append("Fix dependency installation errors")
        
        if not error_log and execution_log:
            if "listening" not in execution_log.lower() and "started" not in execution_log.lower():
                recommendations.append("Add startup logging to confirm the application is running")
        
        return recommendations