# project_chat.py
import os
import json
import requests
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

# Import existing modules
from project_scanner import ProjectScanner
from TaskFlowTextManager import TaskFlowTextManager
from function_analyzer import FunctionAnalyzer

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

gemini_api_key = os.environ.get("GEMINI_API_KEY")
gemini_api_url = os.environ.get("GEMINI_API_URL")

class ChangeType(Enum):
    CREATE = "create"
    EDIT = "edit"
    DELETE = "delete"

@dataclass
class FileChange:
    type: ChangeType
    file_path: str
    content: Optional[str] = None
    original_content: Optional[str] = None
    description: str = ""

@dataclass
class ConversationContext:
    user_request: str
    requested_functions: List[str] = None
    function_details: Dict[str, Any] = None
    proposed_changes: List[FileChange] = None
    conversation_history: List[Dict] = None

    def __post_init__(self):
        if self.requested_functions is None:
            self.requested_functions = []
        if self.function_details is None:
            self.function_details = {}
        if self.proposed_changes is None:
            self.proposed_changes = []
        if self.conversation_history is None:
            self.conversation_history = []

class ProjectChatManager:
    def __init__(self, project_root: str = ".", project_file: str = "project-file.txt"):
        self.project_root = Path(project_root).resolve()
        self.project_file = project_file
        self.project_manager = None
        self.conversation_context = None
        self.api_key = GEMINI_API_KEY
        self.base_url = GEMINI_API_URL
        
    def initialize_project(self):
        """Initialize or load project"""
        if not Path(self.project_file).exists():
            print("🚀 Project file not found. Creating new project analysis...")
            self._create_project_file()
        
        # Load project data
        self.project_manager = TaskFlowTextManager(self.project_file)
        self.project_manager.load_project()
        
        print(f"✅ Project loaded: {self.project_manager.project_name}")
        print(f"📁 Files: {len(self.project_manager.files)}")
        print(f"🔧 Functions: {len(self.project_manager.functions)}")
        
    def _create_project_file(self):
        """Create project-file.txt using existing scanner"""
        print("🔍 Scanning project structure...")
        scanner = ProjectScanner(str(self.project_root))
        project_info, files, functions = scanner.scan_project()
        
        from project_scanner import ProjectFileGenerator
        generator = ProjectFileGenerator(self.project_file)
        generator.generate(project_info, files, functions)
        
    def start_chat(self):
        """Start the interactive chat session"""
        print("\n" + "="*60)
        print("🤖 Project Chat Assistant")
        print("="*60)
        print("Ask me to make changes to your project!")
        print("Commands: /help, /functions, /files, /quit")
        print("-"*60)
        
        while True:
            try:
                user_input = input("\n💬 You: ").strip()
                
                if not user_input:
                    continue
                    
                # Handle commands
                if user_input.startswith('/'):
                    if not self._handle_command(user_input):
                        break
                    continue
                
                # Process user request
                self._process_user_request(user_input)
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                
    def _handle_command(self, command: str) -> bool:
        """Handle special commands"""
        cmd = command.lower()
        
        if cmd == '/quit' or cmd == '/exit':
            return False
        elif cmd == '/help':
            self._show_help()
        elif cmd == '/functions':
            self._list_functions()
        elif cmd == '/files':
            self._list_files()
        elif cmd == '/status':
            self._show_status()
        else:
            print(f"Unknown command: {command}")
            
        return True
        
    def _show_help(self):
        """Show help information"""
        print("""
📚 Available Commands:
  /help       - Show this help
  /functions  - List all project functions
  /files      - List all project files
  /status     - Show current conversation status
  /quit       - Exit the chat

💡 Example requests:
  "Add error handling to the login function"
  "Create a new function to validate user input"
  "Update the database connection to use environment variables"
  "Add logging to all API calls"
        """)
        
    def _list_functions(self):
        """List all functions"""
        print("\n🔧 Project Functions:")
        for func_id, func in self.project_manager.functions.items():
            files_str = ", ".join([f"File {idx}" for idx in func.files_involved])
            print(f"  {func_id}. {func.name}")
            print(f"    Files: {files_str}")
            print(f"    {func.description[:80]}...")
            
    def _list_files(self):
        """List all files"""
        print("\n📁 Project Files:")
        for idx, file_obj in self.project_manager.files.items():
            print(f"  {idx}. {file_obj.path}")
            
    def _show_status(self):
        """Show current conversation status"""
        if not self.conversation_context:
            print("No active conversation")
            return
            
        ctx = self.conversation_context
        print(f"\n📊 Conversation Status:")
        print(f"Request: {ctx.user_request}")
        print(f"Functions requested: {len(ctx.requested_functions)}")
        print(f"Function details loaded: {len(ctx.function_details)}")
        print(f"Proposed changes: {len(ctx.proposed_changes)}")
        
    def _process_user_request(self, user_request: str):
        """Process user request through AI conversation"""
        self.conversation_context = ConversationContext(user_request=user_request)
        
        # Start AI conversation
        self._ai_conversation_loop()
        
    def _ai_conversation_loop(self):
        """Handle AI conversation with context management"""
        ctx = self.conversation_context
        max_iterations = 10
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Prepare context for AI
            ai_context = self._prepare_ai_context()
            
            # Get AI response
            ai_response = self._call_ai(ai_context)
            
            if not ai_response:
                print("❌ Failed to get AI response")
                break
                
            # Parse AI response
            action = self._parse_ai_response(ai_response)
            
            if action == "request_function_details":
                # AI wants function details
                continue
            elif action == "propose_changes":
                # AI proposed file changes
                self._handle_proposed_changes()
                break
            elif action == "complete":
                # AI completed the task
                print("✅ Task completed!")
                break
            elif action == "clarification_needed":
                # AI needs clarification
                continue
            else:
                print("🤔 Unexpected AI response")
                break
                
    def _prepare_ai_context(self) -> str:
        """Prepare context for AI conversation"""
        ctx = self.conversation_context
        
        # Basic project info
        project_info = f"""
PROJECT: {self.project_manager.project_name}
DESCRIPTION: {self.project_manager.project_description}
TECHNOLOGY: {self.project_manager.technology}

AVAILABLE FUNCTIONS:
"""
        
        # Add function list
        for func_id, func in self.project_manager.functions.items():
            files_str = ", ".join([f"File {idx}" for idx in func.files_involved])
            project_info += f"{func_id}. {func.name} (Files: {files_str})\n"
            
        # Add file list
        project_info += "\nAVAILABLE FILES:\n"
        for idx, file_obj in self.project_manager.files.items():
            project_info += f"{idx}. {file_obj.path}\n"
            
        # Add conversation history
        history = ""
        for msg in ctx.conversation_history:
            history += f"{msg['role']}: {msg['content']}\n"
            
        # Add function details if loaded
        function_details = ""
        if ctx.function_details:
            function_details = "\nFUNCTION DETAILS:\n"
            for func_id, details in ctx.function_details.items():
                function_details += f"\n{func_id}:\n{details}\n"
                
        prompt = f"""
You are a project assistant helping to implement changes to a codebase.

{project_info}

{history}

CURRENT USER REQUEST: {ctx.user_request}

{function_details}

Your task is to help implement the requested changes. You can:

1. REQUEST_FUNCTION_DETAILS: Ask for specific function details by providing function IDs
   Format: REQUEST_FUNCTION_DETAILS: [func_id1, func_id2]

2. PROPOSE_CHANGES: Propose specific file changes
   Format: PROPOSE_CHANGES: {{
     "changes": [
       {{
         "type": "edit|create|delete",
         "file_path": "path/to/file",
         "content": "new file content",
         "description": "what this change does"
       }}
     ],
     "explanation": "overall explanation of changes"
   }}

3. CLARIFICATION_NEEDED: Ask user for more details
   Format: CLARIFICATION_NEEDED: Your question here

4. COMPLETE: Task is done
   Format: COMPLETE: Summary of what was accomplished

Respond with exactly one of the above formats.
"""
        
        return prompt
        
    def _call_ai(self, prompt: str) -> str:
        """Call Gemini AI API"""
        try:
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }
            
            headers = {"Content-Type": "application/json"}
            
            response = requests.post(
                f"{self.base_url}?key={self.api_key}",
                json=payload,
                headers=headers,
                timeout=60
            )
            
            response.raise_for_status()
            result = response.json()
            return result['candidates'][0]['content']['parts'][0]['text']
            
        except Exception as e:
            print(f"❌ AI API Error: {e}")
            return None
            
    def _parse_ai_response(self, response: str) -> str:
        """Parse AI response and take appropriate action"""
        response = response.strip()
        ctx = self.conversation_context
        
        # Add to conversation history
        ctx.conversation_history.append({
            "role": "assistant",
            "content": response
        })
        
        if response.startswith("REQUEST_FUNCTION_DETAILS:"):
            # Extract function IDs
            func_ids_str = response.replace("REQUEST_FUNCTION_DETAILS:", "").strip()
            try:
                # Parse function IDs
                func_ids = [fid.strip() for fid in func_ids_str.replace("[", "").replace("]", "").split(",")]
                func_ids = [fid.strip("'\"") for fid in func_ids if fid.strip()]
                
                print(f"🔍 AI requesting details for functions: {', '.join(func_ids)}")
                
                # Load function details
                for func_id in func_ids:
                    if func_id in self.project_manager.functions:
                        func = self.project_manager.functions[func_id]
                        ctx.function_details[func_id] = self._format_function_details(func)
                        ctx.requested_functions.append(func_id)
                    else:
                        print(f"⚠️ Function {func_id} not found")
                        
                return "request_function_details"
                
            except Exception as e:
                print(f"❌ Error parsing function IDs: {e}")
                
        elif response.startswith("PROPOSE_CHANGES:"):
            # Extract and parse changes
            changes_str = response.replace("PROPOSE_CHANGES:", "").strip()
            try:
                changes_data = self._extract_json_from_text(changes_str)
                if changes_data:
                    changes_obj = json.loads(changes_data)
                    ctx.proposed_changes = self._parse_proposed_changes(changes_obj)
                    print(f"📝 AI proposed {len(ctx.proposed_changes)} file changes")
                    return "propose_changes"
                    
            except Exception as e:
                print(f"❌ Error parsing proposed changes: {e}")
                
        elif response.startswith("CLARIFICATION_NEEDED:"):
            question = response.replace("CLARIFICATION_NEEDED:", "").strip()
            print(f"🤖 AI: {question}")
            user_answer = input("💬 You: ")
            
            ctx.conversation_history.append({
                "role": "user", 
                "content": user_answer
            })
            
            return "clarification_needed"
            
        elif response.startswith("COMPLETE:"):
            summary = response.replace("COMPLETE:", "").strip()
            print(f"✅ AI: {summary}")
            return "complete"
            
        # If no recognized format, treat as clarification
        print(f"🤖 AI: {response}")
        return "clarification_needed"
        
    def _format_function_details(self, func) -> str:
        """Format function details for AI"""
        files_info = []
        for file_idx in func.files_involved:
            if file_idx in self.project_manager.files:
                file_obj = self.project_manager.files[file_idx]
                # Try to read file content
                try:
                    with open(file_obj.path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if len(content) > 2000:
                            content = content[:1000] + "\n... (truncated) ...\n" + content[-1000:]
                        files_info.append(f"File {file_idx} ({file_obj.path}):\n{content}")
                except:
                    files_info.append(f"File {file_idx} ({file_obj.path}): [Could not read file]")
                    
        return f"""
FUNCTION: {func.name}
DESCRIPTION: {func.description}
FILES INVOLVED: {', '.join([f'File {idx}' for idx in func.files_involved])}

IMPLEMENTATION:
{func.implementation}

FILE CONTENTS:
{chr(10).join(files_info)}
"""
        
    def _parse_proposed_changes(self, changes_obj: Dict) -> List[FileChange]:
        """Parse proposed changes from AI response"""
        changes = []
        
        for change_data in changes_obj.get("changes", []):
            change_type = ChangeType(change_data["type"])
            file_path = change_data["file_path"]
            content = change_data.get("content")
            description = change_data.get("description", "")
            
            # Read original content if file exists
            original_content = None
            if Path(file_path).exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        original_content = f.read()
                except:
                    pass
                    
            changes.append(FileChange(
                type=change_type,
                file_path=file_path,
                content=content,
                original_content=original_content,
                description=description
            ))
            
        return changes
        
    def _handle_proposed_changes(self):
        """Handle AI proposed changes"""
        ctx = self.conversation_context
        
        if not ctx.proposed_changes:
            print("No changes proposed")
            return
            
        print("\n" + "="*60)
        print("📝 PROPOSED CHANGES")
        print("="*60)
        
        for i, change in enumerate(ctx.proposed_changes, 1):
            print(f"\n{i}. {change.type.value.upper()}: {change.file_path}")
            print(f"   Description: {change.description}")
            
            if change.type == ChangeType.DELETE:
                print("   ❌ File will be deleted")
            elif change.type == ChangeType.CREATE:
                print("   ✨ New file will be created")
                if change.content:
                    print(f"   Content preview: {change.content[:200]}...")
            elif change.type == ChangeType.EDIT:
                print("   ✏️ File will be modified")
                if change.content:
                    print(f"   New content preview: {change.content[:200]}...")
                    
        print("\n" + "-"*60)
        
        # Ask for confirmation
        while True:
            choice = input("Accept changes? (y)es/(n)o/(d)etails: ").lower().strip()
            
            if choice in ['y', 'yes']:
                self._apply_changes(ctx.proposed_changes)
                break
            elif choice in ['n', 'no']:
                print("❌ Changes rejected")
                break
            elif choice in ['d', 'details']:
                self._show_change_details(ctx.proposed_changes)
            else:
                print("Please enter 'y', 'n', or 'd'")
                
    def _show_change_details(self, changes: List[FileChange]):
        """Show detailed view of changes"""
        for i, change in enumerate(changes, 1):
            print(f"\n{'='*20} CHANGE {i} {'='*20}")
            print(f"Type: {change.type.value.upper()}")
            print(f"File: {change.file_path}")
            print(f"Description: {change.description}")
            
            if change.type == ChangeType.DELETE:
                print("\n--- FILE TO BE DELETED ---")
                if change.original_content:
                    print(change.original_content[:500] + "..." if len(change.original_content) > 500 else change.original_content)
                    
            elif change.type == ChangeType.CREATE:
                print("\n--- NEW FILE CONTENT ---")
                if change.content:
                    print(change.content)
                    
            elif change.type == ChangeType.EDIT:
                print("\n--- ORIGINAL CONTENT ---")
                if change.original_content:
                    print(change.original_content[:500] + "..." if len(change.original_content) > 500 else change.original_content)
                print("\n--- NEW CONTENT ---")
                if change.content:
                    print(change.content)
                    
            input("\nPress Enter to continue...")
            
    def _apply_changes(self, changes: List[FileChange]):
        """Apply the proposed changes"""
        print("\n🔄 Applying changes...")
        
        for change in changes:
            try:
                if change.type == ChangeType.DELETE:
                    if Path(change.file_path).exists():
                        Path(change.file_path).unlink()
                        print(f"❌ Deleted: {change.file_path}")
                    else:
                        print(f"⚠️ File not found: {change.file_path}")
                        
                elif change.type == ChangeType.CREATE:
                    # Create directory if needed
                    Path(change.file_path).parent.mkdir(parents=True, exist_ok=True)
                    with open(change.file_path, 'w', encoding='utf-8') as f:
                        f.write(change.content or "")
                    print(f"✨ Created: {change.file_path}")
                    
                elif change.type == ChangeType.EDIT:
                    with open(change.file_path, 'w', encoding='utf-8') as f:
                        f.write(change.content or "")
                    print(f"✏️ Modified: {change.file_path}")
                    
            except Exception as e:
                print(f"❌ Error applying change to {change.file_path}: {e}")
                
        print("✅ Changes applied successfully!")
        
        # Refresh project file if needed
        if any("project-file.txt" in change.file_path for change in changes):
            print("🔄 Refreshing project data...")
            self.project_manager.load_project()
            
    def _extract_json_from_text(self, text: str) -> str:
        """Extract JSON from text response"""
        import re
        
        # Try to find JSON object
        patterns = [
            r'\{[\s\S]*\}',  # JSON object
            r'\[[\s\S]*\]',  # JSON array
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    json.loads(match)  # Validate JSON
                    return match
                except:
                    continue
                    
        # Try extracting between code blocks
        code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if code_block_match:
            try:
                json.loads(code_block_match.group(1))
                return code_block_match.group(1)
            except:
                pass
                
        return None

def main():
    """Main CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Project Chat Assistant')
    parser.add_argument('--project-root', '-p', default='.', 
                       help='Project root directory (default: current directory)')
    parser.add_argument('--project-file', '-f', default='project-file.txt',
                       help='Project file path (default: project-file.txt)')
    
    args = parser.parse_args()
    
    try:
        # Initialize chat manager
        chat_manager = ProjectChatManager(
            project_root=args.project_root,
            project_file=args.project_file
        )
        
        # Initialize project
        chat_manager.initialize_project()
        
        # Start chat
        chat_manager.start_chat()
        
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()