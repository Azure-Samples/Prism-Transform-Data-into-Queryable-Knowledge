"""
Launch Prism Workflows in DevUI

This script launches the interactive DevUI for running project workflows.
Users can select and run workflows to automatically answer questions
using the project's knowledge base.

Workflows are loaded dynamically from the project's workflow_config.json.
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()

from agent_framework.devui import serve
from workflows.workflow_agent import WorkflowAgentFactory, get_workflows_for_project


def main():
    """Launch DevUI with project workflows"""

    # Get project name from environment
    project_name = os.getenv("PRISM_PROJECT_NAME", "_example")

    print("=" * 80)
    print("Prism Workflows - DevUI")
    print("=" * 80)
    print()
    print(f"Project: {project_name}")
    print()

    # Check if project exists
    project_path = Path("projects") / project_name
    if not project_path.exists():
        print(f"ERROR: Project not found: {project_path}")
        print()
        print("Available projects:")
        projects_dir = Path("projects")
        if projects_dir.exists():
            for p in projects_dir.iterdir():
                if p.is_dir() and not p.name.startswith('.'):
                    print(f"  - {p.name}")
        print()
        print("Set PRISM_PROJECT_NAME environment variable to use a different project.")
        return 1

    # Check if workflow config exists
    config_path = project_path / "workflow_config.json"
    if not config_path.exists():
        print(f"ERROR: Workflow config not found: {config_path}")
        print()
        print("Create a workflow_config.json file with sections and questions.")
        return 1

    # Load workflows
    print("Loading workflows...")
    try:
        factory = WorkflowAgentFactory(project_name)
        section_ids = factory.get_all_section_ids()

        if not section_ids:
            print("WARNING: No sections found in workflow_config.json")
            print("Add sections with questions to enable workflows.")
            return 1

        print()
        print("Available workflows:")
        workflows = []
        for section_id in section_ids:
            info = factory.get_section_info(section_id)
            if info:
                print(f"  - {info['name']} ({info['question_count']} questions)")
                try:
                    workflow = factory.build_section_workflow(section_id)
                    workflows.append(workflow)
                except Exception as e:
                    print(f"    WARNING: Could not build workflow: {e}")

    except Exception as e:
        print(f"ERROR: Failed to load workflows: {e}")
        import traceback
        traceback.print_exc()
        return 1

    if not workflows:
        print()
        print("ERROR: No valid workflows could be built.")
        return 1

    print()
    print("Workflow features:")
    print("  ✓ Sequential question processing (one agent per question)")
    print("  ✓ Knowledge base search with citations")
    print("  ✓ Automatic answer extraction")
    print("  ✓ Document reference extraction")
    print("  ✓ Results saved to projects/{project}/output/results.json")
    print()
    print("=" * 80)
    print("LAUNCHING DEVUI")
    print("=" * 80)
    print()
    print("DevUI will open in your browser at: http://localhost:8080")
    print()
    print("How to use:")
    print("  1. Select a workflow from the dropdown menu")
    print("  2. Enter a start message (or use default)")
    print("  3. Click 'Run' to start the workflow")
    print("  4. Watch real-time execution as each question is answered")
    print(f"  5. Results are saved to projects/{project_name}/output/results.json")
    print()
    print("Press Ctrl+C to stop the server")
    print()

    try:
        # Serve all workflows
        serve(
            entities=workflows,
            auto_open=True
        )
    except KeyboardInterrupt:
        print("\n\nShutting down DevUI...")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
