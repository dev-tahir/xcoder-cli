import os
import re
import json
import fnmatch
from pathlib import Path
from typing import List, Set, Dict, Optional, Tuple
from dataclasses import dataclass
import argparse

from technology_detector import TechnologyDetector, TechnologyInfo
from function_analyzer import FunctionAnalyzer, AnalyzedFunction

@dataclass
class ProjectFile:
    index: int
    path: str
    relative_path: str
    size: int
    extension: str

@dataclass
class ProjectInfo:
    name: str
    description: str
    technologies: List[str]
    root_path: str

class IgnorePatternManager:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.gitignore_patterns = []
        self.tech_ignore_patterns = []
        self.system_excludes = [
            # Project management files
            "project_manager.py",
            "project_scanner.py", 
            "technology_detector.py",
            "function_analyzer.py",
            "TaskFlowTextManager.py",  # Added this
            "project-file.txt",
            # Common excludes
            ".git/**",
            ".DS_Store",
            "Thumbs.db"
        ]
        
    def load_gitignore(self):
        """Load patterns from .gitignore file"""
        gitignore_path = self.project_root / ".gitignore"
        if gitignore_path.exists():
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    self.gitignore_patterns.append(line)
        
        print(f"Loaded {len(self.gitignore_patterns)} patterns from .gitignore")
    
    def load_tech_ignore_patterns(self, technologies: List[TechnologyInfo]):
        """Load technology-specific ignore patterns"""
        for tech in technologies:
            tech_file = self.project_root / f"{tech.name.lower().replace('-', '_')}.txt"
            
            if tech_file.exists():
                with open(tech_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        self.tech_ignore_patterns.append(line)
        
        print(f"Loaded {len(self.tech_ignore_patterns)} technology-specific patterns")
    
    def should_ignore(self, file_path: str) -> bool:
        """Check if file should be ignored"""
        relative_path = os.path.relpath(file_path, self.project_root)
        filename = os.path.basename(file_path)
        
        # Always ignore .git directory
        if '.git' in Path(relative_path).parts:
            return True
        
        # Check system excludes
        for pattern in self.system_excludes:
            if self._match_pattern(relative_path, pattern) or self._match_pattern(filename, pattern):
                return True
        
        # Check all patterns
        all_patterns = self.gitignore_patterns + self.tech_ignore_patterns
        
        for pattern in all_patterns:
            if self._match_pattern(relative_path, pattern):
                return True
        
        return False
    
    def _match_pattern(self, path: str, pattern: str) -> bool:
        """Match file path against ignore pattern"""
        if pattern.endswith('/'):
            pattern = pattern[:-1]
            return any(fnmatch.fnmatch(part, pattern) for part in Path(path).parts)
        elif '**' in pattern:
            pattern = pattern.replace('**', '*')
            return fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(os.path.basename(path), pattern)
        else:
            return fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(os.path.basename(path), pattern)

class ProjectScanner:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.ignore_manager = IgnorePatternManager(project_root)
        self.tech_detector = TechnologyDetector()
        self.function_analyzer = FunctionAnalyzer()
        
    def scan_project(self) -> Tuple[ProjectInfo, List[ProjectFile], List[AnalyzedFunction]]:
        """Scan project and return comprehensive analysis"""
        
        # Detect technologies
        print("🔍 Detecting technologies...")
        technologies = self.tech_detector.detect_technologies(str(self.project_root))
        
        print(f"📋 Detected technologies:")
        for tech in technologies:
            print(f"   - {tech.name} ({tech.confidence:.1%}): {tech.description}")
        
        # Create technology ignore files
        self.tech_detector.create_technology_files(str(self.project_root), technologies)
        
        # Load ignore patterns
        self.ignore_manager.load_gitignore()
        self.ignore_manager.load_tech_ignore_patterns(technologies)
        
        # Get project info
        project_info = self._get_project_info([t.name for t in technologies])
        
        # Scan files
        print("📁 Scanning project files...")
        files = self._scan_files()
        
        # Analyze functions using AI
        print("🤖 Analyzing project functions...")
        file_dicts = [
            {
                "index": f.index,
                "path": f.path,
                "relative_path": f.relative_path,
                "extension": f.extension
            }
            for f in files
        ]
        
        functions = self.function_analyzer.analyze_project_functions(
            file_dicts, [t.name for t in technologies]
        )
        
        return project_info, files, functions
    
    def _scan_files(self) -> List[ProjectFile]:
        """Scan and collect project files"""
        files = []
        index = 1
        
        for root, dirs, filenames in os.walk(self.project_root):
            # Filter directories
            dirs[:] = [d for d in dirs if not self.ignore_manager.should_ignore(os.path.join(root, d))]
            
            for filename in filenames:
                file_path = os.path.join(root, filename)
                
                if not self.ignore_manager.should_ignore(file_path):
                    relative_path = os.path.relpath(file_path, self.project_root)
                    
                    try:
                        size = os.path.getsize(file_path)
                        extension = Path(filename).suffix
                        
                        project_file = ProjectFile(
                            index=index,
                            path=file_path,
                            relative_path=relative_path,
                            size=size,
                            extension=extension
                        )
                        files.append(project_file)
                        index += 1
                    except OSError:
                        continue
        
        # Sort files by path
        files.sort(key=lambda f: f.relative_path)
        
        # Update indices after sorting
        for i, file in enumerate(files, 1):
            file.index = i
        
        return files
    
    def _get_project_info(self, technologies: List[str]) -> ProjectInfo:
        """Extract project information"""
        project_name = self.project_root.name.upper()
        description = self._extract_description()
        
        return ProjectInfo(
            name=project_name,
            description=description,
            technologies=technologies,
            root_path=str(self.project_root)
        )
    
    def _extract_description(self) -> str:
        """Extract project description from various sources"""
        # Try package.json first
        package_json = self.project_root / "package.json"
        if package_json.exists():
            try:
                with open(package_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'description' in data and data['description']:
                        return data['description'].upper()
            except:
                pass
        
        # Try manifest.json for browser extensions
        manifest_json = self.project_root / "manifest.json"
        if manifest_json.exists():
            try:
                with open(manifest_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'description' in data and data['description']:
                        return data['description'].upper()
            except:
                pass
        
        # Try README files
        for readme_name in ['README.md', 'README.txt', 'README']:
            readme_path = self.project_root / readme_name
            if readme_path.exists():
                try:
                    with open(readme_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        lines = [line.strip() for line in content.split('\n') if line.strip()]
                        if lines:
                            first_line = lines[0].replace('#', '').strip()
                            if len(first_line) > 10:
                                return first_line.upper()
                except:
                    pass
        
        return "PROJECT DESCRIPTION"

class ProjectFileGenerator:
    def __init__(self, output_path: str = "project-file.txt"):
        self.output_path = output_path
    
    def generate(self, project_info: ProjectInfo, files: List[ProjectFile], functions: List[AnalyzedFunction]):
        """Generate project-file.txt with detailed function analysis"""
        content = self._build_content(project_info, files, functions)
        
        with open(self.output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Generated {self.output_path} with {len(files)} files and {len(functions)} functions")
    
    def _build_content(self, project_info: ProjectInfo, files: List[ProjectFile], functions: List[AnalyzedFunction]) -> str:
        """Build the content for project-file.txt with detailed function format"""
        lines = []
        
        # Header
        lines.append(f"Project:{project_info.name}")
        lines.append(f"Description:{project_info.description}")
        lines.append(f"technology:{', '.join(project_info.technologies)}")
        
        # Files section
        lines.append("PROJECT FILES INDEX:")
        for file in files:
            lines.append(f"{file.index}. {file.relative_path}")
        
        lines.append("")
        
        # Functions section with detailed format
        lines.append("All functions:")
        
        if functions:
            for i, func in enumerate(functions, 1):
                lines.append(f"{i}F. {func.name}")
                lines.append(func.description)
                
                # Add files flow if available
                if func.files_flow:
                    lines.append(f"Files(Index) Flow: {func.files_flow}")
                
                lines.append("Implementation:")
                lines.append(func.implementation)
                lines.append("")
        else:
            lines.append("# No functions identified during analysis")
            lines.append("")
        
        return '\n'.join(lines)
def main():
    parser = argparse.ArgumentParser(description='Generate project-file.txt with AI analysis')
    parser.add_argument('--path', '-p', default='.', help='Project root path (default: current directory)')
    parser.add_argument('--output', '-o', default='project-file.txt', help='Output file path')
    parser.add_argument('--no-functions', action='store_true', help='Skip function analysis')
    
    args = parser.parse_args()
    
    project_root = os.path.abspath(args.path)
    
    if not os.path.exists(project_root):
        print(f"❌ Error: Project path '{project_root}' does not exist")
        return
    
    print(f"🚀 Scanning project: {project_root}")
    print("=" * 60)
    
    try:
        # Initialize scanner and generator
        scanner = ProjectScanner(project_root)
        generator = ProjectFileGenerator(args.output)
        
        # Scan project
        project_info, files, functions = scanner.scan_project()
        
        print(f"\n📊 Project Summary:")
        print(f"   Name: {project_info.name}")
        print(f"   Technologies: {', '.join(project_info.technologies)}")
        print(f"   Files found: {len(files)}")
        print(f"   Functions analyzed: {len(functions)}")
        
        # Show file statistics
        extensions = {}
        for file in files:
            ext = file.extension or 'no extension'
            extensions[ext] = extensions.get(ext, 0) + 1
        
        print(f"\n📁 File types:")
        for ext, count in sorted(extensions.items()):
            print(f"   {ext}: {count}")
        
        if functions:
            print(f"\n🔧 Functions identified:")
            for func in functions:
                print(f"   - {func.name}")
        
        # Generate project file
        generator.generate(project_info, files, functions)
        
        print(f"\n✅ Successfully generated {args.output}")
        print("📝 The project file includes AI-analyzed functions!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()