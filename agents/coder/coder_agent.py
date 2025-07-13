from collections.abc import AsyncGenerator
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import re
from datetime import datetime

# Add the project root to the Python path so we can import from the agents module
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from acp_sdk import Message
from acp_sdk.models import MessagePart
from beeai_framework.agents.react import ReActAgent
from beeai_framework.backend.chat import ChatModel
from beeai_framework.memory import TokenMemory
from beeai_framework.utils.dicts import exclude_none

from agents.agent_configs import coder_config
from workflows.workflow_config import GENERATED_CODE_PATH

# Load environment variables from .env file
load_dotenv()


async def coder_agent(input: list[Message]) -> AsyncGenerator:
    """Agent responsible for writing code implementations and creating project files"""
    llm = ChatModel.from_name(coder_config["model"])
    
    # Extract input text
    input_text = ""
    for message in input:
        for part in message.parts:
            input_text += part.content + "\n"
    
    # Debug: Print input length and first few characters
    print(f"📊 Input length: {len(input_text)} characters")
    if "SESSION_ID" in input_text:
        print("✅ SESSION_ID found in input text")
    else:
        print("❌ SESSION_ID NOT found in input text")
    
    # Check if a SESSION_ID or PROJECT_DIR was provided in the input
    session_id = None
    project_dir = None
    
    # Extract SESSION_ID if present
    session_match = re.search(r'SESSION_ID:\s*(\S+)', input_text)
    if session_match:
        session_id = session_match.group(1)
        print(f"📋 Using session ID: {session_id}")
    else:
        print(f"⚠️  No SESSION_ID found in input (searched for 'SESSION_ID:')")
        # Debug: print first 200 chars of input
        print(f"🔍 Input preview: {input_text[:200]}...")
    
    # Extract PROJECT_DIR if present
    dir_match = re.search(r'PROJECT_DIR:\s*(.+?)(?:\n|$)', input_text)
    if dir_match:
        project_dir = dir_match.group(1).strip()
        print(f"📁 Using project directory: {project_dir}")
    
    agent = ReActAgent(
        llm=llm, 
        tools=[], 
        templates={
            "system": lambda template: template.update(
                defaults=exclude_none({
                    "instructions": """
                    You are a senior software developer. Your role is to:
                    1. Write clean, efficient, and well-documented code
                    2. Create complete project structures with all necessary files
                    3. Follow best practices and coding standards
                    4. Include proper error handling and edge case management
                    5. Write unit tests and integration tests
                    6. Optimize for performance and maintainability
                    
                    IMPORTANT: Always create working code implementations and write them to files.
                    Never ask for more details - work with what you have and make reasonable assumptions.
                    Extract requirements from the plan, design, and tests provided to create complete implementations.
                    
                    CRITICAL VERSION REQUIREMENTS:
                    When creating Python Flask applications:
                    - Use Flask>=3.0.0 for compatibility with modern dependencies
                    - NEVER use Flask 2.0.x which has compatibility issues with Werkzeug 3.x
                    - Example: Flask==3.0.3 or Flask>=3.0.0
                    
                    FLASK APPLICATION REQUIREMENTS:
                    1. All SQLAlchemy models MUST include a to_dict() method for serialization:
                       def to_dict(self):
                           return {
                               'id': self.id,
                               'field1': self.field1,
                               # ... all fields
                           }
                    
                    2. If using Marshmallow schemas, they MUST be integrated in routes correctly:
                       - Use schema.load() for input validation
                       - Use jsonify(schema.dump(object)) for output serialization (NOT schema.jsonify)
                       - Handle validation errors properly
                       - Example:
                         return jsonify(todo_schema.dump(todo)), 200
                    
                    3. Error handlers MUST be registered with the Flask app:
                       app.register_error_handler(404, not_found_error)
                       app.register_error_handler(400, bad_request_error)
                    
                    4. Always include a health check endpoint in app.py:
                       @app.route('/health')
                       def health():
                           return jsonify({'status': 'healthy'}), 200
                    
                    5. Ensure all imports are used and all defined components are integrated
                    
                    CRITICAL: You MUST respond with actual code files in this EXACT format:
                    
                    FILENAME: package.json
                    ```json
                    {
                      "name": "my-project",
                      "version": "1.0.0"
                    }
                    ```
                    
                    FILENAME: src/app.js
                    ```javascript
                    const express = require('express');
                    const app = express();
                    // Complete working code here
                    ```
                    
                    FILENAME: README.md
                    ```markdown
                    # Project Name
                    Setup instructions here
                    ```
                    
                    DO NOT write explanatory text without code files. Every response must include multiple FILENAME: entries with actual code.
                    Always include AT MINIMUM:
                    - Main application file
                    - Package/dependency file (package.json, requirements.txt, etc.)
                    - README.md with setup instructions
                    - At least one test file
                    - Configuration files as needed
                    
                    Create a complete, working project that can be immediately used.
                    """,
                    "role": "system",
                })
            )
        },
        memory=TokenMemory(llm)
    )
    
    response = await agent.run(prompt="Implement the following requirements and create all necessary project files: " + str(input))
    
    # Parse the response to extract files and create project structure
    response_text = response.result.text
    
    try:
        # Extract project name from the response or use default
        project_name = "app"
        if "todo" in response_text.lower():
            project_name = "todo_api"
        elif "blog" in response_text.lower():
            project_name = "blog_api"
        elif "chat" in response_text.lower():
            project_name = "chat_app"
        elif "auth" in response_text.lower():
            project_name = "auth_system"
        elif "registration" in response_text.lower():
            project_name = "user_registration"
        elif "ecommerce" in response_text.lower() or "shop" in response_text.lower():
            project_name = "ecommerce_app"
        elif "social" in response_text.lower():
            project_name = "social_app"
        
        # Check if we should reuse an existing directory
        if project_dir:
            # Use the provided project directory
            project_root = project_dir
            project_folder_name = os.path.basename(project_root)
            print(f"📂 Reusing existing project directory: {project_root}")
        elif session_id:
            # Use session ID to create/find directory
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_base = os.path.abspath(os.path.join(script_dir, "..", ".."))
            generated_dir = os.path.abspath(os.path.join(project_base, GENERATED_CODE_PATH))
            
            # Create directory name based on session ID
            project_folder_name = f"{project_name}_session_{session_id}"
            project_root = os.path.join(generated_dir, project_folder_name)
            print(f"📂 Using session-based directory: {project_root}")
        else:
            # Create new directory with timestamp (original behavior)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Determine project root directory using the centralized configuration
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_base = os.path.abspath(os.path.join(script_dir, "..", ".."))
            
            # Use the centralized GENERATED_CODE_PATH configuration
            generated_dir = os.path.abspath(os.path.join(project_base, GENERATED_CODE_PATH))
            print(f"🔄 Using generated code path: {generated_dir}")  # Debug log
            
            project_folder_name = f"{project_name}_generated_{timestamp}"
            project_root = os.path.join(generated_dir, project_folder_name)
            print(f"📁 Creating new project directory: {project_root}")
        
        # Create the directory if it doesn't exist
        os.makedirs(project_root, exist_ok=True)
        
        # Parse files from the response
        
        # Try multiple patterns to catch different formats
        file_patterns = [
            r'FILENAME:\s*(.+?)\n```(\w*)\n([\s\S]+?)\n```',  # Standard format
            r'FILENAME:\s*(.+?)\n```(\w+)?\s*([\s\S]+?)\s*```',  # With optional language
            r'### (.+?)\n```(\w+)\n([\s\S]+?)\n```',  # Markdown header format
            r'`(.+?)`\n```(\w+)\n([\s\S]+?)\n```',  # Backtick filename
            r'File:\s*(.+?)\n```(\w*)\n([\s\S]+?)\n```',  # Alternative "File:" format
        ]
        
        files_found = []
        for pattern in file_patterns:
            matches = re.findall(pattern, response_text, re.MULTILINE)
            if matches:
                files_found.extend(matches)
                break  # Use first pattern that finds matches
        
        created_files = []
        
        # Debug output
        print(f"🔍 Searching for files in response...")
        print(f"📝 Response length: {len(response_text)} characters")
        print(f"🎯 Files found: {len(files_found)}")
        
        if files_found:
            for filename, language, code_content in files_found:
                filename = filename.strip()
                code_content = code_content.strip()
                
                print(f"📄 Processing file: {filename}")
                
                # Create full file path
                file_path = os.path.join(project_root, filename)
                
                # Create directory structure if needed
                file_dir = os.path.dirname(file_path)
                if file_dir and file_dir != project_root:
                    os.makedirs(file_dir, exist_ok=True)
                    print(f"📁 Created directory: {file_dir}")
                
                # Write the file
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(code_content)
                    created_files.append(file_path)
                    print(f"✅ Created: {filename}")
                except Exception as file_error:
                    print(f"❌ Error writing file {file_path}: {file_error}")
            
            # Generate a summary of created files
            # Include session info if using session-based directory
            session_info = ""
            if session_id:
                session_info = f"🔗 Session ID: {session_id}\n"
            
            files_summary = f"""
✅ PROJECT CREATED: {project_folder_name}
📁 Location: {project_root}
{session_info}📄 Files created: {len(created_files)}
🕐 Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Files:
""" + "\n".join([f"  - {os.path.relpath(f, project_root)}" for f in created_files])
            
            # Add the original response for context
            final_response = f"{files_summary}\n\n--- IMPLEMENTATION DETAILS ---\n{response_text}"
            
        else:
            # Enhanced fallback - try to extract any code blocks and create reasonable filenames
            print("⚠️  No files found in expected format, trying fallback extraction...")
            
            # Look for any code blocks
            code_blocks = re.findall(r'```(\w+)\n([\s\S]+?)\n```', response_text)
            
            if code_blocks:
                print(f"🔄 Found {len(code_blocks)} code blocks, creating files...")
                
                for i, (language, code_content) in enumerate(code_blocks):
                    # Generate reasonable filename based on language and content
                    if language == 'javascript' or language == 'js':
                        if 'express' in code_content.lower() or 'app.listen' in code_content:
                            filename = 'app.js'
                        elif 'test' in code_content.lower() or 'describe' in code_content:
                            filename = 'test.js'
                        else:
                            filename = f'script_{i+1}.js'
                    elif language == 'python' or language == 'py':
                        if 'flask' in code_content.lower() or 'app.run' in code_content:
                            filename = 'app.py'
                        elif 'test' in code_content.lower():
                            filename = 'test.py'
                        else:
                            filename = f'script_{i+1}.py'
                    elif language == 'json':
                        if 'name' in code_content and 'version' in code_content:
                            filename = 'package.json'
                        else:
                            filename = f'config_{i+1}.json'
                    elif language == 'markdown' or language == 'md':
                        filename = 'README.md'
                    elif language == 'yaml' or language == 'yml':
                        filename = 'docker-compose.yml' if 'version' in code_content else f'config_{i+1}.yml'
                    else:
                        filename = f'file_{i+1}.{language}' if language else f'file_{i+1}.txt'
                    
                    # Create the file
                    file_path = os.path.join(project_root, filename)
                    try:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(code_content.strip())
                        created_files.append(file_path)
                        print(f"✅ Created (fallback): {filename}")
                    except Exception as file_error:
                        print(f"❌ Error creating fallback file {filename}: {file_error}")
                
                # Include session info if using session-based directory
                session_info = ""
                if session_id:
                    session_info = f"🔗 Session ID: {session_id}\n"
                
                files_summary = f"""
✅ PROJECT CREATED: {project_folder_name} (via fallback extraction)
📁 Location: {project_root}
{session_info}📄 Files created: {len(created_files)}
🕐 Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Files:
""" + "\n".join([f"  - {os.path.relpath(f, project_root)}" for f in created_files])
                
                final_response = f"{files_summary}\n\n--- IMPLEMENTATION DETAILS ---\n{response_text}"
            
            else:
                # Last resort - create a debug file with the full response
                debug_file = os.path.join(project_root, "debug_response.txt")
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write("DEBUG: Full LLM Response\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(response_text)
                
                final_response = f"""
⚠️  No code files detected in response. Created debug file for analysis.
📁 Location: {project_root}
📄 Debug file: debug_response.txt

💡 The LLM may not be following the expected FILENAME: format.
Check debug_response.txt to see the actual response format.

Expected format:
FILENAME: app.js
```javascript
code here
```
"""
        
        yield MessagePart(content=final_response)
        
    except Exception as e:
        error_msg = f"""
❌ Error creating project files: {str(e)}

Raw implementation response:
{response_text}
"""
        yield MessagePart(content=error_msg)
