"""
AI Agents (v2)
Intelligent agents that use runbooks and dynamic failure injection.
"""

import asyncio
import difflib
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.random_failure import get_failure_injector, FailureMode


def now_ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


@dataclass
class Message:
    agent: str
    text: str
    timestamp: str
    message_type: str = "speech"  # speech, code, log, system
    extra: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.agent,
            "text": self.text,
            "timestamp": self.timestamp,
            "message_type": self.message_type,
            "extra": self.extra
        }


class BaseAgent:
    """Base class for all AI agents."""
    
    def __init__(self, name: str, delay: float = 1.5):
        self.name = name
        self.delay = delay

    async def speak(self, text: str, msg_type: str = "speech", extra: Optional[Dict] = None) -> Message:
        """Generate a message with realistic delay."""
        await asyncio.sleep(self.delay)
        return Message(
            agent=self.name,
            text=text,
            timestamp=now_ts(),
            message_type=msg_type,
            extra=extra
        )


class ChairAgent(BaseAgent):
    """AI Incident Commander - runs the triage call."""
    
    def __init__(self, delay: float = 1.5):
        super().__init__("ChairAgent", delay)

    async def open_call(self, ticket) -> Message:
        injector = get_failure_injector()
        failure = injector.get_current_failure()
        symptoms = failure.symptoms if failure else ["Unknown error pattern"]
        
        return await self.speak(
            f"🚨 **Opening triage for {ticket['id']}**\n"
            f"**Severity:** {ticket['severity']}\n"
            f"**Summary:** {ticket['summary']}\n"
            f"**First detected:** {ticket['first_detected']}\n"
            f"**Symptoms:** {symptoms[0]}"
        )

    async def request_assessment(self) -> Message:
        return await self.speak(
            "📋 MainAgent, please provide your initial assessment based on available signals."
        )

    async def request_deploys(self) -> Message:
        return await self.speak(
            "🔍 SREAgent, what are the recent deployments and any similar past incidents?"
        )

    async def route_to_experts(self, services: List[str]) -> Message:
        agents = ", ".join(f"{s.title()}Agent" for s in services)
        return await self.speak(
            f"📌 Routing to domain experts: {agents}. Please analyze the logs and provide your findings."
        )

    async def request_fix(self) -> Message:
        return await self.speak(
            "🔧 FrontendAgent, please inspect the code and propose a fix."
        )

    async def confirm_fix(self) -> Message:
        return await self.speak(
            "✅ Fix has been applied and deployed. Moving to monitoring phase."
        )

    async def close_call(self) -> Message:
        return await self.speak(
            "📝 **Closing triage call.** Actions assigned and RCA to follow.\n"
            "Thank you all for the rapid response."
        )


class MainAgent(BaseAgent):
    """Initial analysis and routing agent."""
    
    def __init__(self, delay: float = 2.0):
        super().__init__("MainAgent", delay)

    async def initial_assessment(self, logs: List[str]) -> Tuple[Message, List[str]]:
        injector = get_failure_injector()
        failure = injector.get_current_failure()
        
        affected_services = [failure.service] if failure else ["frontend"]
        
        analysis = f"**Initial Assessment:**\n"
        analysis += f"- Analyzed {len(logs)} log entries\n"
        analysis += f"- Primary error pattern: `{failure.error_code}` - {failure.message}\n" if failure else ""
        analysis += f"- **Affected service:** {failure.service.title()}\n" if failure else ""
        analysis += f"- **Error type:** {failure.error_type.replace('_', ' ').title()}\n" if failure else ""
        analysis += f"\n**Hypothesis:** {failure.root_cause[:100]}..." if failure else ""
        
        return await self.speak(analysis), affected_services


