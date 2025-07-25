# project_manager.py
import sys
from pathlib import Path

# Import the original TaskFlowTextManager
# (Include the TaskFlowTextManager class from your original code here)
from task_flow_text_manager import TaskFlowTextManager

def quick_setup():
    """Quick setup wizard for new projects"""
    print("🚀 Project File Quick Setup")
    print("-" * 30)
    
    # Check if project-file.txt exists
    if not Path("project-file.txt").exists():
        print("❌ project-file.txt not found!")
        print("Run the scanner first: python project_scanner.py")
        return
    
    # Load project
    manager = TaskFlowTextManager("project-file.txt")
    manager.load_project()
    
    print(f"📁 Loaded project: {manager.project_name}")
    print(f"📄 Files: {len(manager.files)}")
    
    # Ask if user wants to add functions
    if input("\nAdd functions interactively? (y/N): ").lower() == 'y':
        while True:
            print("\n" + "="*40)
            name = input("Function name (or 'done' to finish): ")
            if name.lower() == 'done':
                break
            
            description = input("Description: ")
            
            # Show available files
            print("\nAvailable files:")
            for idx, file in manager.files.items():
                print(f"  {idx}. {file.path}")
            
            files_input = input("File indices (comma-separated): ")
            files_involved = []
            if files_input:
                try:
                    files_involved = [int(x.strip()) for x in files_input.split(',')]
                except ValueError:
                    print("Invalid file indices, skipping...")
                    continue
            
            implementation = input("Implementation: ")
            
            manager.add_function(name, description, implementation, files_involved)
    
    # Save
    manager.save_project()
    print("✅ Project file updated!")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'setup':
        quick_setup()
    else:
        main()  # Run the original interactive menu