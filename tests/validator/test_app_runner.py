"""
Tests for the app runner agent.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import tempfile
from pathlib import Path

from agents.validator.app_runner_agent import AppRunnerAgent
from shared.data_models import ValidationResult


class TestAppRunnerAgent:
    """Test cases for AppRunnerAgent"""
    
    @pytest.fixture
    def agent(self):
        """Create an app runner agent"""
        return AppRunnerAgent(timeout=30)
    
    @pytest.fixture
    def node_files(self):
        """Sample Node.js project files"""
        return {
            'package.json': '''
{
  "name": "test-app",
  "version": "1.0.0",
  "scripts": {
    "start": "node server.js"
  },
  "dependencies": {
    "express": "^4.18.0"
  }
}
''',
            'server.js': '''
const express = require('express');
const app = express();
const PORT = 3000;

app.get('/', (req, res) => {
  res.send('Hello World!');
});

app.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});
'''
        }
    
    @pytest.fixture
    def python_files(self):
        """Sample Python project files"""
        return {
            'requirements.txt': 'flask==2.3.0\n',
            'app.py': '''
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello World!'

if __name__ == '__main__':
    app.run(port=5000)
'''
        }
    
    def test_detect_project_type_node(self, agent, node_files):
        """Test Node.js project detection"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Write package.json
            (Path(temp_dir) / 'package.json').write_text(node_files['package.json'])
            
            project_type = agent._detect_project_type(temp_dir)
            assert project_type == 'node'
    
    def test_detect_project_type_python(self, agent, python_files):
        """Test Python project detection"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Write requirements.txt
            (Path(temp_dir) / 'requirements.txt').write_text(python_files['requirements.txt'])
            
            project_type = agent._detect_project_type(temp_dir)
            assert project_type == 'python'
    
    def test_detect_project_type_unknown(self, agent):
        """Test unknown project type detection"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_type = agent._detect_project_type(temp_dir)
            assert project_type == 'unknown'
    
    @pytest.mark.asyncio
    async def test_validate_application_success(self, agent, node_files):
        """Test successful application validation"""
        with patch.object(agent, '_install_dependencies', return_value="Install successful"):
            with patch.object(agent, '_run_application', return_value=("Server started", None, 3000)):
                with patch.object(agent, '_check_health', return_value=True):
                    result = await agent.validate_application(
                        node_files,
                        {'health_endpoint': '/'}
                    )
                    
                    assert isinstance(result, ValidationResult)
                    assert result.success is True
                    assert result.project_type == 'node'
                    assert result.port_listening == 3000
                    assert result.health_check_passed is True
    
    @pytest.mark.asyncio
    async def test_validate_application_install_failure(self, agent, python_files):
        """Test validation with installation failure"""
        with patch.object(agent, '_install_dependencies', return_value="ERROR: Failed to install"):
            with patch.object(agent, '_run_application', return_value=("", "Module not found", None)):
                result = await agent.validate_application(python_files)
                
                assert result.success is False
                assert result.error_log is not None
                assert len(result.recommendations) > 0
    
    @pytest.mark.asyncio
    async def test_install_dependencies_node(self, agent):
        """Test Node.js dependency installation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create package.json
            package_json = Path(temp_dir) / 'package.json'
            package_json.write_text('{"name": "test", "dependencies": {}}')
            
            with patch('asyncio.create_subprocess_exec') as mock_subprocess:
                mock_process = AsyncMock()
                mock_process.communicate.return_value = (b"Install complete", b"")
                mock_subprocess.return_value = mock_process
                
                result = await agent._install_dependencies(temp_dir, 'node', 30)
                
                assert "Install complete" in result
                mock_subprocess.assert_called_with(
                    'npm', 'install',
                    cwd=temp_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
    
    @pytest.mark.asyncio
    async def test_run_application_with_port_detection(self, agent):
        """Test running application with port detection"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('asyncio.create_subprocess_exec') as mock_subprocess:
                mock_process = AsyncMock()
                mock_process.returncode = None  # Still running
                mock_process.pid = 12345
                mock_subprocess.return_value = mock_process
                
                with patch.object(agent, '_detect_listening_port', return_value=8080):
                    output, error, port = await agent._run_application(
                        temp_dir, 'node', {}, 30
                    )
                    
                    assert port == 8080
                    assert error is None
    
    def test_get_node_run_command_with_scripts(self, agent):
        """Test getting Node.js run command from package.json scripts"""
        with tempfile.TemporaryDirectory() as temp_dir:
            package_json = Path(temp_dir) / 'package.json'
            package_json.write_text('''
{
  "scripts": {
    "start": "node index.js",
    "dev": "nodemon index.js"
  }
}
''')
            
            cmd = agent._get_node_run_command(temp_dir)
            assert cmd == ['npm', 'start']
    
    def test_get_python_run_command_app_py(self, agent):
        """Test getting Python run command for app.py"""
        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / 'app.py').touch()
            
            cmd = agent._get_python_run_command(temp_dir)
            assert cmd == ['python', 'app.py']
    
    def test_generate_recommendations(self, agent):
        """Test recommendation generation"""
        recommendations = agent._generate_recommendations(
            'node',
            'npm ERR! missing script: start',
            '',
            'Error: Cannot find module express'
        )
        
        assert len(recommendations) > 0
        assert any('dependencies' in rec for rec in recommendations)
    
    @pytest.mark.asyncio
    async def test_detect_listening_port(self, agent):
        """Test port detection from process"""
        with patch('asyncio.create_subprocess_shell') as mock_shell:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (
                b"node    12345 user   23u  IPv4  0x123456      0t0  TCP *:3000 (LISTEN)\n",
                b""
            )
            mock_shell.return_value = mock_process
            
            port = await agent._detect_listening_port(12345)
            assert port == 3000
    
    @pytest.mark.asyncio
    async def test_check_health(self, agent):
        """Test health endpoint checking"""
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            
            mock_session.get.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value.__aenter__.return_value = mock_session
            
            result = await agent._check_health(3000, '/health')
            assert result is True