class SREAgent(BaseAgent):
    """Infrastructure, deployments, and observability agent."""
    
    def __init__(self, delay: float = 1.8):
        super().__init__("SREAgent", delay)

    async def recent_deploys(self) -> Message:
        deploys = [
            ("backend/orders", "v1.3.2", "2026-02-08 13:58:00", "Added validation rules"),
            ("frontend", "v2.8.0", "2026-02-08 13:55:00", "Checkout flow update"),
            ("billing", "v4.1.0", "2026-02-07 09:30:00", "Stripe SDK upgrade"),
        ]
        
        text = "**Recent Deployments:**\n"
        for service, version, time, note in deploys:
            text += f"- `{service}` {version} ({time}) — {note}\n"
        
        text += "\n**⚠️ Note:** Backend deployed AFTER frontend — possible contract mismatch."
        
        return await self.speak(text)

    async def past_incidents(self) -> Message:
        text = "**Similar Past Incidents:**\n"
        text += "- INC-2026-015: API contract mismatch after backend deploy\n"
        text += "- INC-2026-012: Frontend/backend version skew\n"
        return await self.speak(text)

    async def provide_logs(self, count: int = 30) -> List[str]:
        """Generate realistic logs for current failure."""
        injector = get_failure_injector()
        return injector.generate_logs(count)


class BillingAgent(BaseAgent):
    """Billing and payment domain expert."""
    
    def __init__(self, delay: float = 2.0):
        super().__init__("BillingAgent", delay)

    async def analyze(self, logs: List[str]) -> Message:
        injector = get_failure_injector()
        failure = injector.get_current_failure()
        
        relevant_logs = [l for l in logs if "billing" in l.lower() or "ERROR" in l]
        
        text = "**Billing Analysis:**\n"
        text += f"- Found {len(relevant_logs)} relevant log entries\n\n"
        
        if failure and failure.service == "billing":
            text += f"**Root Cause Identified:**\n"
            text += f"Error: `{failure.error_code}` - {failure.message}\n\n"
            text += f"**Analysis:** {failure.root_cause}\n\n"
            text += f"**Evidence:**\n```\n{relevant_logs[0] if relevant_logs else 'See logs above'}\n```\n\n"
            text += "**Recommendation:** Escalate to FrontendAgent for code fix."
        else:
            text += "No billing-specific root cause found. Deferring to other agents."
        
        return await self.speak(text)


class OrderingAgent(BaseAgent):
    """Order processing domain expert."""
    
    def __init__(self, delay: float = 2.0):
        super().__init__("OrderingAgent", delay)

    async def analyze(self, logs: List[str]) -> Message:
        injector = get_failure_injector()
        failure = injector.get_current_failure()
        
        text = "**Ordering Analysis:**\n"
        
        if failure and failure.service == "ordering":
            text += f"**Root Cause Identified:**\n"
            text += f"Error: `{failure.error_code}` - {failure.message}\n\n"
            text += f"**Analysis:** {failure.root_cause}\n\n"
            text += "**Recommendation:** Escalate to FrontendAgent for code fix."
        else:
            text += "Order processing pipeline appears healthy.\n"
            text += "Issue is upstream — likely billing/frontend layer."
        
        return await self.speak(text)


