import os
import re
import json
import requests
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

gemini_api_key = os.environ.get("GEMINI_API_KEY")
gemini_api_url = os.environ.get("GEMINI_API_URL")

@dataclass
class AnalyzedFunction:
    name: str
    description: str
    implementation: str
    files_involved: List[int]
    function_type: str
    files_flow: str

class FunctionAnalyzer:
    def __init__(self, api_key: str = GEMINI_API_KEY):
        self.api_key = api_key
        self.base_url = GEMINI_API_URL
    
    def analyze_project_functions(self, files: List[Dict], technologies: List[str]) -> List[AnalyzedFunction]:
        """Analyze project files using multi-step prompting for maximum accuracy"""
        
        # Step 1: Read and prepare file contents
        file_contents = self._prepare_file_contents(files)
        
        # Step 2: Initial function identification
        print("🔍 Step 1: Identifying core functions...")
        core_functions = self._identify_core_functions(file_contents, technologies)
        
        # Step 3: Detailed analysis for each function
        print("🔍 Step 2: Analyzing function details...")
        detailed_functions = []
        
        for func_basic in core_functions:
            detailed_func = self._analyze_function_details(
                func_basic, file_contents, technologies
            )
            if detailed_func:
                detailed_functions.append(detailed_func)
        
        # Step 4: Generate file flows
        print("🔍 Step 3: Mapping file interactions...")
        final_functions = []
        
        for func in detailed_functions:
            flow_func = self._generate_file_flow(func, file_contents)
            final_functions.append(flow_func)
        
        return final_functions
    
    def _prepare_file_contents(self, files: List[Dict]) -> List[Dict]:
        """Read and prepare file contents for analysis"""
        file_contents = []
        
        for file in files:
            if file["extension"] in ['.js', '.py', '.ts', '.jsx', '.tsx', '.json', '.css', '.html', '.md']:
                content = self._read_file_content(file["path"])
                if content:
                    file_contents.append({
                        "index": file["index"],
                        "path": file["relative_path"],
                        "extension": file["extension"],
                        "content": content,
                        "summary": self._generate_file_summary(content, file["relative_path"])
                    })
        
        return file_contents
    
    def _generate_file_summary(self, content: str, file_path: str) -> str:
        """Generate a brief summary of what the file does"""
        # Extract key information based on file type
        if file_path.endswith('.js'):
            # Look for functions, event listeners, API calls
            functions = re.findall(r'function\s+(\w+)', content)
            event_listeners = re.findall(r'addEventListener\s*\(\s*[\'"](\w+)', content)
            api_calls = re.findall(r'fetch\s*\(|axios\.|post\(|get\(', content)
            
            summary_parts = []
            if functions:
                summary_parts.append(f"Functions: {', '.join(functions[:3])}")
            if event_listeners:
                summary_parts.append(f"Events: {', '.join(event_listeners[:3])}")
            if api_calls:
                summary_parts.append("Contains API calls")
            
            return "; ".join(summary_parts) if summary_parts else "JavaScript file"
        
        elif file_path.endswith('.json'):
            try:
                data = json.loads(content)
                if 'manifest_version' in data:
                    return "Browser extension manifest"
                elif 'dependencies' in data:
                    return "Package configuration"
                else:
                    return "Configuration file"
            except:
                return "JSON data file"
        
        elif file_path.endswith('.css'):
            selectors = re.findall(r'\.(\w+)\s*{', content)
            return f"Styles for: {', '.join(selectors[:5])}" if selectors else "CSS styles"
        
        elif file_path.endswith('.md'):
            return "Documentation file"
        
        return "Project file"
    
    def _identify_core_functions(self, file_contents: List[Dict], technologies: List[str]) -> List[Dict]:
        """Step 1: Identify core functions using AI"""
        
        # Prepare file summaries
        files_summary = []
        for file_info in file_contents:
            files_summary.append(f"File {file_info['index']}: {file_info['path']} - {file_info['summary']}")
        
        files_text = '\n'.join(files_summary)
        
        prompt = f"""
You are analyzing a {', '.join(technologies)} project to identify its core functional capabilities.

Project Files Summary:
{files_text}

Based on the file types and names, identify 3-6 major functional capabilities this project provides.

For each function, provide:
1. A clear, descriptive name in UPPERCASE (like "CONTENT CAPTURE", "USER AUTHENTICATION", "DATA PROCESSING")
2. A brief description of what the functionality does for users
3. The file indices that are likely involved in this functionality

EXAMPLES of good function identification:
- "FACEBOOK POSTING" - Posts captured content to Facebook through API integration
- "CONTENT CAPTURE" - Captures webpage elements and user selections
- "BROWSER EXTENSION LIFECYCLE" - Manages extension initialization and permissions

Return a JSON array:
[
    {{
        "name": "CONTENT CAPTURE",
        "description": "Captures webpage content including text, images, and metadata for social media posting",
        "likely_files": [3, 5]
    }},
    {{
        "name": "FACEBOOK INTEGRATION", 
        "description": "Handles authentication and posting captured content to Facebook through their API",
        "likely_files": [7]
    }}
]

Return ONLY the JSON array, no other text.
"""
        
        try:
            response = self._call_gemini_api(prompt)
            json_data = self._extract_json_from_text(response)
            
            if json_data:
                return json.loads(json_data)
        
        except Exception as e:
            print(f"❌ Error in function identification: {e}")
        
        return []
    
    def _analyze_function_details(self, func_basic: Dict, file_contents: List[Dict], technologies: List[str]) -> AnalyzedFunction:
        """Step 2: Analyze detailed implementation for each function"""
        
        # Get detailed content for relevant files
        relevant_files = []
        for file_info in file_contents:
            if file_info['index'] in func_basic['likely_files']:
                relevant_files.append(file_info)
        
        # Prepare detailed file content
        detailed_content = []
        for file_info in relevant_files:
            detailed_content.append(f"""
File {file_info['index']}: {file_info['path']}
Extension: {file_info['extension']}
Summary: {file_info['summary']}
Content:
{file_info['content'][:2000]}
---END OF FILE---
""")
        
        files_detail = '\n'.join(detailed_content)
        
        # Show example format
        example_format = """
EXAMPLE FORMAT:
Function Name: TASK CREATION
Description: Allows users to create new tasks with title, description, priority, and due date
Files Involved: [1, 8, 17, 19]
Implementation:
File 8: Renders File 17 TaskForm component, handles form submission by calling File 1 API, redirects to File 4 dashboard on successful creation
File 17: Reusable form component with client-side validation using File 22 types for Task interface, File 14 Input components for form inputs, File 13 Button for submit action, sends POST request to File 1, displays loading states and error messages
File 1: POST endpoint that validates task data using File 22 Task interface and File 21 validation helpers, saves to database using File 19 createTask(), returns created task with success/error status using File 21 response utilities
File 19: Contains createTask() that inserts new task record into PostgreSQL database using Prisma ORM from File 23 package.json, with user association and proper indexing
"""
        
        prompt = f"""
Analyze the function "{func_basic['name']}" in detail using the provided file contents.

{example_format}

Function to analyze: {func_basic['name']}
Description: {func_basic['description']}

Relevant Files:
{files_detail}

Create a detailed implementation analysis following the EXACT format shown in the example above.

For each file involved:
1. Explain SPECIFICALLY what that file does for this function
2. Mention specific components, functions, or methods used
3. Reference other files it interacts with (by file number)
4. Be technical but concise - one clear sentence per file

Return a JSON object:
{{
    "name": "{func_basic['name']}",
    "description": "Enhanced description based on code analysis",
    "files_involved": [list of file indices],
    "implementation": {{
        "file_X": "Specific description of what file X does...",
        "file_Y": "Specific description of what file Y does..."
    }}
}}

Return ONLY the JSON object, no other text.
"""
        
        try:
            response = self._call_gemini_api(prompt, timeout=60)
            json_data = self._extract_json_from_text(response)
            
            if json_data:
                data = json.loads(json_data)
                
                # Format implementation text
                impl_parts = []
                for file_key, description in data['implementation'].items():
                    file_num = file_key.replace('file_', '').replace('File ', '')
                    impl_parts.append(f"File {file_num}: {description}")
                
                return AnalyzedFunction(
                    name=data['name'],
                    description=data['description'],
                    implementation='\n'.join(impl_parts),
                    files_involved=data['files_involved'],
                    function_type="core",
                    files_flow=""  # Will be filled in next step
                )
        
        except Exception as e:
            print(f"❌ Error analyzing {func_basic['name']}: {e}")
        
        return None
    
    def _generate_file_flow(self, func: AnalyzedFunction, file_contents: List[Dict]) -> AnalyzedFunction:
        """Step 3: Generate file interaction flow"""
        
        # Get file paths for context
        file_paths = {}
        for file_info in file_contents:
            if file_info['index'] in func.files_involved:
                file_paths[file_info['index']] = file_info['path']
        
        prompt = f"""
Based on this function analysis, determine the logical flow of file interactions.

Function: {func.name}
Files involved: {func.files_involved}
File paths: {file_paths}

Implementation details:
{func.implementation}

Create a logical flow showing how files interact with each other using arrows (->).

EXAMPLES:
- For user-initiated action: 8 -> 17 -> 1 -> 19 -> 4
- For data flow: 4 -> 1 -> 19 -> 16
- For authentication: 9 -> 3 -> 20 -> 10 -> 18 -> 4

Consider:
1. What file initiates the process (UI components, entry points)
2. What files handle the logic (APIs, processing)
3. What files store/retrieve data (database, storage)
4. What files display results (UI, responses)

Return only the flow sequence as: X -> Y -> Z -> W
"""
        
        try:
            response = self._call_gemini_api(prompt)
            flow = response.strip()
            
            # Clean up the flow
            flow = re.sub(r'[^\d\s\-\>]', '', flow)
            flow = re.sub(r'\s+', ' ', flow).strip()
            
            func.files_flow = flow
            
        except Exception as e:
            print(f"❌ Error generating flow for {func.name}: {e}")
            # Fallback: simple sequential flow
            func.files_flow = " -> ".join(map(str, sorted(func.files_involved)))
        
        return func
    
    def _call_gemini_api(self, prompt: str, timeout: int = 30) -> str:
        """Call Gemini API with error handling"""
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
            timeout=timeout
        )
        response.raise_for_status()
        
        result = response.json()
        return result['candidates'][0]['content']['parts'][0]['text']
    
    def _read_file_content(self, file_path: str) -> str:
        """Read complete file content"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                # Limit content size to avoid API limits
                if len(content) > 4000:
                    return content[:2000] + "\n... (content truncated) ..." + content[-2000:]
                return content
        except Exception:
            return ""
    
    def _extract_json_from_text(self, text: str) -> str:
        """Extract JSON from AI response"""
        text = text.strip()
        
        # Try to find JSON object or array
        patterns = [
            r'\{[\s\S]*\}',  # JSON object
            r'\[[\s\S]*\]',  # JSON array
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    json.loads(match)
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

# Test the analyzer
if __name__ == '__main__':
    analyzer = FunctionAnalyzer()
    
    # Example usage
    test_files = [
        {"index": 3, "relative_path": "background.js", "path": "./background.js", "extension": ".js"},
        {"index": 5, "relative_path": "content_script.js", "path": "./content_script.js", "extension": ".js"},
        {"index": 7, "relative_path": "post_to_facebook.js", "path": "./post_to_facebook.js", "extension": ".js"}
    ]
    
    functions = analyzer.analyze_project_functions(test_files, ["Browser-Extension", "JavaScript"])
    
    for func in functions:
        print(f"Function: {func.name}")
        print(f"Description: {func.description}")
        print(f"Files Flow: {func.files_flow}")
        print(f"Implementation:\n{func.implementation}")
        print("-" * 80)