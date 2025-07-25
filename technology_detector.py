import os
import json
import requests
from pathlib import Path
from typing import List, Dict, Set
from dataclasses import dataclass

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_API_URL = os.environ.get("GEMINI_API_URL")

@dataclass
class TechnologyInfo:
    name: str
    confidence: float
    description: str
    typical_files: List[str]

class TechnologyDetector:
    def __init__(self, api_key: str = GEMINI_API_KEY):
        self.api_key = api_key
        self.base_url = GEMINI_API_URL
        
    def detect_technologies(self, project_root: str) -> List[TechnologyInfo]:
        """Detect technologies in project using AI analysis"""
        # Get root structure
        root_structure = self._get_root_structure(project_root)
        
        # Try rule-based detection first
        rule_based = self._rule_based_detection(project_root)
        
        if rule_based:
            return rule_based
        
        # Use AI for unknown projects
        return self._ai_based_detection(root_structure)
    
    def _get_root_structure(self, project_root: str) -> Dict[str, List[str]]:
        """Get root files and directories structure"""
        root_path = Path(project_root)
        structure = {
            "files": [],
            "directories": [],
            "file_extensions": [],
            "notable_files": [],
            "files_with_extensions": []  # New field for complete filenames
        }
        
        file_extensions_set = set()  # Use set to avoid duplicates for extensions
        
        try:
            for item in root_path.iterdir():
                if item.is_file():
                    # Add complete filename with extension
                    structure["files_with_extensions"].append(item.name)
                    structure["files"].append(item.name)
                    
                    if item.suffix:
                        file_extensions_set.add(item.suffix)
                    
                    # Mark notable files
                    notable_patterns = [
                        'package.json', 'requirements.txt', 'Cargo.toml', 'go.mod',
                        'pom.xml', 'composer.json', 'Gemfile', 'manifest.json',
                        'setup.py', 'pyproject.toml', 'CMakeLists.txt', 'Makefile'
                    ]
                    if item.name.lower() in [p.lower() for p in notable_patterns]:
                        structure["notable_files"].append(item.name)
                        
                elif item.is_dir() and not item.name.startswith('.'):
                    structure["directories"].append(item.name)
        except PermissionError:
            pass
        
        # Convert set to list for file_extensions
        structure["file_extensions"] = list(file_extensions_set)
        return structure

    def _rule_based_detection(self, project_root: str) -> List[TechnologyInfo]:
        """Rule-based technology detection"""
        root_path = Path(project_root)
        technologies = []
        
        # JavaScript/Node.js ecosystem
        if (root_path / "package.json").exists():
            package_data = self._read_package_json(root_path / "package.json")
            if package_data:
                deps = {**package_data.get('dependencies', {}), **package_data.get('devDependencies', {})}
                
                if 'next' in deps:
                    technologies.append(TechnologyInfo("Next-JS", 0.9, "Next.js React framework", ["next.config.js", "pages/", "app/"]))
                elif 'react' in deps:
                    technologies.append(TechnologyInfo("React", 0.8, "React JavaScript library", ["src/", "public/"]))
                elif '@angular/core' in deps:
                    technologies.append(TechnologyInfo("Angular", 0.9, "Angular framework", ["angular.json", "src/app/"]))
                elif 'vue' in deps:
                    technologies.append(TechnologyInfo("Vue", 0.8, "Vue.js framework", ["vue.config.js", "src/"]))
                else:
                    technologies.append(TechnologyInfo("Node.js", 0.7, "Node.js application", ["package.json"]))
        
        # Python
        if (root_path / "requirements.txt").exists() or (root_path / "setup.py").exists() or (root_path / "pyproject.toml").exists():
            technologies.append(TechnologyInfo("Python", 0.8, "Python application", ["requirements.txt", "setup.py"]))
        
        # Browser Extension
        if (root_path / "manifest.json").exists():
            manifest_data = self._read_manifest_json(root_path / "manifest.json")
            if manifest_data and 'manifest_version' in manifest_data:
                technologies.append(TechnologyInfo("Browser-Extension", 0.9, "Browser extension", ["manifest.json", "background.js", "content_script.js"]))
        
        # Other technologies
        if (root_path / "Cargo.toml").exists():
            technologies.append(TechnologyInfo("Rust", 0.9, "Rust application", ["Cargo.toml", "src/"]))
        
        if (root_path / "go.mod").exists():
            technologies.append(TechnologyInfo("Go", 0.9, "Go application", ["go.mod", "main.go"]))
        
        if (root_path / "pom.xml").exists():
            technologies.append(TechnologyInfo("Java", 0.9, "Java/Maven project", ["pom.xml", "src/"]))
        
        return technologies
    
    def _ai_based_detection(self, structure: Dict[str, List[str]]) -> List[TechnologyInfo]:
        """Use AI to detect technologies from project structure"""
        prompt = f"""
        Analyze this project structure and identify the technologies being used:
        
        Files in root directory: {', '.join(structure['files_with_extensions'])}
        Directories in root: {', '.join(structure['directories'])}
        File extensions found: {', '.join(structure['file_extensions'])}
        Notable files: {', '.join(structure['notable_files'])}
        
        Identify ALL technologies that might be present in this project. Consider:
        - Programming languages
        - Frameworks and libraries  
        - Development tools
        - Project types (web app, mobile app, browser extension, etc.)
        
        Return a JSON array with objects containing:
        - "name": technology name (use standard names like "JavaScript", "Python", "Browser-Extension", "React", etc.)
        - "confidence": confidence score 0.0-1.0
        - "description": brief description
        - "typical_files": array of files/patterns typically associated with this technology
        
        Example format:
        [
            {{"name": "JavaScript", "confidence": 0.9, "description": "JavaScript programming language", "typical_files": ["*.js", "package.json"]}},
            {{"name": "Browser-Extension", "confidence": 0.8, "description": "Browser extension project", "typical_files": ["manifest.json", "background.js"]}}
        ]
        
        Return ONLY the JSON array, no other text.
        """
        print("Sending AI request for technology detection...")
        print(f"Prompt: {prompt}...")
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
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            content = result['candidates'][0]['content']['parts'][0]['text']
            
            # Extract JSON from response
            json_match = self._extract_json_from_text(content)
            if json_match:
                tech_data = json.loads(json_match)
                return [
                    TechnologyInfo(
                        name=tech['name'],
                        confidence=tech['confidence'],
                        description=tech['description'],
                        typical_files=tech['typical_files']
                    )
                    for tech in tech_data
                ]
        
        except Exception as e:
            print(f"Error in AI technology detection: {e}")
        
        # Fallback
        return [TechnologyInfo("Unknown", 0.5, "Unknown project type", [])]
    
    def _extract_json_from_text(self, text: str) -> str:
        """Extract JSON array from text response"""
        import re
        # Try to find JSON array
        json_pattern = r'\[[\s\S]*?\]'
        matches = re.findall(json_pattern, text)
        
        for match in matches:
            try:
                json.loads(match)  # Validate JSON
                return match
            except:
                continue
        
        return None
    
    def _read_package_json(self, path: Path) -> Dict:
        """Read package.json file"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def _read_manifest_json(self, path: Path) -> Dict:
        """Read manifest.json file"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def create_technology_files(self, project_root: str, technologies: List[TechnologyInfo]):
        """Create technology-specific ignore files"""
        root_path = Path(project_root)
        
        for tech in technologies:
            tech_file = root_path / f"{tech.name.lower().replace('-', '_')}.txt"
            
            if not tech_file.exists():
                patterns = self._generate_ignore_patterns(tech.name)
                
                with open(tech_file, 'w', encoding='utf-8') as f:
                    f.write(f"# Ignore patterns for {tech.name} projects\n")
                    f.write(f"# {tech.description}\n")
                    f.write(f"# Confidence: {tech.confidence:.1%}\n\n")
                    
                    for pattern in patterns:
                        f.write(f"{pattern}\n")
                
                print(f"Created {tech_file.name} for {tech.name}")
    
    def _generate_ignore_patterns(self, technology: str) -> List[str]:
        """Generate ignore patterns for technology"""
        prompt = f"""
        Generate a comprehensive list of files and folders that should be ignored when creating documentation for a {technology} project.
        Include:
        - Build outputs and compiled files
        - Dependencies and package managers  
        - IDE and editor files
        - OS-specific files
        - Temporary files
        - Cache directories
        - Environment files
        - Log files
        - Development tools files
        
        Return ONLY a JSON array of glob patterns, no other text:
        Example: ["node_modules/**", "*.log", ".env*", "dist/**"]
        """
        
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
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            content = result['candidates'][0]['content']['parts'][0]['text']
            
            json_match = self._extract_json_from_text(content)
            if json_match:
                return json.loads(json_match)
                
        except Exception as e:
            print(f"Error generating patterns for {technology}: {e}")
        
        # Fallback patterns
        return self._get_default_patterns(technology)
    
    def _get_default_patterns(self, technology: str) -> List[str]:
        """Default ignore patterns for technologies"""
        patterns = {
            "javascript": ["node_modules/**", "*.log", ".env*", "dist/**", "build/**"],
            "python": ["__pycache__/**", "*.pyc", "venv/**", "*.egg-info/**", ".pytest_cache/**"],
            "browser-extension": ["*.zip", "*.crx", "web-ext-artifacts/**"],
            "unknown": ["*.log", ".env*", ".DS_Store", "Thumbs.db", ".vscode/**", ".idea/**"]
        }
        
        key = technology.lower().replace('-', '').replace('_', '')
        return patterns.get(key, patterns["unknown"])

# Usage example and testing
if __name__ == '__main__':
    detector = TechnologyDetector()
    technologies = detector.detect_technologies('.')
    
    print("Detected Technologies:")
    for tech in technologies:
        print(f"- {tech.name} ({tech.confidence:.1%}): {tech.description}")
    
    detector.create_technology_files('.', technologies)