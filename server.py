#!/usr/bin/env python3
"""MCP server for GitHub API integration.

Provides tools for:
- list_repos: List GitHub repositories
- create_issue: Create a GitHub issue
- create_pr: Create a pull request
- get_pull_request: Get details of a pull request
"""

import os
import json
import requests
import time
from typing import Optional, List, Dict, Any

# GitHub API configuration
GITHUB_TOKEN = os.environ.get("GH_TOKEN", "")

GITHUB_API_BASE = "https://api.github.com"

if not GITHUB_TOKEN:
    print("Warning: GH_TOKEN environment variable not set")


def github_request(method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
    """Make a request to the GitHub API."""
    url = f"{GITHUB_API_BASE}{endpoint}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "MCP-Builder-Github",
    }
    if "headers" in kwargs:
        headers.update(kwargs.pop("headers"))
    response = requests.request(method, url, headers=headers, **kwargs)
    if response.status_code == 401:
        raise Exception("Unauthorized: Check your GH_TOKEN environment variable")
    if response.status_code == 403:
        raise Exception("Forbidden: You may have hit rate limits or lack permissions")
    if response.status_code == 404:
        raise Exception(f"Not Found: {endpoint}")
    response.raise_for_status()
    return response.json() if response.text else {}


# Tool: list_repos
def list_repos(
    owner: Optional[str] = None,
    type: str = "all",
    sort: str = "updated",
    direction: str = "desc",
    per_page: int = 30,
    page: int = 1,
) -> List[Dict[str, Any]]:
    """List GitHub repositories.
    
    Args:
        owner: Filter by owner (username or organization)
        type: Filter by type (all, member, public, private, fork)
        sort: Sort criterion (updated, pushed, full_name, name)
        direction: Sort direction (asc, desc)
        per_page: Number of results per page (default: 30)
        page: Page number (default: 1)
    
    Returns:
        List of repository objects
    """
    if owner:
        endpoint = f"/users/{owner}/repos"
    else:
        endpoint = "/user/repos"
    params = {
        "type": type,
        "sort": sort,
        "direction": direction,
        "per_page": per_page,
        "page": page,
    }
    
    all_repos = []
    while True:
        data = github_request("GET", endpoint, params=params)
        if isinstance(data, list):
            all_repos.extend(data)
            if len(data) < per_page:
                break
            params["page"] += 1
        else:
            break
    
    return all_repos


