"""
Web Application (v3)
Flask app with improved delays, human-in-the-loop approval, and LLaMA integration.
"""

import asyncio
import json
import queue
import threading
import time
import random
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, Response, jsonify, request
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from incident_ai.llama_generator import get_incident_generator, DynamicIncident

app = Flask(__name__, 
            template_folder="templates",
            static_folder="static")

# Global message queue for SSE
message_queues = []
current_incident = None

# Human-in-the-loop approval state
approval_pending = False
approval_granted = False
approval_event = threading.Event()

# Participants in the triage call
PARTICIPANTS = [
    {"name": "Nitin", "role": "Engineering Lead", "avatar": "👨‍💻"},
    {"name": "ChairAgent", "role": "Triage Chair (AI)", "avatar": "🤖"},
    {"name": "MainAgent", "role": "Incident Coordinator (AI)", "avatar": "🎯"},
    {"name": "SREAgent", "role": "SRE (AI)", "avatar": "🔧"},
    {"name": "BillingAgent", "role": "Billing Expert (AI)", "avatar": "💳"},
    {"name": "OrderingAgent", "role": "Orders Expert (AI)", "avatar": "📦"},
    {"name": "FrontendAgent", "role": "Frontend Expert (AI)", "avatar": "🖥️"},
]


def broadcast_message(msg: dict):
    """Send message to all connected clients."""
    for q in message_queues:
        try:
            q.put_nowait(msg)
        except:
            pass


def delay_with_ping(seconds: float):
    """Sleep with periodic pings to keep SSE alive."""
    # For cloud platforms with 30s timeouts, use shorter delays
    # and send keepalive pings
    actual_delay = min(seconds, 1.5)  # Cap at 1.5s for production
    time.sleep(actual_delay)


def create_message(agent: str, text: str, msg_type: str = "speech") -> dict:
    """Create a message dict."""
    return {
        "agent": agent,
        "text": text,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "message_type": msg_type
    }


