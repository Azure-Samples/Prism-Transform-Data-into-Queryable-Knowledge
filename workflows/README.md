# Prism Workflows

Automated document querying using Agent Framework + Azure AI Search.

## Overview

Workflows allow you to define structured question sets that are automatically
answered using the project's knowledge agent. Each project has its own
`workflow_config.json` defining sections and questions.

## Architecture

```
Workflow Config (JSON)
  ↓
WorkflowAgentFactory
  ↓
Section Workflow (per section)
  ↓
Question Agent (per question)
  ↓
Results (JSON)
```

## Configuration

Workflows are configured per-project in `workflow_config.json` (stored in Azure Blob Storage):

```json
{
  "sections": [
    {
      "id": "section1",
      "name": "Technical Specifications",
      "template": "Answer based on technical documents...",
      "questions": [
        {
          "id": "q1",
          "question": "What is the rated voltage?",
          "instructions": "Look in electrical specs"
        }
      ]
    }
  ]
}
```

## Usage

### Via Web UI

1. Go to **Workflows** in the navigation
2. Select your project
3. Choose a section to run
4. Click **Run Section**
5. View results when complete

## File Structure

```
workflows/
├── __init__.py           # Package init
├── README.md             # This file
├── workflow_agent.py     # Generic workflow factory
└── run_workflows.py      # CLI launcher
```

## Results

Results are saved to `output/results.json` in Azure Blob Storage:

```json
{
  "section1": {
    "q1": {
      "answer": "The rated voltage is 400kV...",
      "references": ["Document A, Page 5"],
      "timestamp": "2024-01-15T10:30:00Z"
    }
  }
}
```

## Agent Prompt Construction

At runtime, the agent prompt is constructed as:

```
Agent Prompt = Section Template + Question + Instructions
```

This allows per-section customization while maintaining consistent question structure.