# Tool: create_issue
def create_issue(
    owner: str,
    repo: str,
    title: str,
    body: Optional[str] = None,
    labels: Optional[List[str]] = None,
    assignees: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Create a GitHub issue.
    
    Args:
        owner: Repository owner (username or organization)
        repo: Repository name
        title: Issue title
        body: Issue body/description
        labels: List of label names
        assignees: List of assignee usernames
    
    Returns:
        Created issue object
    """
    endpoint = f"/repos/{owner}/{repo}/issues"
    payload = {
        "title": title,
    }
    if body:
        payload["body"] = body
    if labels:
        payload["labels"] = labels
    if assignees:
        payload["assignees"] = assignees
    
    return github_request("POST", endpoint, json=payload)


# Tool: create_pr
def create_pr(
    owner: str,
    repo: str,
    title: str,
    body: Optional[str] = None,
    head: Optional[str] = None,
    base: str = "main",
) -> Dict[str, Any]:
    """Create a pull request.
    
    Args:
        owner: Repository owner (username or organization)
        repo: Repository name
        title: PR title
        body: PR body/description
        head: Head branch (format: owner:branch or just branch name)
        base: Base branch (default: main)
    
    Returns:
        Created pull request object
    """
    endpoint = f"/repos/{owner}/{repo}/pulls"
    payload = {
        "title": title,
        "base": base,
    }
    if body:
        payload["body"] = body
    if head:
        payload["head"] = head
    
    return github_request("POST", endpoint, json=payload)


# Tool: get_pull_request
def get_pull_request(
    owner: str,
    repo: str,
    pull_number: int,
) -> Dict[str, Any]:
    """Get details of a pull request.
    
    Args:
        owner: Repository owner (username or organization)
        repo: Repository name
        pull_number: Pull request number
    
    Returns:
        Pull request object
    """
    endpoint = f"/repos/{owner}/{repo}/pulls/{pull_number}"
    return github_request("GET", endpoint)


# Tool metadata for MCP description
TOOLS = {
    "list_repos": {
        "function": list_repos,
        "description": "List GitHub repositories, optionally filtered by owner, type, sort, and direction.",
        "parameters": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Filter by owner (username or organization)"},
                "type": {"type": "string", "description": "Filter by type (all, member, public, private, fork)"},
                "sort": {"type": "string", "description": "Sort criterion (updated, pushed, full_name, name)"},
                "direction": {"type": "string", "description": "Sort direction (asc, desc)"},
            },
            "required": [],
            "additionalProperties": False,
        },
    },
    "create_issue": {
        "function": create_issue,
        "description": "Create a GitHub issue with title, body, labels, and assignees.",
        "parameters": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner (username or organization)"},
                "repo": {"type": "string", "description": "Repository name"},
                "title": {"type": "string", "description": "Issue title"},
                "body": {"type": "string", "description": "Issue body/description"},
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of label names",
                },
                "assignees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of assignee usernames",
                },
            },
            "required": ["owner", "repo", "title"],
            "additionalProperties": False,
        },
    },
    "create_pr": {
        "function": create_pr,
        "description": "Create a pull request with title, body, head branch, and base branch.",
        "parameters": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner (username or organization)"},
                "repo": {"type": "string", "description": "Repository name"},
                "title": {"type": "string", "description": "PR title"},
                "body": {"type": "string", "description": "PR body/description"},
                "head": {"type": "string", "description": "Head branch (format: owner:branch or just branch name)"},
                "base": {"type": "string", "description": "Base branch (default: main)"},
            },
            "required": ["owner", "repo", "title"],
            "additionalProperties": False,
        },
    },
    "get_pull_request": {
        "function": get_pull_request,
        "description": "Get details of a pull request by number.",
        "parameters": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner (username or organization)"},
                "repo": {"type": "string", "description": "Repository name"},
                "pull_number": {"type": "integer", "description": "Pull request number"},
            },
            "required": ["owner", "repo", "pull_number"],
            "additionalProperties": False,
        },
    },
}


def get_tools():
    """Return the tools dictionary for MCP registration."""
    return TOOLS


if __name__ == "__main__":
    # Simple CLI for testing
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python server.py <tool_name> [args...]")
        print("Available tools: list_repos, create_issue, create_pr, get_pull_request")
        sys.exit(1)
    
    tool_name = sys.argv[1]
    
    if tool_name == "list_repos":
        owner = sys.argv[2] if len(sys.argv) > 2 else None
        repos = list_repos(owner=owner)
        print(json.dumps(repos, indent=2))
    elif tool_name == "create_issue":
        owner = sys.argv[2]
        repo = sys.argv[3]
        title = sys.argv[4]
        body = sys.argv[5] if len(sys.argv) > 5 else None
        labels = json.loads(sys.argv[6]) if len(sys.argv) > 6 else None
        assignees = json.loads(sys.argv[7]) if len(sys.argv) > 7 else None
        result = create_issue(owner, repo, title, body, labels, assignees)
        print(json.dumps(result, indent=2))
    elif tool_name == "create_pr":
        owner = sys.argv[2]
        repo = sys.argv[3]
        title = sys.argv[4]
        body = sys.argv[5] if len(sys.argv) > 5 else None
        head = sys.argv[6] if len(sys.argv) > 6 else None
        base = sys.argv[7] if len(sys.argv) > 7 else "main"
        result = create_pr(owner, repo, title, body, head, base)
        print(json.dumps(result, indent=2))
    elif tool_name == "get_pull_request":
        owner = sys.argv[2]
        repo = sys.argv[3]
        pull_number = int(sys.argv[4])
        result = get_pull_request(owner, repo, pull_number)
        print(json.dumps(result, indent=2))
    else:
        print(f"Unknown tool: {tool_name}")
        sys.exit(1)