def run_triage_sync():
    """Run triage session synchronously with production-safe delays."""
    global current_incident
    
    # Generate a dynamic incident (could be billing, ordering, database, etc.)
    generator = get_incident_generator()
    incident = generator.generate_incident()
    current_incident = incident
    
    # Write buggy code to the appropriate file
    code_path = Path(f"demo_code/{incident.file_name}")
    code_path.parent.mkdir(parents=True, exist_ok=True)
    code_path.write_text(incident.buggy_code)
    
    # Create ticket
    ticket_id = f"INC-2026-{random.randint(100, 999)}"
    
    # ========== TRIAGE BEGINS ==========
    
    # 1. Chair opens (3s delay)
    delay_with_ping(3)
    broadcast_message(create_message("ChairAgent", 
        f"🚨 **Opening triage for {ticket_id}**\n"
        f"**Severity:** SEV-2\n"
        f"**Service:** {incident.service.upper()}\n"
        f"**Error:** `{incident.error_code}` - {incident.error_message}\n"
        f"**Symptoms:** {', '.join(incident.symptoms[:2])}"
    ))
    
    # 2. Chair requests assessment (2s)
    delay_with_ping(2)
    broadcast_message(create_message("ChairAgent",
        "📋 MainAgent, please provide your initial assessment."
    ))
    
    # 3. Main assessment (4s - thinking)
    delay_with_ping(4)
    broadcast_message(create_message("MainAgent",
        f"**Initial Assessment:**\n"
        f"- Error pattern: `{incident.error_code}`\n"
        f"- Affected service: **{incident.service.upper()}**\n"
        f"- Responsible team: **{incident.agent_owner}**\n"
        f"- Hypothesis: {incident.root_cause}\n\n"
        f"Recommend routing to **{incident.agent_owner}** for deep dive."
    ))
    
    # 4. Chair asks for deploys (2s)
    delay_with_ping(2)
    broadcast_message(create_message("ChairAgent",
        "🔍 SREAgent, check recent deployments and similar incidents."
    ))
    
    # 5. SRE provides deploy info (3s)
    delay_with_ping(3)
    broadcast_message(create_message("SREAgent",
        "**Recent Deployments:**\n"
        f"- `backend/{incident.service}` v1.{random.randint(1,9)}.{random.randint(0,9)} ({datetime.now().strftime('%H:%M')}) - Added validation\n"
        "- `frontend` v2.8.0 (earlier) - Checkout refactor\n\n"
        "**⚠️ Backend deployed AFTER frontend - possible contract mismatch**"
    ))
    
    # 6. SRE past incidents (2s)
    delay_with_ping(2)
    broadcast_message(create_message("SREAgent",
        "**Similar Past Incidents:**\n"
        "- INC-2026-015: API contract mismatch after deploy\n"
        "- INC-2026-008: Frontend/backend version skew"
    ))
    
    # 7. Route to responsible agent (2s)
    delay_with_ping(2)
    broadcast_message(create_message("ChairAgent",
        f"📌 Routing to **{incident.agent_owner}** for detailed analysis."
    ))
    
    # 8. Responsible agent analysis (4s)
    delay_with_ping(4)
    broadcast_message(create_message(incident.agent_owner,
        f"**{incident.service.upper()} Analysis:**\n"
        f"- Found errors matching `{incident.error_code}`\n"
        f"- File: `{incident.file_name}`\n"
        f"- Root cause: {incident.root_cause}\n\n"
        f"**Recommendation:** Code fix required."
    ))
    
    # 9. Other agents confirm no issues (3s)
    delay_with_ping(3)
    other_agents = ["BillingAgent", "OrderingAgent", "SREAgent"]
    other_agent = random.choice([a for a in other_agents if a != incident.agent_owner])
    broadcast_message(create_message(other_agent,
        f"**{other_agent.replace('Agent', '')} Status:**\n"
        "- No issues detected in our domain\n"
        f"- Confirming {incident.agent_owner} has the lead"
    ))
    
    # 10. Chair requests fix (2s)
    delay_with_ping(2)
    broadcast_message(create_message("ChairAgent",
        f"🔧 {incident.agent_owner}, please inspect the code and propose a fix."
    ))
    
    # 11. Agent inspects code (4s)
    delay_with_ping(4)
    broadcast_message(create_message(incident.agent_owner,
        f"**Code Inspection - `{incident.file_name}`:**\n"
        f"❌ **Bug Found:** {incident.fix_description}\n\n"
        f"**Error:** `{incident.error_code}` - {incident.error_message}\n\n"
        "Preparing patch..."
    ))
    
    # 12. Show diff (3s)
    delay_with_ping(3)
    broadcast_message(create_message(incident.agent_owner,
        f"**Proposed Fix:**\n```diff\n{incident.fix_description}\n```",
        msg_type="code"
    ))
    
    # 13. Apply fix locally (2s)
    delay_with_ping(2)
    code_path.write_text(incident.fixed_code)
    broadcast_message(create_message(incident.agent_owner,
        f"✅ Fix applied locally to `{incident.file_name}`"
    ))
    
    # 14. BUILD PHASE - before human approval (3s)
    delay_with_ping(3)
    deploy_target = "Kubernetes" if incident.service in ["database", "kubernetes", "cache", "gateway", "auth", "queue"] else "Vercel"
    broadcast_message(create_message(incident.agent_owner,
        f"**{deploy_target} Build:**\n"
        "```\n"
        "▶ Building project...\n"
        "✓ Compiled successfully in 8.2s\n"
        "▶ Running tests... passed\n"
        "✓ Build ready for deployment\n"
        "```",
        msg_type="code"
    ))
    
    # ========== HUMAN IN THE LOOP - APPROVAL REQUIRED ==========
    global approval_pending, approval_granted, approval_event
    approval_pending = True
    approval_granted = False
    approval_event.clear()
    
    delay_with_ping(1)
    broadcast_message(create_message("ChairAgent",
        "⚠️ **HUMAN APPROVAL REQUIRED**\n\n"
        f"@Nitin - Please review the proposed fix and approve deployment to production.\n\n"
        f"**Service:** {incident.service.upper()}\n"
        f"**File:** `{incident.file_name}`\n"
        f"**Change:** {incident.fix_description}",
        msg_type="approval_request"
    ))
    
    # Wait for human approval (short timeout for demo, auto-approve if not responded)
    broadcast_message({
        "type": "waiting_approval",
        "message": "Waiting for Nitin's approval... (auto-approves in 15s)",
        "timestamp": datetime.now().strftime("%H:%M:%S")
    })
    
    # Short timeout for production demo (15 seconds), auto-approve if no response
    print(f"[TRIAGE] Waiting for approval... approval_granted={approval_granted}")
    approved = approval_event.wait(timeout=15)
    print(f"[TRIAGE] Wait complete. approved={approved}, approval_granted={approval_granted}")
    
    if not approved:
        # Auto-approve for demo purposes (timeout reached)
        print("[TRIAGE] Timeout - auto-approving")
        approval_granted = True
        broadcast_message(create_message("Nitin",
            "✅ **Auto-approved** - Fix looks good, proceeding with deployment.",
            msg_type="human"
        ))
    elif not approval_granted:
        print("[TRIAGE] Rejected by user")
        broadcast_message(create_message("ChairAgent",
            "❌ **Deployment rejected by Nitin.**\n"
            "Triage paused. Manual intervention required."
        ))
        approval_pending = False
        return
    else:
        # Human manually approved
        print("[TRIAGE] Manually approved by user")
        delay_with_ping(0.5)
        broadcast_message(create_message("Nitin",
            "✅ **Approved!** Looks good, deploy to production.",
            msg_type="human"
        ))
    
    approval_pending = False
    
    # 15. DEPLOY after approval (1.5s)
    delay_with_ping(1.5)
    broadcast_message(create_message(incident.agent_owner,
        f"**{deploy_target} Deployment:**\n"
        "```\n"
        "▶ Human approval received ✓\n"
        "▶ Deploying to production...\n"
        f"✓ https://{incident.service}.prod.example.com\n"
        f"✓ Deployment to {incident.service} complete!\n"
        "```",
        msg_type="code"
    ))
    
    # 16. Chair confirms (2s)
    delay_with_ping(2)
    broadcast_message(create_message("ChairAgent",
        "✅ Fix deployed. Monitoring error rates..."
    ))
    
    # 17. Chair closes (3s)
    delay_with_ping(3)
    broadcast_message(create_message("ChairAgent",
        "📝 **Closing triage call.**\n"
        "Error rate normalized. Fix confirmed working.\n"
        "RCA to follow. Thank you all!"
    ))
    
    # 18. RCA (2s)
    delay_with_ping(2)
    
    # Dynamic impact based on service
    impact_map = {
        "billing": "Payment processing failures. ~50 failed transactions.",
        "ordering": "Order creation failures. ~30 duplicate/lost orders.",
        "database": "Database connection failures affecting all services.",
        "auth": "Authentication failures. Users logged out unexpectedly.",
        "cache": "Cache failures causing database overload.",
        "kubernetes": "Pod restarts causing intermittent service unavailability.",
        "queue": "Message processing failures. Events lost.",
        "gateway": "API gateway failures blocking requests.",
        "frontend": "UI failures preventing user interactions.",
    }
    impact = impact_map.get(incident.service, "Service degradation affecting users.")
    
    rca_text = f"""# 📋 Root Cause Analysis

## What Happened
**{incident.service.upper()}** service returned `{incident.error_code}` errors.

## Error Details
{incident.error_message}

## Why It Happened
{incident.root_cause}

## Customer Impact
{impact}

## Fix Applied
**File:** `{incident.file_name}`
**Change:** {incident.fix_description}

## Preventive Actions
- Add monitoring for `{incident.error_code}` errors
- Add integration tests for {incident.service} service
- Review deployment procedures

## Timeline
- {datetime.now().strftime('%H:%M')} - Alert triggered
- +2 min - Triage opened
- +5 min - Root cause identified by {incident.agent_owner}
- +8 min - Fix deployed
- +10 min - Incident resolved
"""
    broadcast_message(create_message("System", rca_text, msg_type="rca"))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/stream")
