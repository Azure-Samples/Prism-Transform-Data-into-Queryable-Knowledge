"""
Generic Workflow Agent - Config-Driven Question Answering

This module creates workflow agents dynamically from workflow_config.json.
Each project has its own workflow configuration with sections and questions.

Architecture:
- Load workflow config from projects/{project}/workflow_config.json
- Each section has a template + list of questions with instructions
- Agent prompt = Section Template + Question + Instructions
- Sequential workflow: Q1 -> Save -> Q2 -> Save -> ... -> Complete

No hardcoded domain logic - fully user-configurable via UI.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv

# Agent Framework imports
from agent_framework import WorkflowBuilder, executor, WorkflowContext
from agent_framework.azure import AzureOpenAIChatClient
from agent_framework._workflows._agent_executor import AgentExecutorResponse

# Storage service
from apps.api.app.services.storage_service import get_storage_service

# Load environment
load_dotenv()

# Configuration
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
# Use workflow-specific deployment (gpt-5-chat) if available, fall back to chat deployment
AZURE_OPENAI_CHAT_DEPLOYMENT = os.getenv("AZURE_OPENAI_WORKFLOW_DEPLOYMENT_NAME") or os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME", "gpt-5-chat")


def load_workflow_config(project_name: str) -> Dict:
    """
    Load workflow configuration from blob storage.

    Args:
        project_name: Name of the project

    Returns:
        Workflow config dict with sections and questions
    """
    storage = get_storage_service()
    config = storage.read_json(project_name, "workflow_config.json")

    if not config:
        raise FileNotFoundError(f"Workflow config not found for project: {project_name}")

    return config


def get_search_tool(project_name: str):
    """
    Get the search tool for querying project documents.

    Args:
        project_name: Name of the project

    Returns:
        Search function configured for the project
    """
    # Import the search function - this uses the Azure AI Search index
    from scripts.query.query_knowledge_agent import search_documents
    return search_documents


class WorkflowAgentFactory:
    """
    Factory for creating workflow agents from configuration.

    This class dynamically creates agents and workflows based on
    the workflow_config.json for a project.
    """

    def __init__(self, project_name: str):
        """
        Initialize the factory for a specific project.

        Args:
            project_name: Name of the project
        """
        self.project_name = project_name
        self.config = load_workflow_config(project_name)
        self.storage = get_storage_service()

        # Initialize chat client
        self.chat_client = AzureOpenAIChatClient(
            api_key=AZURE_OPENAI_API_KEY,
            endpoint=AZURE_OPENAI_ENDPOINT,
            deployment_name=AZURE_OPENAI_CHAT_DEPLOYMENT,
            api_version=AZURE_OPENAI_API_VERSION
        )

        # Get search tool
        self.search_tool = get_search_tool(project_name)

    def _build_agent_instructions(self, section: Dict, question: Dict) -> str:
        """
        Build agent instructions by combining section template with question.

        The formula is: Section Template + Question + Instructions

        Args:
            section: Section dict with id, name, template
            question: Question dict with id, question, instructions

        Returns:
            Complete agent instructions string
        """
        template = section.get('template', '')
        question_text = question.get('question', '')
        instructions = question.get('instructions', '')

        # Build the full prompt
        prompt_parts = []

        # Section template (base instructions)
        if template:
            prompt_parts.append(template)

        # Question
        prompt_parts.append(f"\n\n**Question:** {question_text}")

        # Question-specific instructions
        if instructions:
            prompt_parts.append(f"\n\n**Additional Instructions:** {instructions}")

        # Output format instructions
        prompt_parts.append("""

**CRITICAL: IMMEDIATE ACTION REQUIRED**
You MUST immediately search for and answer the question above. Do NOT wait for additional input.
Do NOT respond with greetings, acknowledgments, or "how can I help" messages.
Start by calling the search tool, then provide your answer.

**Response Format:**
Please provide your answer in the following format:

Answer: [Your direct answer - could be Yes, No, N/A, or a specific value/quantity]

Reference: [Use the document names and page/location info from the === SOURCE DOCUMENTS === section. Format as: "Document Name (Page N)" or "Document Name (Location)". Do NOT use raw chunk IDs like "ec9320d9_chunk_005" - always use human-readable document names and locations.]

Comments: [Any additional context, technical details, or important notes]

