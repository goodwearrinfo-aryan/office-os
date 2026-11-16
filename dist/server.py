#!/usr/bin/env python3
"""GitHub MCP server - connects to GitHub API for repo, issue, and PR management.

Tools:
- list_repos: List GitHub repositories
- create_issue: Create a GitHub issue  
- create_pr: Create a pull request
- get_pull_request: Get pull request details
"""

import os
import sys
import json
import requests
from typing import Optional, List, Dict, Any

# GitHub API configuration
GITHUB_TOKEN = os.environ.get("GH_TOKEN", "")
GITHUB_API_BASE = "https://api.github.com"

if not GITHUB_TOKEN:
    print("Warning: GH_TOKEN environment variable not set", file=sys.stderr)


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
    response.raise_for_status()
    return response.json() if response.text else {}


# Tool: list_repos - List GitHub repositories
def list_repos(
    owner: Optional[str] = None,
    type: str = "all",
    sort: str = "updated",
    direction: str = "desc",
) -> List[Dict[str, Any]]:
    """List GitHub repositories, optionally filtered by owner, type, sort, and direction.
    
    Args:
        owner: Filter by owner (username or organization)
        type: Filter by type (all, member, public, private, fork)
        sort: Sort criterion (updated, pushed, full_name, name)
        direction: Sort direction (asc, desc)
    
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
    }
    data = github_request("GET", endpoint, params=params)
    if isinstance(data, list):
        return data
    return []


# Tool: create_issue - Create a GitHub issue
def create_issue(
    owner: str,
    repo: str,
    title: str,
    body: Optional[str] = None,
    labels: Optional[List[str]] = None,
    assignees: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Create a GitHub issue with title, body, labels, and assignees.
    
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
    payload = {"title": title}
    if body:
        payload["body"] = body
    if labels:
        payload["labels"] = labels
    if assignees:
        payload["assignees"] = assignees
    return github_request("POST", endpoint, json=payload)


# Tool: create_pr - Create a pull request
def create_pr(
    owner: str,
    repo: str,
    title: str,
    body: Optional[str] = None,
    head: Optional[str] = None,
    base: str = "main",
) -> Dict[str, Any]:
    """Create a pull request with title, body, head branch, and base branch.
    
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
    payload = {"title": title, "base": base}
    if body:
        payload["body"] = body
    if head:
        payload["head"] = head
    return github_request("POST", endpoint, json=payload)


# Tool: get_pull_request - Get pull request details
def get_pull_request(
    owner: str,
    repo: str,
    pull_number: int,
) -> Dict[str, Any]:
    """Get details of a pull request by number.
    
    Args:
        owner: Repository owner (username or organization)
        repo: Repository name
        pull_number: Pull request number
    
    Returns:
        Pull request object
    """
    endpoint = f"/repos/{owner}/{repo}/pulls/{pull_number}"
    return github_request("GET", endpoint)


# Tool registry for MCP discovery
TOOL_SPEC = {
    "list_repos": {
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


def get_tool_specs():
    """Return tool specifications for MCP registration."""
    return TOOL_SPEC


def execute_tool(tool_name: str, args: dict) -> Any:
    """Execute a tool by name with given arguments."""
    tools = {
        "list_repos": list_repos,
        "create_issue": create_issue,
        "create_pr": create_pr,
        "get_pull_request": get_pull_request,
    }
    if tool_name not in tools:
        raise ValueError(f"Unknown tool: {tool_name}")
    return tools[tool_name](**args)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python server.py <tool_name> [args...]")
        print("Available tools: list_repos, create_issue, create_pr, get_pull_request")
        sys.exit(1)
    
    tool_name = sys.argv[1]
    # Parse remaining args as JSON dict
    args_str = " ".join(sys.argv[2:])
    try:
        args = json.loads(args_str) if args_str else {}
    except json.JSONDecodeError:
        args = {}
    
    try:
        result = execute_tool(tool_name, args)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}, indent=2), file=sys.stderr)
        sys.exit(1)