def stream():
    """SSE endpoint for real-time messages."""
    def generate():
        q = queue.Queue()
        message_queues.append(q)
        try:
            while True:
                try:
                    msg = q.get(timeout=60)
                    yield f"data: {json.dumps(msg)}\n\n"
                except queue.Empty:
                    yield f"data: {json.dumps({'type': 'ping'})}\n\n"
        except GeneratorExit:
            pass
        finally:
            if q in message_queues:
                message_queues.remove(q)
    
    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/start", methods=["POST"])
def start_triage():
    """Start a new triage session."""
    global approval_pending, approval_granted
    approval_pending = False
    approval_granted = False
    
    thread = threading.Thread(target=run_triage_sync)
    thread.daemon = True
    thread.start()
    return jsonify({"status": "started"})


@app.route("/approve", methods=["POST"])
def approve_deployment():
    """Human approves the deployment."""
    global approval_granted, approval_pending
    print(f"[APPROVE] Received approval request. Pending: {approval_pending}")
    approval_granted = True
    approval_event.set()
    print(f"[APPROVE] Event set. Granted: {approval_granted}")
    return jsonify({"status": "approved", "by": "Nitin"})


@app.route("/reject", methods=["POST"])
def reject_deployment():
    """Human rejects the deployment."""
    global approval_granted, approval_pending
    print(f"[REJECT] Received rejection request. Pending: {approval_pending}")
    approval_granted = False
    approval_event.set()
    return jsonify({"status": "rejected", "by": "Nitin"})


