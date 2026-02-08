import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any

from .sample_logs import generate_logs
from .utils import unified_diff


def now_ts():
    return datetime.now().isoformat()


@dataclass
class Ticket:
    id: str
    severity: str
    env: str
    summary: str
    first_detected: str


class Agent:
    def __init__(self, name: str):
        self.name = name

    async def speak(self, text: str) -> Dict[str, Any]:
        msg = {"agent": self.name, "ts": now_ts(), "text": text}
        # small delay to simulate thinking
        await asyncio.sleep(0.05)
        return msg


class ChairAgent(Agent):
    async def open_call(self, ticket: Ticket):
        return await self.speak(
            f":rotating_light: Opening triage for {ticket.id} — {ticket.summary} (sev={ticket.severity})"
        )

    async def close_call(self):
        return await self.speak(":white_check_mark: Closing the call — actions assigned and RCA to follow")


class MainAgent(Agent):
    async def initial_assessment(self, ticket: Ticket, logs: List[str]):
        # Look for quick signals
        hints = []
        for L in logs[-10:]:
            if "missing field 'currency'" in L or "requires currency" in L:
                hints.append("billing_validation")
        if hints:
            return await self.speak(
                "Initial assessment: evidence of payment/billing validation failures. Routing to Billing + Frontend"
            )
        return await self.speak("Initial assessment: no obvious pattern — ask SRE for recent deploys and metrics")


class SREAgent(Agent):
    async def recent_deploys(self):
        # provide a simulated deploy history
        return await self.speak(
            "Recent deploy: backend/orders v1.3.2 (2026-02-08T13:58:00), frontend v2.8.0 (2026-02-08T13:55:00)"
        )

    async def provide_logs(self, ticket: Ticket, count: int = 30):
        # return last N logs
        return list(generate_logs(ticket.id, lines=count))


class BillingAgent(Agent):
    async def analyze(self, logs: List[str]):
        findings = [L for L in logs if "currency" in L or "Stripe" in L]
        if findings:
            text = "BillingAgent: Found Stripe/payment validation errors referencing missing currency. Hypothesis: frontend/contract mismatch."
        else:
            text = "BillingAgent: No billing errors in provided logs."
        return await self.speak(text)


class OrderingAgent(Agent):
    async def analyze(self, logs: List[str]):
        findings = [L for L in logs if "inventory" in L or "create-order" in L]
        if findings:
            text = "OrderingAgent: Some inventory lock errors observed but majority are 400 on create-order."
        else:
            text = "OrderingAgent: No ordering-specific stack traces found."
        return await self.speak(text)


class FrontendAgent(Agent):
    async def inspect_code(self, demo_frontend_path: str):
        # read file and look for missing 'currency' in JSON body
        path = f"{demo_frontend_path}/checkout.ts"
        try:
            with open(path, "r", encoding="utf-8") as f:
                orig = f.read()
        except FileNotFoundError:
            return await self.speak("FrontendAgent: demo frontend file not found."), None, None

        if "currency" in orig:
            return await self.speak("FrontendAgent: Looks OK — 'currency' present."), orig, None
        # propose fix: insert currency field right after the `amount` line.
        lines = orig.splitlines(keepends=True)
        fixed_lines = []
        inserted = False
        for i, line in enumerate(lines):
            fixed_lines.append(line)
            if not inserted and "amount" in line and ")" not in line:
                # ensure the amount line ends with a comma
                if not line.rstrip().endswith(","):
                    fixed_lines[-1] = line.rstrip() + ",\n"
                # determine indentation
                indent = ""
                for ch in line:
                    if ch.isspace():
                        indent += ch
                    else:
                        break
                insert_line = f"{indent}currency: \"INR\",\n"
                fixed_lines.append(insert_line)
                inserted = True

        if not inserted:
            # fallback: append currency before the closing of the body
            fixed = orig.replace(
                "})",
                "  ,currency: \"INR\"\n  })",
            )
        else:
            fixed = "".join(fixed_lines)

        diff = unified_diff(orig, fixed, fromfile="checkout.ts", tofile="checkout.fixed.ts")
        return await self.speak(
            "FrontendAgent: Detected missing 'currency' in request body. Proposing patch."
        ), orig, (fixed, diff)

    async def apply_fix(self, demo_frontend_path: str, fixed_content: str):
        path = f"{demo_frontend_path}/checkout.ts"
        with open(path, "w", encoding="utf-8") as f:
            f.write(fixed_content)
        return await self.speak("FrontendAgent: Applied fix to checkout.ts and created patch")

    async def simulate_vercel_deploy(self):
        # simulated deploy logs
        lines = [
            "Vercel: Building project (node v18)",
            "Vercel: Installing dependencies...",
            "Vercel: Build completed in 12.3s",
            "Vercel: Deploying to production...",
            "Vercel: Production deployment success — https://demo-frontend.vercel.app (alias)"
        ]
        for l in lines:
            await asyncio.sleep(0.02)
        return lines
