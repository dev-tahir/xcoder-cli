import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json

@dataclass
class Function:
    id: str
    name: str
    description: str
    implementation: str
    files_involved: List[str]

@dataclass
class ProjectFile:
    index: int
    path: str
    description: str

class TaskFlowTextManager:
    def __init__(self, text_file_path: str = "paste.txt"):
        self.text_file_path = text_file_path
        self.project_name = ""
        self.project_description = ""
        self.technology = ""
        self.files = {}  # index -> ProjectFile
        self.functions = {}  # function_id -> Function
        self.config_section = ""
        
    def load_project(self):
        """Load project data from text file"""
        try:
            with open(self.text_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self._parse_content(content)
            print(f"Project '{self.project_name}' loaded successfully")
            print(f"Files: {len(self.files)}, Functions: {len(self.functions)}")
            
        except FileNotFoundError:
            print(f"File {self.text_file_path} not found")
        except Exception as e:
            print(f"Error loading project: {e}")
    
    def _parse_content(self, content: str):
        """Parse the text file content"""
        lines = content.split('\n')
        current_section = None
        current_function = None
        temp_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Parse header
            if line.startswith('Project:'):
                self.project_name = line.split(':', 1)[1].strip()
            elif line.startswith('Description:'):
                self.project_description = line.split(':', 1)[1].strip()
            elif line.startswith('technology:'):
                self.technology = line.split(':', 1)[1].strip()
            
            # Parse files section
            elif line == 'PROJECT FILES INDEX:':
                current_section = 'files'
            elif current_section == 'files' and line and not line.startswith('All functions:'):
                if re.match(r'^\d+\.', line):
                    parts = line.split('.', 1)
                    if len(parts) == 2:
                        index = int(parts[0])
                        path = parts[1].strip()
                        self.files[index] = ProjectFile(index, path, "")
            
            # Parse functions section
            elif line == 'All functions:':
                current_section = 'functions'
            elif current_section == 'functions' and re.match(r'^\d+F\.', line):
                # Save previous function if exists
                if current_function:
                    self.functions[current_function['id']] = Function(
                        id=current_function['id'],
                        name=current_function['name'],
                        description=current_function['description'],
                        implementation='\n'.join(current_function['implementation']),
                        files_involved=current_function['files']
                    )
                
                # Start new function
                parts = line.split('.', 1)
                func_id = parts[0].strip()
                func_name = parts[1].strip()
                
                current_function = {
                    'id': func_id,
                    'name': func_name,
                    'description': '',
                    'implementation': [],
                    'files': []
                }
                
            elif current_function and line and not re.match(r'^\d+F\.', line):
                if not current_function['description'] and not line.startswith('Implementation:'):
                    current_function['description'] = line
                elif line.startswith('Implementation:'):
                    pass  # Skip implementation header
                elif line.startswith('File '):
                    # Extract file references
                    file_refs = re.findall(r'File (\d+)', line)
                    current_function['files'].extend([int(ref) for ref in file_refs])
                    current_function['implementation'].append(line)
                else:
                    current_function['implementation'].append(line)
            
            # Parse config section
            elif line.startswith('key projct configuration:'):
                current_section = 'config'
                self.config_section = line + '\n'
            elif current_section == 'config':
                self.config_section += line + '\n'
            
            i += 1
        
        # Save last function
        if current_function:
            self.functions[current_function['id']] = Function(
                id=current_function['id'],
                name=current_function['name'],
                description=current_function['description'],
                implementation='\n'.join(current_function['implementation']),
                files_involved=current_function['files']
            )
    
    def add_function(self, name: str, description: str, implementation: str, files_involved: List[int] = None):
        """Add new function to project"""
        if files_involved is None:
            files_involved = []
        
        # Generate new function ID
        existing_ids = [int(fid.replace('F', '')) for fid in self.functions.keys()]
        new_id = str(max(existing_ids) + 1) + 'F' if existing_ids else '1F'
        
        # Validate file references
        for file_idx in files_involved:
            if file_idx not in self.files:
                print(f"Warning: File {file_idx} not found in project files")
        
        new_function = Function(
            id=new_id,
            name=name,
            description=description,
            implementation=implementation,
            files_involved=files_involved
        )
        
        self.functions[new_id] = new_function
        print(f"Added function {new_id}: {name}")
        return new_id
    
    def edit_function(self, function_id: str, name: str = None, description: str = None, 
                     implementation: str = None, files_involved: List[int] = None):
        """Edit existing function"""
        if function_id not in self.functions:
            print(f"Function {function_id} not found")
            return False
        
        func = self.functions[function_id]
        
        if name:
            func.name = name
        if description:
            func.description = description
        if implementation:
            func.implementation = implementation
        if files_involved is not None:
            # Validate file references
            for file_idx in files_involved:
                if file_idx not in self.files:
                    print(f"Warning: File {file_idx} not found in project files")
            func.files_involved = files_involved
        
        print(f"Updated function {function_id}: {func.name}")
        return True
    
    def delete_function(self, function_id: str):
        """Delete function from project"""
        if function_id not in self.functions:
            print(f"Function {function_id} not found")
            return False
        
        func_name = self.functions[function_id].name
        del self.functions[function_id]
        print(f"Deleted function {function_id}: {func_name}")
        return True
    
    def add_file(self, path: str, description: str = ""):
        """Add new file to project"""
        # Generate new file index
        new_index = max(self.files.keys()) + 1 if self.files else 1
        
        new_file = ProjectFile(new_index, path, description)
        self.files[new_index] = new_file
        
        print(f"Added file {new_index}: {path}")
        return new_index
    
    def edit_file(self, index: int, path: str = None, description: str = None):
        """Edit existing file"""
        if index not in self.files:
            print(f"File {index} not found")
            return False
        
        file_obj = self.files[index]
        
        if path:
            file_obj.path = path
        if description is not None:
            file_obj.description = description
        
        print(f"Updated file {index}: {file_obj.path}")
        return True
    
    def delete_file(self, index: int):
        """Delete file from project and update function references"""
        if index not in self.files:
            print(f"File {index} not found")
            return False
        
        file_path = self.files[index].path
        
        # Remove file references from functions
        for func in self.functions.values():
            if index in func.files_involved:
                func.files_involved.remove(index)
                print(f"Removed file {index} reference from function {func.id}")
        
        del self.files[index]
        print(f"Deleted file {index}: {file_path}")
        return True
    
    def reorder_files(self):
        """Reorder file indices to be sequential"""
        sorted_files = sorted(self.files.items())
        new_files = {}
        index_mapping = {}
        
        for new_idx, (old_idx, file_obj) in enumerate(sorted_files, 1):
            file_obj.index = new_idx
            new_files[new_idx] = file_obj
            index_mapping[old_idx] = new_idx
        
        # Update function file references
        for func in self.functions.values():
            func.files_involved = [index_mapping.get(idx, idx) for idx in func.files_involved]
        
        self.files = new_files
        print("File indices reordered")
    
    def save_project(self):
        """Save project back to text file"""
        try:
            content = self._generate_content()
            
            with open(self.text_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"Project saved to {self.text_file_path}")
            
        except Exception as e:
            print(f"Error saving project: {e}")
    
    def _generate_content(self) -> str:
        """Generate text file content from current data"""
        lines = []
        
        # Header
        lines.append(f"Project:{self.project_name}")
        lines.append(f"Description:{self.project_description}")
        lines.append(f"technology:{self.technology}")
        
        # Files section
        lines.append("PROJECT FILES INDEX:")
        for index in sorted(self.files.keys()):
            file_obj = self.files[index]
            lines.append(f"{index}. {file_obj.path}")
        
        lines.append("")
        
        # Functions section
        lines.append("All functions:")
        for func_id in sorted(self.functions.keys(), key=lambda x: int(x.replace('F', ''))):
            func = self.functions[func_id]
            lines.append(f"{func_id}. {func.name}")
            lines.append(func.description)
            lines.append("Implementation:")
            lines.append(func.implementation)
            lines.append("")
        
        # Config section
        lines.append(self.config_section.strip())
        
        return '\n'.join(lines)
    
    def list_functions(self):
        """List all functions"""
        print("\n=== Functions ===")
        for func_id in sorted(self.functions.keys(), key=lambda x: int(x.replace('F', ''))):
            func = self.functions[func_id]
            files_str = ", ".join([f"File {idx}" for idx in func.files_involved])
            print(f"{func_id}. {func.name}")
            print(f"   Files: {files_str}")
            print(f"   Description: {func.description[:100]}...")
            print()
    
    def list_files(self):
        """List all files"""
        print("\n=== Files ===")
        for index in sorted(self.files.keys()):
            file_obj = self.files[index]
            print(f"{index}. {file_obj.path}")
    
    def search_functions(self, query: str):
        """Search functions by name or description"""
        query_lower = query.lower()
        results = []
        
        for func in self.functions.values():
            if (query_lower in func.name.lower() or 
                query_lower in func.description.lower() or
                query_lower in func.implementation.lower()):
                results.append(func)
        
        print(f"\n=== Search Results for '{query}' ===")
        for func in results:
            print(f"{func.id}. {func.name}")
            print(f"   Description: {func.description[:100]}...")
        
        return results
    
    def get_function_info(self, function_id: str):
        """Get detailed function information"""
        if function_id not in self.functions:
            print(f"Function {function_id} not found")
            return None
        
        func = self.functions[function_id]
        print(f"\n=== Function {function_id} ===")
        print(f"Name: {func.name}")
        print(f"Description: {func.description}")
        print(f"Files involved: {', '.join([f'File {idx}' for idx in func.files_involved])}")
        print(f"Implementation:\n{func.implementation}")
        
        return func
    
    def validate_project(self):
        """Validate project consistency"""
        issues = []
        
        # Check file references in functions
        for func in self.functions.values():
            for file_idx in func.files_involved:
                if file_idx not in self.files:
                    issues.append(f"Function {func.id} references non-existent File {file_idx}")
        
        # Check for duplicate file paths
        paths = [f.path for f in self.files.values()]
        duplicates = [path for path in paths if paths.count(path) > 1]
        if duplicates:
            issues.append(f"Duplicate file paths found: {set(duplicates)}")
        
        if issues:
            print("\n=== Validation Issues ===")
            for issue in issues:
                print(f"- {issue}")
        else:
            print("Project validation passed!")
        
        return len(issues) == 0

# Interactive CLI
def interactive_menu():
    print("\n=== TaskFlow Text Manager ===")
    print("1. Load project")
    print("2. Add function")
    print("3. Edit function")
    print("4. Delete function")
    print("5. Add file")
    print("6. Edit file")
    print("7. Delete file")
    print("8. List functions")
    print("9. List files")
    print("10. Search functions")
    print("11. Function info")
    print("12. Validate project")
    print("13. Reorder files")
    print("14. Save project")
    print("0. Exit")
    
    return input("\nSelect option: ")

def main():
    text_file = input("Enter text file path (default: paste.txt): ") or "paste.txt"
    manager = TaskFlowTextManager(text_file)
    
    while True:
        choice = interactive_menu()
        
        if choice == '0':
            break
        elif choice == '1':
            manager.load_project()
        elif choice == '2':
            name = input("Function name: ")
            description = input("Description: ")
            implementation = input("Implementation: ")
            files_input = input("File indices (comma-separated, optional): ")
            files_involved = []
            if files_input:
                try:
                    files_involved = [int(x.strip()) for x in files_input.split(',')]
                except ValueError:
                    print("Invalid file indices")
                    continue
            manager.add_function(name, description, implementation, files_involved)
        elif choice == '3':
            func_id = input("Function ID (e.g., 1F): ")
            print("Leave empty to keep current value:")
            name = input("New name: ") or None
            description = input("New description: ") or None
            implementation = input("New implementation: ") or None
            files_input = input("New file indices (comma-separated): ")
            files_involved = None
            if files_input:
                try:
                    files_involved = [int(x.strip()) for x in files_input.split(',')]
                except ValueError:
                    print("Invalid file indices")
                    continue
            manager.edit_function(func_id, name, description, implementation, files_involved)
        elif choice == '4':
            func_id = input("Function ID to delete: ")
            manager.delete_function(func_id)
        elif choice == '5':
            path = input("File path: ")
            description = input("Description (optional): ")
            manager.add_file(path, description)
        elif choice == '6':
            try:
                index = int(input("File index: "))
                print("Leave empty to keep current value:")
                path = input("New path: ") or None
                description = input("New description: ") or None
                manager.edit_file(index, path, description)
            except ValueError:
                print("Invalid file index")
        elif choice == '7':
            try:
                index = int(input("File index to delete: "))
                manager.delete_file(index)
            except ValueError:
                print("Invalid file index")
        elif choice == '8':
            manager.list_functions()
        elif choice == '9':
            manager.list_files()
        elif choice == '10':
            query = input("Search query: ")
            manager.search_functions(query)
        elif choice == '11':
            func_id = input("Function ID: ")
            manager.get_function_info(func_id)
        elif choice == '12':
            manager.validate_project()
        elif choice == '13':
            manager.reorder_files()
        elif choice == '14':
            manager.save_project()

if __name__ == '__main__':
    main()