**Important:**
- Use the search tool to find relevant information in the documents
- Be precise and cite specific sources using document names and page numbers from the SOURCE DOCUMENTS section
- NEVER cite chunk IDs (e.g., "Chunk: abc123_chunk_001") - always use the document filename and location
- If information is not found, state "N/A" and explain what you searched for
- Self-validate your answer by searching for contradicting information
""")

        return '\n'.join(prompt_parts)

    def create_question_agent(self, section: Dict, question: Dict):
        """
        Create an agent for a specific question.

        Args:
            section: Section dict
            question: Question dict

        Returns:
            Configured agent executor
        """
        section_id = section.get('id', 'unknown')
        question_id = question.get('id', 'unknown')
        question_text = question.get('question', 'Unknown question')

        # Build instructions
        instructions = self._build_agent_instructions(section, question)

        # Create safe agent name
        safe_name = f"Section_{section_id}_Q_{question_id}"
        safe_name = safe_name.replace(' ', '_').replace('/', '_').replace('-', '_')

        # Create agent
        agent = self.chat_client.create_agent(
            name=safe_name,
            instructions=instructions,
            tools=[self.search_tool]
        )

        # Add logging wrapper
        from agent_framework._workflows._agent_executor import AgentExecutor
        if isinstance(agent, AgentExecutor):
            original_call = agent.__call__

            async def logged_call(message, ctx):
                print(f"\n[AGENT] ===== STARTING {section_id}/{question_id} =====")
                print(f"[AGENT] Question: {question_text[:100]}...")
                print(f"[AGENT] Executing agent...")
                try:
                    result = await original_call(message, ctx)
                    print(f"[AGENT] Agent execution completed for {section_id}/{question_id}")
                    return result
                except Exception as e:
                    import traceback
                    print(f"\n[AGENT] ===== AGENT FAILED: {section_id}/{question_id} =====")
                    print(f"[AGENT] Error: {e}")
                    print(traceback.format_exc())
                    raise

            agent.__call__ = logged_call

        return agent

    def create_question_saver(self, section: Dict, question: Dict, question_index: int):
        """
        Create a saver executor that saves the answer immediately after generation.

        Args:
            section: Section dict
            question: Question dict
            question_index: Index of the question in the section

        Returns:
            Saver executor
        """
        section_id = section.get('id', 'unknown')
        section_name = section.get('name', 'Unknown Section')
        question_id = question.get('id', 'unknown')
        question_text = question.get('question', '')

        # Capture storage and project_name for closure
        storage = self.storage
        project_name = self.project_name

        @executor(id=f"saver_{section_id}_{question_id}")
        async def question_saver(agent_response: AgentExecutorResponse, ctx: WorkflowContext) -> None:
            """Save this question's answer to results file."""

            print(f"\n[SAVER] Processing response for {section_id}/{question_id}...")

            # Extract response text
            if hasattr(agent_response, 'agent_run_response'):
                response_text = agent_response.agent_run_response.text
            else:
                response_text = str(agent_response)

            # Parse Answer/Reference/Comments
            answer = "N/A"
            reference = ""
            comments = ""

            lines = response_text.split('\n')
            current_section = None

            for line in lines:
                line_stripped = line.strip()
                if line_stripped.startswith('Answer:'):
                    current_section = 'answer'
                    answer = line_stripped.replace('Answer:', '').strip()
                elif line_stripped.startswith('Reference:'):
                    current_section = 'reference'
                    reference = line_stripped.replace('Reference:', '').strip()
                elif line_stripped.startswith('Comments:'):
                    current_section = 'comments'
                    comments = line_stripped.replace('Comments:', '').strip()
                elif current_section and line_stripped:
                    if current_section == 'reference':
                        reference += ' ' + line_stripped
                    elif current_section == 'comments':
                        comments += ' ' + line_stripped

            # Load existing results from blob storage or create new
            results = storage.read_json(project_name, "output/results.json")
            if not results:
                results = {"sections": {}}

            # Ensure section exists in results
            if section_id not in results["sections"]:
                results["sections"][section_id] = {
                    "name": section_name,
                    "questions": {}
                }

            # Save question result
            results["sections"][section_id]["questions"][question_id] = {
                "question": question_text,
                "answer": answer,
                "reference": reference,
                "comments": comments,
                "raw_response": response_text
            }

            # Write back to blob storage
            storage.write_json(project_name, "output/results.json", results)

            print(f"[SAVER] Saved {section_id}/{question_id}: {answer[:50]}...")

            # Run evaluation on the answer (async-safe, non-blocking for UI)
            try:
                from scripts.evaluation.evaluate_results import evaluate_single_answer
                print(f"[EVAL] Evaluating {section_id}/{question_id}...")

                eval_result = evaluate_single_answer(
                    query=question_text,
                    response=answer,
                    context=response_text,
                    comments=comments
                )

                # Re-read results to avoid race conditions
                results = storage.read_json(project_name, "output/results.json")
                if results and section_id in results.get("sections", {}):
                    results["sections"][section_id]["questions"][question_id]["evaluation"] = eval_result
                    storage.write_json(project_name, "output/results.json", results)

                avg_score = eval_result.get("average_score", "N/A")
                print(f"[EVAL] {section_id}/{question_id} average score: {avg_score}")
            except Exception as e:
                print(f"[EVAL] Evaluation failed for {section_id}/{question_id}: {e}")
                # Don't fail the workflow if evaluation fails - continue to next question

            await ctx.send_message(f"Saved {section_id}/{question_id}")

        return question_saver

    def build_section_workflow(self, section_id: str):
        """
        Build a workflow for a specific section.

        Args:
            section_id: ID of the section to build workflow for

        Returns:
            Workflow object
        """
        # Find section in config
        section = None
        for s in self.config.get('sections', []):
            if s.get('id') == section_id:
                section = s
                break

        if not section:
            raise ValueError(f"Section not found: {section_id}")

        section_name = section.get('name', 'Unknown Section')
        questions = section.get('questions', [])

        if not questions:
            raise ValueError(f"Section {section_id} has no questions")

        print(f"[WORKFLOW] Building workflow for section: {section_name}")
        print(f"[WORKFLOW] Questions: {len(questions)}")

        # Create agents and savers for each question
        agents = []
        savers = []

        for i, question in enumerate(questions):
            agent = self.create_question_agent(section, question)
            saver = self.create_question_saver(section, question, i)
            agents.append(agent)
            savers.append(saver)
            print(f"  Created Q{i+1}: {question.get('question', '')[:50]}...")

        # Create completion executor
        @executor(id=f"completion_{section_id}")
        async def completion_executor(message: str, ctx: WorkflowContext) -> None:
            """Final step: Output completion message."""
            completion_msg = f"""
{'='*80}
SECTION COMPLETE: {section_name}
{'='*80}
All {len(questions)} questions have been answered and saved.

Results saved to blob storage: {self.project_name}/output/results.json
"""
            await ctx.yield_output(completion_msg)

        # Build workflow
        builder = WorkflowBuilder(
            name=f"{section_name}",
            description=f"Answers {len(questions)} questions for {section_name}"
        )

        # Set first agent as start
        builder.set_start_executor(agents[0])

        # Chain: Q1 -> Saver1 -> Q2 -> Saver2 -> ... -> Completion
        for i in range(len(agents)):
            builder.add_edge(agents[i], savers[i])

            if i < len(agents) - 1:
                builder.add_edge(savers[i], agents[i + 1])
            else:
                builder.add_edge(savers[i], completion_executor)

        workflow = builder.build()

        print(f"[WORKFLOW] Workflow built successfully for {section_name}")

        return workflow

    def get_all_section_ids(self) -> List[str]:
        """Get list of all section IDs in the config."""
        return [s.get('id') for s in self.config.get('sections', [])]

    def get_section_info(self, section_id: str) -> Optional[Dict]:
        """Get info about a specific section."""
        for s in self.config.get('sections', []):
            if s.get('id') == section_id:
                return {
                    'id': s.get('id'),
                    'name': s.get('name'),
                    'question_count': len(s.get('questions', []))
                }
        return None


