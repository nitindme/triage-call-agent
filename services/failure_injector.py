"""
Failure Injection Engine
Randomly injects failures based on policy configuration.
No hardcoded scenarios - every demo is unique.
"""

import json
import random
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class FailureMode:
    id: str
    service: str
    type: str
    error_code: str
    message: str
    probability: float
    fix_hint: str


@dataclass
class ActiveFailure:
    failure: FailureMode
    triggered_at: datetime
    trace_id: str


class FailureInjector:
    def __init__(self, policy_path: str = "services/failure_policy.json"):
        self.policy_path = Path(policy_path)
        self.policy = self._load_policy()
        self.active_failures: List[ActiveFailure] = []
        self._failure_modes = self._parse_failure_modes()

    def _load_policy(self) -> Dict[str, Any]:
        if self.policy_path.exists():
            with open(self.policy_path, "r") as f:
                return json.load(f)
        return {"enabled": False, "failure_modes": []}

    def _parse_failure_modes(self) -> List[FailureMode]:
        modes = []
        for fm in self.policy.get("failure_modes", []):
            modes.append(FailureMode(
                id=fm["id"],
                service=fm["service"],
                type=fm["type"],
                error_code=fm["error_code"],
                message=fm["message"],
                probability=fm["probability"],
                fix_hint=fm["fix_hint"]
            ))
        return modes

    def is_enabled(self) -> bool:
        return self.policy.get("enabled", False)

    def should_fail(self, service: str) -> Optional[FailureMode]:
        """Check if a service call should fail based on probability."""
        if not self.is_enabled():
            return None

        max_failures = self.policy.get("global_settings", {}).get("max_simultaneous_failures", 2)
        if len(self.active_failures) >= max_failures:
            return None

        applicable = [fm for fm in self._failure_modes if fm.service == service]
        for fm in applicable:
            if random.random() < fm.probability:
                return fm
        return None

    def trigger_failure(self, service: str, trace_id: str) -> Optional[ActiveFailure]:
        """Attempt to trigger a failure for a service."""
        failure_mode = self.should_fail(service)
        if failure_mode:
            active = ActiveFailure(
                failure=failure_mode,
                triggered_at=datetime.now(),
                trace_id=trace_id
            )
            self.active_failures.append(active)
            return active
        return None

    def trigger_specific_failure(self, failure_id: str, trace_id: str) -> Optional[ActiveFailure]:
        """Trigger a specific failure by ID (for demos)."""
        for fm in self._failure_modes:
            if fm.id == failure_id:
                active = ActiveFailure(
                    failure=fm,
                    triggered_at=datetime.now(),
                    trace_id=trace_id
                )
                self.active_failures.append(active)
                return active
        return None

    def get_active_failures(self) -> List[ActiveFailure]:
        return self.active_failures.copy()

    def clear_failures(self):
        self.active_failures = []

    def get_random_failure(self) -> Optional[FailureMode]:
        """Pick a random failure mode for demo purposes."""
        if not self._failure_modes:
            return None
        return random.choice(self._failure_modes)


# Singleton instance
_injector: Optional[FailureInjector] = None


def get_injector() -> FailureInjector:
    global _injector
    if _injector is None:
        _injector = FailureInjector()
    return _injector
