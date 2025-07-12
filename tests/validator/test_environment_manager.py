"""
Tests for the environment manager.
"""
import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock

from agents.validator.environment_manager import EnvironmentManager


class TestEnvironmentManager:
    """Test cases for EnvironmentManager"""
    
    @pytest.fixture
    def env_manager(self):
        """Create an environment manager"""
        return EnvironmentManager()
    
    @pytest.mark.asyncio
    async def test_create_test_environment(self, env_manager):
        """Test creating a test environment"""
        session_id = "test_session_123"
        env_path = await env_manager.create_test_environment(session_id)
        
        assert os.path.exists(env_path)
        assert session_id in env_manager.active_environments
        assert env_manager.active_environments[session_id] == env_path
        
        # Check subdirectories were created
        assert os.path.exists(os.path.join(env_path, 'src'))
        assert os.path.exists(os.path.join(env_path, 'tests'))
        assert os.path.exists(os.path.join(env_path, 'config'))
        
        # Cleanup
        env_manager.cleanup_environment(session_id)
    
    @pytest.mark.asyncio
    async def test_create_test_environment_with_base_path(self, env_manager):
        """Test creating environment with specified base path"""
        with tempfile.TemporaryDirectory() as base_dir:
            session_id = "test_session_456"
            env_path = await env_manager.create_test_environment(session_id, base_dir)
            
            assert env_path.startswith(base_dir)
            assert os.path.exists(env_path)
            
            # Cleanup
            env_manager.cleanup_environment(session_id)
    
    def test_cleanup_environment(self, env_manager):
        """Test environment cleanup"""
        # Create a temp directory manually
        temp_dir = tempfile.mkdtemp()
        session_id = "cleanup_test"
        env_manager.active_environments[session_id] = temp_dir
        
        # Create a file in the directory
        test_file = os.path.join(temp_dir, "test.txt")
        Path(test_file).write_text("test content")
        
        # Cleanup
        env_manager.cleanup_environment(session_id)
        
        assert not os.path.exists(temp_dir)
        assert session_id not in env_manager.active_environments
    
    def test_cleanup_all_environments(self, env_manager):
        """Test cleaning up all environments"""
        # Create multiple environments
        temp_dirs = []
        for i in range(3):
            temp_dir = tempfile.mkdtemp()
            temp_dirs.append(temp_dir)
            env_manager.active_environments[f"session_{i}"] = temp_dir
        
        # Cleanup all
        env_manager.cleanup_all_environments()
        
        assert len(env_manager.active_environments) == 0
        for temp_dir in temp_dirs:
            assert not os.path.exists(temp_dir)
    
    @pytest.mark.asyncio
    async def test_setup_virtual_environment(self, env_manager):
        """Test Python virtual environment setup"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('asyncio.create_subprocess_exec') as mock_subprocess:
                mock_process = AsyncMock()
                mock_process.communicate.return_value = (b"", b"")
                mock_process.returncode = 0
                mock_subprocess.return_value = mock_process
                
                venv_path = await env_manager.setup_virtual_environment(temp_dir)
                
                assert venv_path == os.path.join(temp_dir, "venv")
                mock_subprocess.assert_called_with(
                    "python3", "-m", "venv", venv_path,
                    stdout=-1,
                    stderr=-1
                )
    
    @pytest.mark.asyncio
    async def test_install_node_modules(self, env_manager):
        """Test Node.js module installation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create package.json
            package_json = os.path.join(temp_dir, "package.json")
            Path(package_json).write_text('{"name": "test"}')
            
            with patch('asyncio.create_subprocess_exec') as mock_subprocess:
                mock_process = AsyncMock()
                mock_process.communicate.return_value = (b"", b"")
                mock_subprocess.return_value = mock_process
                
                await env_manager.install_node_modules(temp_dir)
                
                mock_subprocess.assert_called_with(
                    "npm", "install",
                    cwd=temp_dir,
                    stdout=-1,
                    stderr=-1
                )
    
    def test_copy_files_to_environment(self, env_manager):
        """Test copying files to environment"""
        with tempfile.TemporaryDirectory() as temp_dir:
            files = {
                "app.py": "print('Hello')",
                "src/module.py": "def func(): pass",
                "config/settings.json": '{"debug": true}'
            }
            
            env_manager.copy_files_to_environment(temp_dir, files)
            
            # Verify files were created
            for file_path, content in files.items():
                full_path = os.path.join(temp_dir, file_path)
                assert os.path.exists(full_path)
                assert Path(full_path).read_text() == content
    
    def test_get_environment_info(self, env_manager):
        """Test getting environment information"""
        with tempfile.TemporaryDirectory() as temp_dir:
            session_id = "info_test"
            env_manager.active_environments[session_id] = temp_dir
            
            # Create some files
            Path(os.path.join(temp_dir, "file1.txt")).write_text("content1")
            Path(os.path.join(temp_dir, "file2.txt")).write_text("content2")
            os.makedirs(os.path.join(temp_dir, "venv"))
            
            info = env_manager.get_environment_info(session_id)
            
            assert info is not None
            assert info['path'] == temp_dir
            assert info['file_count'] == 2
            assert info['has_venv'] is True
            assert info['has_node_modules'] is False
            assert info['size_mb'] > 0
    
    def test_get_environment_info_nonexistent(self, env_manager):
        """Test getting info for non-existent environment"""
        info = env_manager.get_environment_info("nonexistent")
        assert info is None
    
    def test_get_directory_size(self, env_manager):
        """Test directory size calculation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files with known sizes
            file1 = os.path.join(temp_dir, "file1.txt")
            file2 = os.path.join(temp_dir, "subdir", "file2.txt")
            
            os.makedirs(os.path.dirname(file2))
            Path(file1).write_text("a" * 1000)
            Path(file2).write_text("b" * 2000)
            
            size = env_manager._get_directory_size(temp_dir)
            assert size >= 3000  # At least the size of our content
    
    @pytest.mark.asyncio
    async def test_create_isolated_container(self, env_manager):
        """Test Docker container creation"""
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"container123\n", b"")
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process
            
            container_id = await env_manager.create_isolated_container("test_session")
            
            assert container_id == "container123"
            mock_subprocess.assert_called_with(
                "docker", "create", "-it", "--name", "test_test_session", "python:3.9-slim",
                stdout=-1,
                stderr=-1
            )