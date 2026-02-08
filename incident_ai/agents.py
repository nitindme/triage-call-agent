"""
AI Agents
Intelligent agents that use runbooks and LLaMA prompts for incident triage.
"""

import asyncio
import difflib
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from .runbook_loader import get_runbook_manager, Runbook
from .prompt_builder import build_agent_prompt, build_analysis_prompt


def now_ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


@dataclass
class Message:
    agent: str
    text: str
    timestamp: str
    message_type: str = "speech"  # speech, code, log, system
    extra: Optional[Dict[str, Any]] = None


class BaseAgent:
    """Base class for all AI agents."""
    
    def __init__(self, name: str, delay: float = 1.5):
        self.name = name
        self.delay = delay
        self.runbook: Optional[Runbook] = None
        self._load_runbook()

    def _load_runbook(self):
        manager = get_runbook_manager()
        self.runbook = manager.load_runbook(self.name)

    def get_prompt(self) -> str:
        """Get the LLaMA system prompt for this agent."""
        if self.runbook:
            return build_agent_prompt(self.runbook)
        return f"You are {self.name}, an AI agent in an incident triage."

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
        return await self.speak(
            f"🚨 **Opening triage for {ticket.id}**\n"
            f"**Severity:** {ticket.severity}\n"
            f"**Summary:** {ticket.summary}\n"
            f"**First detected:** {ticket.first_detected}\n"
            f"**Symptoms:** {', '.join(ticket.symptoms[:3])}"
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
        # Analyze logs for patterns
        billing_signals = any("currency" in l or "Stripe" in l or "BILLING" in l for l in logs)
        ordering_signals = any("ORDER" in l or "inventory" in l for l in logs)
        
        affected_services = []
        if billing_signals:
            affected_services.append("billing")
        if ordering_signals:
            affected_services.append("ordering")
        if not affected_services:
            affected_services = ["frontend"]

        analysis = f"**Initial Assessment:**\n"
        analysis += f"- Analyzed {len(logs)} log entries\n"
        analysis += f"- Error patterns detected: "
        
        if billing_signals:
            analysis += "payment/billing validation failures, "
        if ordering_signals:
            analysis += "order processing issues, "
        analysis = analysis.rstrip(", ")
        
        analysis += f"\n- **Hypothesis:** API contract mismatch between frontend and backend\n"
        analysis += f"- **Recommended routing:** {', '.join(s.title() + 'Agent' for s in affected_services)}"
        
        return await self.speak(analysis), affected_services


class SREAgent(BaseAgent):
    """Infrastructure, deployments, and observability agent."""
    
    def __init__(self, delay: float = 1.8):
        super().__init__("SREAgent", delay)

    async def recent_deploys(self) -> Message:
        deploys = [
            ("backend/orders", "v1.3.2", "2026-02-08 13:58:00", "Added currency validation"),
            ("frontend", "v2.8.0", "2026-02-08 13:55:00", "Checkout flow refactor"),
            ("billing", "v4.1.0", "2026-02-07 09:30:00", "Stripe SDK upgrade"),
        ]
        
        text = "**Recent Deployments:**\n"
        for service, version, time, note in deploys:
            text += f"- `{service}` {version} ({time}) — {note}\n"
        
        text += "\n**⚠️ Note:** Backend added currency validation AFTER frontend deploy. Possible contract mismatch."
        
        return await self.speak(text)

    async def past_incidents(self) -> Message:
        text = "**Similar Past Incidents:**\n"
        text += "- INC-2026-015: Currency validation added without frontend update (resolved in 23 min)\n"
        text += "- INC-2026-012: Inventory lock deadlock during flash sale\n"
        text += "\n*Recommend checking if current issue matches INC-2026-015 pattern.*"
        return await self.speak(text)

    async def provide_logs(self, count: int = 30) -> List[str]:
        """Generate realistic logs."""
        import random
        logs = []
        for i in range(count):
            ts = f"2026-02-08T14:{i:02d}:00"
            if i % 5 == 0:
                logs.append(f"{ts} ERROR [billing] POST /api/create-order 400 - validation failed: missing field 'currency'")
            elif i % 7 == 0:
                logs.append(f"{ts} ERROR [billing] Stripe: PaymentIntent requires currency - received null")
            elif i % 11 == 0:
                logs.append(f"{ts} WARN [ordering] inventory lock contention for sku=SKU1234")
            else:
                logs.append(f"{ts} INFO [{random.choice(['frontend', 'gateway', 'auth'])}] Request processed successfully")
        return logs


class BillingAgent(BaseAgent):
    """Billing and payment domain expert."""
    
    def __init__(self, delay: float = 2.0):
        super().__init__("BillingAgent", delay)

    async def analyze(self, logs: List[str]) -> Message:
        currency_errors = [l for l in logs if "currency" in l.lower()]
        stripe_errors = [l for l in logs if "stripe" in l.lower()]
        
        text = "**Billing Analysis:**\n"
        text += f"- Found {len(currency_errors)} currency-related errors\n"
        text += f"- Found {len(stripe_errors)} Stripe API errors\n\n"
        
        if currency_errors:
            text += "**Root Cause Hypothesis:**\n"
            text += "Backend now requires `currency` field in payment requests.\n"
            text += "Frontend is NOT sending this field.\n\n"
            text += "**Evidence:**\n"
            text += f"```\n{currency_errors[0]}\n```\n\n"
            text += "**Recommendation:** Escalate to FrontendAgent to add `currency` to request payload."
        else:
            text += "No billing-specific issues found in logs."
        
        return await self.speak(text)


class OrderingAgent(BaseAgent):
    """Order processing domain expert."""
    
    def __init__(self, delay: float = 2.0):
        super().__init__("OrderingAgent", delay)

    async def analyze(self, logs: List[str]) -> Message:
        order_errors = [l for l in logs if "ORDER" in l or "create-order" in l]
        inventory_errors = [l for l in logs if "inventory" in l.lower()]
        
        text = "**Ordering Analysis:**\n"
        text += f"- Order-related errors: {len(order_errors)}\n"
        text += f"- Inventory lock issues: {len(inventory_errors)}\n\n"
        
        if order_errors and "validation" in str(order_errors):
            text += "**Observation:** Order creation failing due to upstream validation (billing).\n"
            text += "Orders are not reaching our service — blocked at billing layer.\n\n"
            text += "**Recommendation:** This is NOT an ordering bug. Defer to BillingAgent findings."
        else:
            text += "Order processing pipeline appears healthy. No action required from Ordering."
        
        return await self.speak(text)


class FrontendAgent(BaseAgent):
    """Frontend code and deployment agent."""
    
    def __init__(self, delay: float = 2.0):
        super().__init__("FrontendAgent", delay)

    async def inspect_code(self, demo_frontend_path: str = "demo_frontend") -> Tuple[Message, Optional[str], Optional[Tuple[str, str]]]:
        """Inspect frontend code for issues."""
        path = Path(demo_frontend_path) / "checkout.ts"
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                orig = f.read()
        except FileNotFoundError:
            return await self.speak("⚠️ Could not locate checkout.ts file."), None, None

        # Check for missing currency
        if "currency" in orig:
            return await self.speak("✅ Frontend code looks correct — `currency` is present."), orig, None

        # Found the bug!
        text = "**Code Inspection Results:**\n"
        text += "❌ **Bug Found:** `checkout.ts` is NOT sending `currency` in the request body.\n\n"
        text += "**Current code:**\n"
        text += "```typescript\n"
        text += 'body: JSON.stringify({\n  paymentIntentId,\n  amount\n})\n'
        text += "```\n\n"
        text += "**Fix Required:** Add `currency: \"INR\"` to the request body."
        
        # Generate fix
        fixed = self._apply_fix(orig)
        diff = self._generate_diff(orig, fixed)
        
        return await self.speak(text), orig, (fixed, diff)

    def _apply_fix(self, original: str) -> str:
        """Apply the currency fix."""
        lines = original.splitlines(keepends=True)
        fixed_lines = []
        for line in lines:
            fixed_lines.append(line)
            if "amount" in line and "currency" not in original:
                # Add currency after amount
                if not line.rstrip().endswith(","):
                    fixed_lines[-1] = line.rstrip().rstrip(",") + ",\n"
                indent = len(line) - len(line.lstrip())
                fixed_lines.append(" " * indent + 'currency: "INR"\n')
        return "".join(fixed_lines)

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
        await asyncio.sleep(0.5)
        
        text = "**Vercel Deployment:**\n"
        text += "```\n"
        text += "▶ Building project...\n"
        text += "✓ Compiled successfully in 8.2s\n"
        text += "▶ Deploying to production...\n"
        text += "✓ Production: https://demo-frontend.vercel.app\n"
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
        text = "# Root Cause Analysis\n\n"
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
