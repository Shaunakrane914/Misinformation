"""
Script to update all Gemini model references to flash-lite versions
"""
import os

# Files to update
files_to_update = [
    "backend/agents/investigator_agent.py",
    "backend/agents/research_agent.py",
    "backend/agents/coordinator_agent.py",
]

def update_model_references(file_path):
    """Update gemini-1.5-flash to gemini-1.5-flash-8b (lite version)"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace model references - using 1.5-flash-8b which is the lite version
    updated_content = content.replace('gemini-1.5-flash', 'gemini-1.5-flash-8b')
    
    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    print(f"✅ Updated: {file_path}")

if __name__ == "__main__":
    print("🔄 Updating Gemini model references to lite versions...")
    for file_path in files_to_update:
        if os.path.exists(file_path):
            update_model_references(file_path)
        else:
            print(f"⚠️  File not found: {file_path}")
    print("✨ All model references updated to gemini-1.5-flash-8b (lite)!")
