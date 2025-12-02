"""
Prism - Document Extraction and Knowledge Query Pipeline

This script provides a complete pipeline from document extraction to Azure AI Search indexing.

Usage:
    # Document Extraction
    python main.py process --project myproject    # Process all documents
    python main.py process --project myproject --test  # Test single document

    # RAG Pipeline
    python main.py deduplicate --project myproject    # Analyze and remove duplicates
    python main.py chunk --project myproject          # Chunk documents semantically
    python main.py embed --project myproject          # Generate embeddings
    python main.py index create --project myproject   # Create Azure AI Search index
    python main.py index upload --project myproject   # Upload to index

    # Agentic Retrieval Setup
    python main.py source create --project myproject  # Create knowledge source
    python main.py agent create --project myproject   # Create knowledge agent
    python main.py agent query --project myproject    # Launch interactive query interface

    # Workflows
    python main.py workflow --project myproject       # Launch workflows
    python main.py run section1 --project myproject   # Run Section 1 directly

    python main.py --help                             # Show help
"""

import sys
import os
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Load .env file first
load_dotenv()


def get_project_path(project_name: str) -> Path:
    """Get the path to a project directory."""
    return Path("projects") / project_name


def get_documents_path(project_name: str) -> Path:
    """Get the path to a project's documents directory."""
    return get_project_path(project_name) / "documents"


def get_output_path(project_name: str) -> Path:
    """Get the path to a project's output directory."""
    return get_project_path(project_name) / "output"


def list_projects() -> list:
    """List all available projects."""
    projects_dir = Path("projects")
    if not projects_dir.exists():
        return []
    return [p.name for p in projects_dir.iterdir()
            if p.is_dir() and not p.name.startswith('.')]