def create_workflow_for_project(project_name: str, section_id: str):
    """
    Convenience function to create a workflow for a project section.

    Args:
        project_name: Name of the project
        section_id: ID of the section

    Returns:
        Workflow object ready to run
    """
    factory = WorkflowAgentFactory(project_name)
    return factory.build_section_workflow(section_id)


def list_project_sections(project_name: str) -> List[Dict]:
    """
    List all sections configured for a project.

    Args:
        project_name: Name of the project

    Returns:
        List of section info dicts
    """
    factory = WorkflowAgentFactory(project_name)
    sections = []

    for section_id in factory.get_all_section_ids():
        info = factory.get_section_info(section_id)
        if info:
            sections.append(info)

    return sections


# For backward compatibility with DevUI
def get_workflows_for_project(project_name: str) -> Dict[str, Any]:
    """
    Get all workflows for a project (for DevUI serving).

    Args:
        project_name: Name of the project

    Returns:
        Dict mapping section_id to workflow
    """
    factory = WorkflowAgentFactory(project_name)
    workflows = {}

    for section_id in factory.get_all_section_ids():
        try:
            workflow = factory.build_section_workflow(section_id)
            workflows[section_id] = workflow
        except Exception as e:
            print(f"Warning: Could not build workflow for {section_id}: {e}")

    return workflows
