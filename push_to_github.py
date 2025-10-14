#!/usr/bin/env python3
"""
Push code to GitHub repository using Replit's GitHub connector
"""
import os
import json
import subprocess

def get_repo_info():
    """Get repository info from previous step"""
    with open('/tmp/github_repo_info.json', 'r') as f:
        return json.load(f)

def push_to_github():
    """Push code to GitHub"""
    print("=" * 60)
    print("Pushing Code to GitHub")
    print("=" * 60)
    
    try:
        # Get repo info
        repo = get_repo_info()
        clone_url = repo['clone_url']
        
        print(f"\n1. Repository: {repo['html_url']}")
        
        # Check if remote exists
        result = subprocess.run(['git', 'remote', 'get-url', 'origin'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"\n2. Remote 'origin' already exists: {result.stdout.strip()}")
            print("   Updating remote URL...")
            subprocess.run(['git', 'remote', 'set-url', 'origin', clone_url], check=True)
        else:
            print(f"\n2. Adding remote 'origin': {clone_url}")
            subprocess.run(['git', 'remote', 'add', 'origin', clone_url], check=True)
        
        print("   ✓ Remote configured")
        
        # Check git status
        print("\n3. Checking git status...")
        result = subprocess.run(['git', 'status', '--short'], 
                              capture_output=True, text=True)
        
        if result.stdout.strip():
            print(f"   Files to commit:\n{result.stdout}")
            
            # Stage all files
            print("\n4. Staging files...")
            subprocess.run(['git', 'add', '.'], check=True)
            print("   ✓ Files staged")
            
            # Commit
            print("\n5. Creating commit...")
            subprocess.run([
                'git', 'commit', '-m', 
                'Initial commit: OpenVDS MCP Server with Docker support'
            ], check=True)
            print("   ✓ Commit created")
        else:
            print("   No changes to commit")
        
        # Push to GitHub
        print("\n6. Pushing to GitHub...")
        result = subprocess.run(['git', 'push', '-u', 'origin', 'main'], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            # Try 'master' branch if 'main' doesn't work
            print("   Trying 'master' branch...")
            result = subprocess.run(['git', 'push', '-u', 'origin', 'master'], 
                                  capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("   ✓ Code pushed successfully!")
        else:
            print(f"   Error: {result.stderr}")
            raise Exception("Push failed")
        
        print("\n" + "=" * 60)
        print("✓ Code Successfully Pushed to GitHub!")
        print("=" * 60)
        print(f"\nRepository: {repo['html_url']}")
        print(f"\nOn your Mac, run:")
        print(f"  git clone {clone_url}")
        print(f"  cd openvds-mcp-server")
        print(f"  ./run-docker.sh")
        print()
        
    except subprocess.TimeoutExpired:
        print("\n✗ Push timed out - you may need to authenticate")
        print("The repository is created, but needs manual push")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(push_to_github())
