"""
Runbook Loader
Loads and manages agent runbooks from JSON files.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class Runbook:
    agent: str
    description: str
    objectives: list
    triage_steps: list
    common_failures: list
    escalation_rules: list
    raw_data: Dict[str, Any]


class RunbookManager:
    def __init__(self, runbooks_dir: str = "runbooks"):
        self.runbooks_dir = Path(runbooks_dir)
        self._cache: Dict[str, Runbook] = {}

    def load_runbook(self, agent_name: str) -> Optional[Runbook]:
        """Load a runbook for a specific agent."""
        # Normalize name
        filename = f"{agent_name.lower().replace('agent', '_agent')}.json"
        if not filename.startswith(agent_name.lower()[:3]):
            filename = f"{agent_name.lower()}_agent.json"
        
        # Try different name patterns
        possible_files = [
            self.runbooks_dir / f"{agent_name.lower()}.json",
            self.runbooks_dir / f"{agent_name.lower().replace('agent', '_agent')}.json",
            self.runbooks_dir / f"{agent_name.lower().replace('Agent', '')}_agent.json",
        ]
        
        for filepath in possible_files:
            if filepath.exists():
                return self._load_from_file(filepath)
        
        # Try to find by agent field
        for filepath in self.runbooks_dir.glob("*.json"):
            with open(filepath, "r") as f:
                data = json.load(f)
                if data.get("agent", "").lower() == agent_name.lower():
                    return self._parse_runbook(data)
        
        return None

    def _load_from_file(self, filepath: Path) -> Runbook:
        with open(filepath, "r") as f:
            data = json.load(f)
        return self._parse_runbook(data)

    def _parse_runbook(self, data: Dict[str, Any]) -> Runbook:
        return Runbook(
            agent=data.get("agent", "Unknown"),
            description=data.get("description", ""),
            objectives=data.get("objectives", []),
            triage_steps=data.get("triage_steps", []),
            common_failures=data.get("common_failures", []),
            escalation_rules=data.get("escalation_rules", []),
            raw_data=data
        )

    def get_all_runbooks(self) -> Dict[str, Runbook]:
        """Load all runbooks from the directory."""
        runbooks = {}
        for filepath in self.runbooks_dir.glob("*.json"):
            try:
                rb = self._load_from_file(filepath)
                runbooks[rb.agent] = rb
            except Exception:
                pass
        return runbooks

    def update_runbook(self, agent_name: str, updates: Dict[str, Any]) -> bool:
        """Update a runbook (for live editing from UI)."""
        for filepath in self.runbooks_dir.glob("*.json"):
            with open(filepath, "r") as f:
                data = json.load(f)
            if data.get("agent", "").lower() == agent_name.lower():
                data.update(updates)
                with open(filepath, "w") as f:
                    json.dump(data, f, indent=2)
                return True
        return False


# Singleton
_manager: Optional[RunbookManager] = None


def get_runbook_manager() -> RunbookManager:
    global _manager
    if _manager is None:
        _manager = RunbookManager()
    return _manager