def main():
    """Main entry point with command routing."""
    # Get default project from environment or use first available
    default_project = os.getenv('PRISM_PROJECT_NAME', None)
    if not default_project:
        projects = list_projects()
        default_project = projects[0] if projects else '_example'

    parser = argparse.ArgumentParser(
        description="Prism - Document Extraction and Knowledge Query Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extraction
  python main.py process --project myproject       Process all documents
  python main.py process --project myproject --test  Test with single document

  # RAG Pipeline
  python main.py deduplicate --project myproject   Analyze duplicates
  python main.py chunk --project myproject         Chunk documents
  python main.py embed --project myproject         Generate embeddings
  python main.py index create --project myproject  Create search index
  python main.py index upload --project myproject  Upload to index

  # Agentic Retrieval Setup
  python main.py source create --project myproject  Create knowledge source
  python main.py agent create --project myproject   Create knowledge agent
  python main.py agent query --project myproject    Launch interactive query

  # Workflows
  python main.py workflow --project myproject       Launch workflows
  python main.py run section1 --project myproject   Run Section 1 directly

Workflow:
  1. Create project folder in projects/
  2. Add documents to projects/{name}/documents/
  3. Extract documents -> projects/{name}/output/extraction_results/
  4. Deduplicate -> projects/{name}/output/document_inventory.json
  5. Chunk -> projects/{name}/output/chunked_documents/
  6. Embed -> projects/{name}/output/embedded_documents/
  7. Create index -> Azure AI Search
  8. Upload -> Index populated
  9. Create knowledge source -> Wrapper for index
  10. Create knowledge agent -> Ready for agentic retrieval
  11. Query -> Interactive chat interface

Directory Structure:
  projects/
    myproject/
      config.json           # Project metadata
      documents/            # Input documents
      output/               # Pipeline outputs
      workflow_config.json  # Sections + questions
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Process command
    process_parser = subparsers.add_parser('process', help='Process documents to markdown')
    process_parser.add_argument('--test', action='store_true',
                               help='Test with single document')
    process_parser.add_argument('--project', type=str, default=default_project,
                               help=f'Project name (default: {default_project})')

    # Deduplicate command
    dedup_parser = subparsers.add_parser('deduplicate', help='Analyze and report document duplicates')
    dedup_parser.add_argument('--project', type=str, default=default_project,
                             help=f'Project name (default: {default_project})')

    # Chunk command
    chunk_parser = subparsers.add_parser('chunk', help='Chunk documents semantically for RAG')
    chunk_parser.add_argument('--project', type=str, default=default_project,
                             help=f'Project name (default: {default_project})')

    # Embed command
    embed_parser = subparsers.add_parser('embed', help='Generate embeddings for chunks')
    embed_parser.add_argument('--project', type=str, default=default_project,
                             help=f'Project name (default: {default_project})')

    # Index command with subcommands
    index_parser = subparsers.add_parser('index', help='Manage Azure AI Search index')
    index_subparsers = index_parser.add_subparsers(dest='index_command', help='Index operations')
    index_create_parser = index_subparsers.add_parser('create', help='Create search index')
    index_create_parser.add_argument('--project', type=str, default=default_project,
                                    help=f'Project name (default: {default_project})')
    index_upload_parser = index_subparsers.add_parser('upload', help='Upload documents to index')
    index_upload_parser.add_argument('--project', type=str, default=default_project,
                                    help=f'Project name (default: {default_project})')

    # Source command with subcommands
    source_parser = subparsers.add_parser('source', help='Manage knowledge source')
    source_subparsers = source_parser.add_subparsers(dest='source_command', help='Source operations')
    source_create_parser = source_subparsers.add_parser('create', help='Create knowledge source')
    source_create_parser.add_argument('--project', type=str, default=default_project,
                                     help=f'Project name (default: {default_project})')

    # Agent command with subcommands
    agent_parser = subparsers.add_parser('agent', help='Manage knowledge agent')
    agent_subparsers = agent_parser.add_subparsers(dest='agent_command', help='Agent operations')
    agent_create_parser = agent_subparsers.add_parser('create', help='Create knowledge agent')
    agent_create_parser.add_argument('--project', type=str, default=default_project,
                                    help=f'Project name (default: {default_project})')
    agent_query_parser = agent_subparsers.add_parser('query', help='Launch interactive query interface')
    agent_query_parser.add_argument('--project', type=str, default=default_project,
                                   help=f'Project name (default: {default_project})')

    # Workflow command
    workflow_parser = subparsers.add_parser('workflow', help='Launch workflows')
    workflow_parser.add_argument('--project', type=str, default=default_project,
                                help=f'Project name (default: {default_project})')

    # Run command - Run workflow sections directly without UI
    run_parser = subparsers.add_parser('run', help='Run workflow section directly (no UI)')
    run_parser.add_argument('section', type=str,
                           help='Section ID to run (from workflow_config.json)')
    run_parser.add_argument('--project', type=str, default=default_project,
                           help=f'Project name (default: {default_project})')
    run_parser.add_argument('--list', action='store_true',
                           help='List available sections for the project')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    # Route to appropriate script
    if args.command == 'process':
        # Set project in environment for backwards compatibility
        os.environ['PRISM_PROJECT_NAME'] = args.project
        print(f"Project: {args.project}")

        # Verify project exists
        docs_path = get_documents_path(args.project)
        if not docs_path.exists():
            print(f"ERROR: Project documents not found: {docs_path}")
            print(f"Create the project folder and add documents to: {docs_path}")
            return 1

        if args.test:
            print("Starting single document test...")
            from scripts.testing import test_single_document
            return test_single_document.main()
        else:
            print("Processing all documents...")
            from scripts.testing import process_all_documents
            return process_all_documents.main()

    elif args.command == 'deduplicate':
        os.environ['PRISM_PROJECT_NAME'] = args.project
        print(f"Project: {args.project}")
        print("Analyzing document duplicates...")
        from scripts.rag import deduplicate_documents
        return deduplicate_documents.main()

    elif args.command == 'chunk':
        os.environ['PRISM_PROJECT_NAME'] = args.project
        print(f"Project: {args.project}")
        print("Chunking documents...")
        from scripts.rag import chunk_documents
        return chunk_documents.main()

    elif args.command == 'embed':
        os.environ['PRISM_PROJECT_NAME'] = args.project
        print(f"Project: {args.project}")
        print("Generating embeddings...")
        from scripts.rag import generate_embeddings
        return generate_embeddings.main()

    elif args.command == 'index':
        if not args.index_command:
            index_parser.print_help()
            return 0

        if args.index_command == 'create':
            os.environ['PRISM_PROJECT_NAME'] = args.project
            print(f"Project: {args.project}")
            print("Creating Azure AI Search index...")
            from scripts.search_index import create_search_index
            return create_search_index.main()

        elif args.index_command == 'upload':
            os.environ['PRISM_PROJECT_NAME'] = args.project
            print(f"Project: {args.project}")
            print("Uploading documents to index...")
            from scripts.search_index import upload_to_search
            return upload_to_search.main()

    elif args.command == 'source':
        if not args.source_command:
            source_parser.print_help()
            return 0

        if args.source_command == 'create':
            os.environ['PRISM_PROJECT_NAME'] = args.project
            print(f"Project: {args.project}")
            print("Creating knowledge source...")
            from scripts.search_index import create_knowledge_source
            return create_knowledge_source.main()

    elif args.command == 'agent':
        if not args.agent_command:
            agent_parser.print_help()
            return 0

        if args.agent_command == 'create':
            os.environ['PRISM_PROJECT_NAME'] = args.project
            print(f"Project: {args.project}")
            print("Creating knowledge agent...")
            from scripts.search_index import create_knowledge_agent
            return create_knowledge_agent.main()

        elif args.agent_command == 'query':
            os.environ['PRISM_PROJECT_NAME'] = args.project
            print(f"Project: {args.project}")
            print("Launching interactive query interface...")
            from scripts.query import query_knowledge_agent
            return query_knowledge_agent.main()

    elif args.command == 'workflow':
        os.environ['PRISM_PROJECT_NAME'] = args.project
        print(f"Project: {args.project}")
        print("Launching workflows...")
        from workflows import run_workflows
        return run_workflows.main()

    elif args.command == 'run':
        os.environ['PRISM_PROJECT_NAME'] = args.project
        print(f"Project: {args.project}")

        import asyncio
        from workflows.workflow_agent import WorkflowAgentFactory, list_project_sections

        # Verify project exists
        project_path = get_project_path(args.project)
        if not project_path.exists():
            print(f"ERROR: Project not found: {project_path}")
            return 1

        # List sections if requested
        if hasattr(args, 'list') and args.list:
            print("\nAvailable sections:")
            try:
                sections = list_project_sections(args.project)
                if not sections:
                    print("  No sections configured. Edit workflow_config.json to add sections.")
                else:
                    for section in sections:
                        print(f"  - {section['id']}: {section['name']} ({section['question_count']} questions)")
            except Exception as e:
                print(f"  Error loading sections: {e}")
            return 0

        # Run the specified section
        section_id = args.section
        print(f"Running section '{section_id}' workflow directly...")

        try:
            # Create workflow factory and build workflow
            factory = WorkflowAgentFactory(args.project)
            section_info = factory.get_section_info(section_id)

            if not section_info:
                print(f"\nError: Section '{section_id}' not found in workflow_config.json")
                print("\nAvailable sections:")
                for s_id in factory.get_all_section_ids():
                    info = factory.get_section_info(s_id)
                    if info:
                        print(f"  - {s_id}: {info['name']} ({info['question_count']} questions)")
                return 1

            print(f"Section: {section_info['name']}")
            print(f"Questions: {section_info['question_count']}")
            print()

            workflow = factory.build_section_workflow(section_id)

            async def run():
                result = await workflow.run("Start workflow")
                print()
                print("Workflow completed!")
                output_file = get_output_path(args.project) / "results.json"
                print(f"Results saved to: {output_file}")
                return result

            asyncio.run(run())
            return 0

        except FileNotFoundError as e:
            print(f"Error: {e}")
            return 1
        except Exception as e:
            print(f"Error running workflow: {e}")
            import traceback
            traceback.print_exc()
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