class FrontendAgent(BaseAgent):
    """Frontend code and deployment agent."""
    
    def __init__(self, delay: float = 2.0):
        super().__init__("FrontendAgent", delay)

    async def inspect_code(self, demo_frontend_path: str = "demo_frontend") -> Tuple[Message, Optional[str], Optional[Tuple[str, str]]]:
        """Inspect frontend code for issues."""
        injector = get_failure_injector()
        failure = injector.get_current_failure()
        
        if not failure:
            return await self.speak("⚠️ No failure context available."), None, None
        
        path = Path(demo_frontend_path) / "checkout.ts"
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                orig = f.read()
        except FileNotFoundError:
            return await self.speak("⚠️ Could not locate checkout.ts file."), None, None

        # Get the fix for current failure
        fixed_code = failure.fix_code.get("checkout.ts", "")
        
        if not fixed_code or orig == fixed_code:
            return await self.speak("✅ Frontend code looks correct."), orig, None

        # Found the bug!
        text = "**Code Inspection Results:**\n"
        text += f"❌ **Bug Found:** {failure.fix_description}\n\n"
        text += f"**Error:** `{failure.error_code}` - {failure.message}\n\n"
        text += "**Fix Required:** See proposed patch below."
        
        diff = self._generate_diff(orig, fixed_code)
        
        return await self.speak(text), orig, (fixed_code, diff)

    def _generate_diff(self, original: str, fixed: str) -> str:
        """Generate a unified diff."""
        orig_lines = original.splitlines(keepends=True)
        fixed_lines = fixed.splitlines(keepends=True)
        diff = difflib.unified_diff(
            orig_lines, fixed_lines,
            fromfile="checkout.ts (before)",
            tofile="checkout.ts (after)"
        )
        return "".join(diff)

    async def show_diff(self, diff: str) -> Message:
        return await self.speak(
            f"**Proposed Fix (diff):**\n```diff\n{diff}\n```",
            msg_type="code"
        )

    async def apply_fix(self, demo_frontend_path: str, fixed_content: str) -> Message:
        """Apply the fix to the file."""
        path = Path(demo_frontend_path) / "checkout.ts"
        with open(path, "w", encoding="utf-8") as f:
            f.write(fixed_content)
        return await self.speak("✅ Fix applied to `checkout.ts`")

    async def simulate_deploy(self) -> Message:
        """Simulate Vercel deployment."""
        await asyncio.sleep(1.0)
        
        text = "**Vercel Deployment:**\n"
        text += "```\n"
        text += "▶ Building project...\n"
        text += "✓ Compiled successfully in 8.2s\n"
        text += "▶ Running tests...\n"
        text += "✓ All tests passed\n"
        text += "▶ Deploying to production...\n"
        text += "✓ Production: https://demo-checkout.vercel.app\n"
        text += "✓ Deployment complete!\n"
        text += "```"
        
        return await self.speak(text, msg_type="code")


@dataclass
class RCA:
    """Root Cause Analysis."""
    what_happened: str
    why_it_happened: str
    why_not_caught: str
    customer_impact: str
    fix_applied: str
    preventive_actions: List[str]
    timeline: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "what_happened": self.what_happened,
            "why_it_happened": self.why_it_happened,
            "why_not_caught": self.why_not_caught,
            "customer_impact": self.customer_impact,
            "fix_applied": self.fix_applied,
            "preventive_actions": self.preventive_actions,
            "timeline": self.timeline
        }

    def format_markdown(self) -> str:
        text = "# 📋 Root Cause Analysis\n\n"
        text += f"## What Happened\n{self.what_happened}\n\n"
        text += f"## Why It Happened\n{self.why_it_happened}\n\n"
        text += f"## Why It Wasn't Caught\n{self.why_not_caught}\n\n"
        text += f"## Customer Impact\n{self.customer_impact}\n\n"
        text += f"## Fix Applied\n{self.fix_applied}\n\n"
        text += "## Preventive Actions\n"
        for action in self.preventive_actions:
            text += f"- {action}\n"
        text += "\n## Timeline\n"
        for event in self.timeline:
            text += f"- {event}\n"
        return text
    
    @classmethod
    def from_failure(cls, failure: FailureMode) -> "RCA":
        """Generate RCA from a failure mode."""
        return cls(
            what_happened=f"Frontend code issue caused {failure.error_code} errors on {failure.service} service.",
            why_it_happened=failure.root_cause,
            why_not_caught="No contract tests between frontend and backend. No end-to-end tests validating API payloads in CI.",
            customer_impact="Users unable to complete checkout. Orders failing with errors. Estimated revenue impact during outage.",
            fix_applied=failure.fix_description,
            preventive_actions=[
                "Add contract tests between frontend and backend for critical APIs",
                "Add end-to-end CI scenarios for payment flows",
                f"Add monitoring alert for {failure.error_code} errors",
                "Implement API versioning to prevent breaking changes"
            ],
            timeline=[
                "14:02 - Alert triggered: High error rate detected",
                "14:03 - Ticket auto-created",
                "14:04 - AI triage call opened",
                "14:08 - Root cause identified",
                "14:10 - Fix applied and deployed",
                "14:12 - Error rate normalized",
                "14:15 - Triage call closed"
            ]
        )