@app.route("/approval-status")
def approval_status():
    """Check if approval is pending."""
    return jsonify({
        "pending": approval_pending,
        "granted": approval_granted
    })


@app.route("/participants")
def get_participants():
    """Get list of participants in the triage call."""
    return jsonify({"participants": PARTICIPANTS})


@app.route("/runbooks")
def get_runbooks():
    """Get available runbooks."""
    runbooks = [
        {
            "id": "billing-errors",
            "name": "Billing Service Errors",
            "description": "Handle billing and payment processing issues",
            "steps": [
                "Check Stripe API status",
                "Verify API credentials",
                "Check for missing required fields",
                "Review recent deployments"
            ]
        },
        {
            "id": "database-issues",
            "name": "Database Connection Issues",
            "description": "Handle database pool exhaustion and deadlocks",
            "steps": [
                "Check connection pool metrics",
                "Review slow query logs",
                "Check for deadlocks",
                "Consider pool size increase"
            ]
        },
        {
            "id": "auth-failures",
            "name": "Authentication Failures",
            "description": "Handle JWT and auth service issues",
            "steps": [
                "Check if JWT secret was recently rotated",
                "Verify token expiration settings",
                "Check auth service health",
                "Review recent auth deployments"
            ]
        },
        {
            "id": "cache-issues",
            "name": "Cache/Redis Issues",
            "description": "Handle cache stampedes and Redis problems",
            "steps": [
                "Check Redis memory usage",
                "Review cache hit/miss rates",
                "Check for thundering herd patterns",
                "Verify cache TTL settings"
            ]
        },
        {
            "id": "k8s-issues",
            "name": "Kubernetes Issues",
            "description": "Handle pod crashes, OOM, and scaling issues",
            "steps": [
                "Check pod status and restarts",
                "Review resource limits",
                "Check node health",
                "Review recent deployments"
            ]
        }
    ]
    return jsonify({"runbooks": runbooks})


@app.route("/current-failure")
def current_failure_route():
    """Get info about current incident."""
    if current_incident:
        return jsonify({
            "id": f"{current_incident.service}_{current_incident.error_code}",
            "service": current_incident.service,
            "error_code": current_incident.error_code,
            "message": current_incident.error_message,
            "file": current_incident.file_name,
            "agent_owner": current_incident.agent_owner
        })
    return jsonify({"status": "no incident"})


@app.route("/buggy-code")
def buggy_code():
    """Get the current buggy code."""
    if current_incident:
        code_path = Path(f"demo_code/{current_incident.file_name}")
        try:
            return jsonify({"code": code_path.read_text(), "file": current_incident.file_name})
        except:
            pass
    return jsonify({"code": "// No code available", "file": "unknown"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    print(f"\n🚨 AI Incident Triage Platform")
    print(f"📌 Running on port: {port}\n")
    app.run(host="0.0.0.0", debug=debug, port=port, threaded=True)
