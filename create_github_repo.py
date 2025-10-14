#!/usr/bin/env python3
"""
Create GitHub repository and push code using Replit's GitHub connector
"""
import os
import json
import subprocess
import requests

def get_github_token():
    """Get GitHub access token from Replit connector"""
    hostname = os.environ.get('REPLIT_CONNECTORS_HOSTNAME')
    repl_identity = os.environ.get('REPL_IDENTITY')
    
    if not hostname or not repl_identity:
        raise Exception("Not running in Replit environment")
    
    headers = {
        'Accept': 'application/json',
        'X_REPLIT_TOKEN': f'repl {repl_identity}'
    }
    
    url = f'https://{hostname}/api/v2/connection?include_secrets=true&connector_names=github'
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    data = response.json()
    if not data.get('items'):
        raise Exception("GitHub not connected")
    
    connection = data['items'][0]
    token = connection['settings'].get('access_token')
    
    if not token:
        raise Exception("No access token found")
    
    return token

def create_github_repo(token, repo_name, description=""):
    """Create a new GitHub repository"""
    url = "https://api.github.com/user/repos"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "name": repo_name,
        "description": description,
        "private": False,
        "auto_init": False
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 201:
        repo_data = response.json()
        return repo_data
    elif response.status_code == 422:
        # Repository already exists
        print(f"Repository '{repo_name}' already exists")
        # Get the existing repo
        user_url = "https://api.github.com/user"
        user_response = requests.get(user_url, headers=headers)
        username = user_response.json()['login']
        
        repo_url = f"https://api.github.com/repos/{username}/{repo_name}"
        repo_response = requests.get(repo_url, headers=headers)
        return repo_response.json()
    else:
        response.raise_for_status()

def main():
    print("=" * 60)
    print("Creating GitHub Repository")
    print("=" * 60)
    
    try:
        # Get GitHub token
        print("\n1. Getting GitHub access token...")
        token = get_github_token()
        print("   ✓ Token retrieved")
        
        # Create repository
        print("\n2. Creating repository 'openvds-mcp-server'...")
        repo = create_github_repo(
            token, 
            "openvds-mcp-server",
            "MCP server for Bluware OpenVDS - AI-assisted access to seismic data"
        )
        print(f"   ✓ Repository created: {repo['html_url']}")
        print(f"   ✓ Clone URL: {repo['clone_url']}")
        
        # Output the git commands to run
        print("\n" + "=" * 60)
        print("Repository Created Successfully!")
        print("=" * 60)
        print(f"\nRepository URL: {repo['html_url']}")
        print(f"\nClone URL: {repo['clone_url']}")
        print("\nOn your Mac, run:")
        print(f"  git clone {repo['clone_url']}")
        print(f"  cd openvds-mcp-server")
        print()
        
        # Save repo info
        with open('/tmp/github_repo_info.json', 'w') as f:
            json.dump({
                'html_url': repo['html_url'],
                'clone_url': repo['clone_url'],
                'git_url': repo['git_url'],
                'ssh_url': repo['ssh_url']
            }, f, indent=2)
        
        print("Repository info saved to /tmp/github_repo_info.json")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
