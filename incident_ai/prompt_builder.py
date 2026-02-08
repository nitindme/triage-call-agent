"""
LLaMA Prompt Builder
Generates prompts for agents based on runbooks and context.
"""

from typing import Dict, Any, List, Optional
from .runbook_loader import Runbook


class PromptBuilder:
    """Builds prompts for LLaMA-based agents."""

    BASE_SYSTEM_PROMPT = """You are {agent_name}, an AI agent participating in a live production incident.

You must:
- Follow your runbook precisely
- Use logs and evidence to support conclusions
- Speak concisely and professionally
- Escalate when your runbook requires it
- Avoid speculation without data
- Collaborate with other agents respectfully

Your role: {description}

Your objectives:
{objectives}

Your triage steps:
{triage_steps}

Known failure patterns:
{failure_patterns}

Escalation rules:
{escalation_rules}
"""

    @classmethod
    def build_agent_prompt(cls, runbook: Runbook) -> str:
        """Build a system prompt for an agent from their runbook."""
        objectives = "\n".join(f"- {obj}" for obj in runbook.objectives)
        triage_steps = "\n".join(f"{i+1}. {step}" for i, step in enumerate(runbook.triage_steps))
        
        failures = []
        for f in runbook.common_failures[:5]:
            if isinstance(f, dict):
                failures.append(f"- {f.get('code', 'N/A')}: {f.get('description', '')}")
            else:
                failures.append(f"- {f}")
        failure_patterns = "\n".join(failures) if failures else "- No known patterns"
        
        escalations = []
        for e in runbook.escalation_rules[:5]:
            if isinstance(e, dict):
                escalations.append(f"- If {e.get('condition', 'N/A')} → escalate to {e.get('escalate_to', 'N/A')}")
            else:
                escalations.append(f"- {e}")
        escalation_rules = "\n".join(escalations) if escalations else "- No escalation rules"

        return cls.BASE_SYSTEM_PROMPT.format(
            agent_name=runbook.agent,
            description=runbook.description,
            objectives=objectives,
            triage_steps=triage_steps,
            failure_patterns=failure_patterns,
            escalation_rules=escalation_rules
        )

    @classmethod
    def build_analysis_prompt(
        cls,
        runbook: Runbook,
        logs: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build a prompt for analyzing logs and incidents."""
        log_snippet = "\n".join(logs[-20:]) if logs else "No logs available"
        
        prompt = f"""Analyze the following incident:

Recent logs:
```
{log_snippet}
```

Based on your runbook and the logs above:
1. What patterns do you see?
2. Which of your known failure modes matches?
3. What is your hypothesis?
4. Who should you escalate to (if any)?
5. What is your recommended action?

Respond concisely and professionally."""
        
        if context:
            prompt += f"\n\nAdditional context: {context}"
        
        return prompt

    @classmethod
    def build_fix_prompt(cls, runbook: Runbook, diagnosis: str, file_content: str) -> str:
        """Build a prompt for generating a code fix."""
        return f"""Based on the diagnosis:
{diagnosis}

And the current code:
```
{file_content}
```

Generate the minimal fix required. Show only the corrected code."""


def build_agent_prompt(runbook: Runbook) -> str:
    """Convenience function."""
    return PromptBuilder.build_agent_prompt(runbook)


def build_analysis_prompt(runbook: Runbook, logs: List[str], context: Optional[Dict[str, Any]] = None) -> str:
    """Convenience function."""
    return PromptBuilder.build_analysis_prompt(runbook, logs, context)
