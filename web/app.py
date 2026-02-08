"""
Web Application
Professional Flask app with SSE streaming for live incident triage.
"""

import asyncio
import json
import queue
import threading
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, Response, jsonify, request, stream_with_context
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from incident_ai import (
    ChairAgent, MainAgent, SREAgent, BillingAgent, 
    OrderingAgent, FrontendAgent, RCA, Message
)
from incident_ai.runbook_loader import get_runbook_manager
from alert_engine import get_alert_engine

app = Flask(__name__, 
            template_folder="templates",
            static_folder="static")

# Global message queue for SSE
message_queue = queue.Queue()
current_incident = None
triage_running = False


def run_async(coro):
    """Run async coroutine in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def run_triage_session(ticket):
    """Run a full triage session and push messages to queue."""
    global triage_running
    triage_running = True
    
    # Initialize agents
    chair = ChairAgent(delay=2.0)
    main = MainAgent(delay=2.5)
    sre = SREAgent(delay=2.0)
    billing = BillingAgent(delay=2.5)
    ordering = OrderingAgent(delay=2.0)
    frontend = FrontendAgent(delay=2.5)
    
    messages = []
    
    def push(msg: Message):
        messages.append(msg)
        message_queue.put(msg)
    
    # 1. Chair opens call
    push(await chair.open_call(ticket))
    
    # 2. Chair requests assessment
    push(await chair.request_assessment())
    
    # 3. Get logs from SRE
    logs = await sre.provide_logs(count=40)
    
    # 4. Main provides assessment
    assessment_msg, affected_services = await main.initial_assessment(logs)
    push(assessment_msg)
    
    # 5. Chair requests deploy info
    push(await chair.request_deploys())
    
    # 6. SRE provides deploys
    push(await sre.recent_deploys())
    
    # 7. SRE provides past incidents
    push(await sre.past_incidents())
    
    # 8. Chair routes to experts
    push(await chair.route_to_experts(affected_services))
    
    # 9. Billing analyzes
    push(await billing.analyze(logs))
    
    # 10. Ordering analyzes
    push(await ordering.analyze(logs))
    
    # 11. Chair requests fix from frontend
    push(await chair.request_fix())
    
    # 12. Frontend inspects code
    inspect_msg, orig, patch_info = await frontend.inspect_code("demo_frontend")
    push(inspect_msg)
    
    if patch_info:
        fixed, diff = patch_info
        
        # 13. Show diff
        push(await frontend.show_diff(diff))
        
        # 14. Apply fix
        push(await frontend.apply_fix("demo_frontend", fixed))
        
        # 15. Deploy
        push(await frontend.simulate_deploy())
        
        # 16. Chair confirms
        push(await chair.confirm_fix())
    
    # 17. Chair closes call
    push(await chair.close_call())
    
    # 18. Generate RCA
    rca = RCA(
        what_happened="Frontend stopped sending required 'currency' field to create-order endpoint after backend validation was tightened.",
        why_it_happened="Backend deploy added mandatory currency validation. Frontend was deployed earlier and did not include currency in the request payload.",
        why_not_caught="No contract tests between frontend and backend. No end-to-end tests validating payment payloads in CI.",
        customer_impact="Users unable to complete checkout. Orders failing with 400 errors. Estimated revenue impact during outage.",
        fix_applied="Added currency: 'INR' to frontend checkout.ts request body. Deployed to production via Vercel.",
        preventive_actions=[
            "Add contract tests between frontend and backend for critical APIs",
            "Add end-to-end CI scenarios for payment flows",
            "Add monitoring alert for 4xx spikes on /api/create-order",
            "Implement API versioning to prevent breaking changes"
        ],
        timeline=[
            "14:02 - Alert triggered: High 400 error rate on /api/create-order",
            "14:03 - Ticket INC-2026-021 auto-created",
            "14:04 - AI triage call opened",
            "14:08 - Root cause identified: missing currency field",
            "14:10 - Fix applied and deployed",
            "14:12 - Error rate normalized",
            "14:15 - Triage call closed"
        ]
    )
    
    # Push RCA as system message
    rca_msg = Message(
        agent="System",
        text=rca.format_markdown(),
        timestamp=datetime.now().strftime("%H:%M:%S"),
        message_type="rca"
    )
    push(rca_msg)
    
    triage_running = False
    return messages, rca


def triage_thread(ticket):
    """Run triage in a separate thread."""
    run_async(run_triage_session(ticket))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/runbooks")
def runbooks():
    manager = get_runbook_manager()
    all_runbooks = manager.get_all_runbooks()
    return render_template("runbooks.html", runbooks=all_runbooks)


@app.route("/api/runbook/<agent_name>")
def get_runbook(agent_name):
    manager = get_runbook_manager()
    rb = manager.load_runbook(agent_name)
    if rb:
        return jsonify(rb.raw_data)
    return jsonify({"error": "Runbook not found"}), 404


@app.route("/api/runbook/<agent_name>", methods=["POST"])
def update_runbook(agent_name):
    manager = get_runbook_manager()
    updates = request.json
    if manager.update_runbook(agent_name, updates):
        return jsonify({"success": True})
    return jsonify({"error": "Failed to update"}), 400


@app.route("/api/start-triage", methods=["POST"])
def start_triage():
    global current_incident
    
    if triage_running:
        return jsonify({"error": "Triage already in progress"}), 400
    
    # Clear queue
    while not message_queue.empty():
        try:
            message_queue.get_nowait()
        except queue.Empty:
            break
    
    # Create incident
    alert_engine = get_alert_engine()
    current_incident = alert_engine.trigger_demo_incident("billing_currency_missing")
    
    # Reset demo frontend to buggy version
    buggy_code = '''// checkout.ts - buggy example Next.js client snippet

async function createOrder(paymentIntentId, amount) {
  const res = await fetch("/api/create-order", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      paymentIntentId,
      amount
    })
  });

  if (!res.ok) {
    throw new Error("Order failed");
  }

  return await res.json();
}

export default createOrder;
'''
    with open("demo_frontend/checkout.ts", "w") as f:
        f.write(buggy_code)
    
    # Start triage in background thread
    thread = threading.Thread(target=triage_thread, args=(current_incident,))
    thread.start()
    
    return jsonify({
        "success": True,
        "ticket_id": current_incident.id,
        "severity": current_incident.severity
    })


@app.route("/api/stream")
def stream():
    def generate():
        while True:
            try:
                msg = message_queue.get(timeout=30)
                data = {
                    "agent": msg.agent,
                    "text": msg.text,
                    "timestamp": msg.timestamp,
                    "type": msg.message_type
                }
                yield f"data: {json.dumps(data)}\n\n"
            except queue.Empty:
                if not triage_running:
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                    break
                yield f"data: {json.dumps({'type': 'ping'})}\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


@app.route("/api/incident")
def get_incident():
    if current_incident:
        return jsonify({
            "id": current_incident.id,
            "severity": current_incident.severity,
            "summary": current_incident.summary,
            "symptoms": current_incident.symptoms,
            "first_detected": current_incident.first_detected
        })
    return jsonify(None)


if __name__ == "__main__":
    app.run(debug=True, port=5050, threaded=True)
