"""
Initialize Polymarket project and agents in the entity registry.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from entity.model import Project, Agent, registry

def main():
    # Create the Polymarket project
    project = Project(
        name="Polymarket Profitability Research",
        description="Research and analysis of Polymarket profitability",
        mode="PAPER_ONLY",
        path="/Users/aryanagarwal/Documents/polymarket.research/",
        status="ACTIVE"
    )
    created_project = registry.create(project)
    print(f"Created project: {created_project.id} - {created_project.name}")

    # Define the agents for the Polymarket project
    agents_data = [
        ("PM-RESEARCH", "research", "IDLE"),
        ("PM-DATA", "data", "IDLE"),
        ("PM-SIGNAL", "signal", "IDLE"),
        ("PM-RISK", "risk", "IDLE"),
        ("PM-ATTRIBUTION", "attribution", "IDLE"),
        ("PM-AUDIT", "audit", "IDLE"),
        ("PM-VALIDATION", "validation", "IDLE"),
        ("PM-OPS", "ops", "IDLE"),
    ]

    created_agents = []
    for name, role, status in agents_data:
        agent = Agent(
            name=name,
            project_id=created_project.id,
            role=role,
            status=status
        )
        created_agent = registry.create(agent)
        created_agents.append(created_agent)
        print(f"Created agent: {created_agent.id} - {created_agent.name} ({created_agent.role})")

    # Print summary
    print("\n=== Summary ===")
    print(f"Project: {created_project.name} (ID: {created_project.id})")
    print(f"Agents created: {len(created_agents)}")
    for agent in created_agents:
        print(f"  - {agent.name} ({agent.role}) [ID: {agent.id}]")

if __name__ == "__main__":
    main()