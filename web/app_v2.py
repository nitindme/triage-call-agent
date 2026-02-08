"""
Web Application (v2)
Simple Flask app with SSE streaming for live incident triage.
"""

import asyncio
import json
import queue
import threading
import time
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, Response, jsonify, request
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.random_failure import get_failure_injector, reset_failure_injector
from incident_ai.agents_v2 import (
    ChairAgent, MainAgent, SREAgent, BillingAgent, 
    OrderingAgent, FrontendAgent, RCA, Message
)

app = Flask(__name__, 
            template_folder="templates",
            static_folder="static")

# Global message queue for SSE
message_queues = []


def run_async(coro):
    """Run async coroutine in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def broadcast_message(msg):
    """Send message to all connected clients."""
    data = msg.to_dict() if hasattr(msg, 'to_dict') else msg
    for q in message_queues:
        try:
            q.put_nowait(data)
        except:
            pass


async def run_triage_session():
    """Run a full triage session with random failure."""
    
    # Reset and select new random failure
    injector = reset_failure_injector()
    failure = injector.select_random_failure()
    injector.inject_buggy_code("demo_frontend")
    
    # Create ticket
    ticket = {
        "id": f"INC-2026-{datetime.now().strftime('%H%M')}",
        "severity": "SEV-2",
        "summary": f"{failure.service.title()} service errors - {failure.message}",
        "first_detected": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    
    # Initialize agents with delays
    chair = ChairAgent(delay=2.0)
    main = MainAgent(delay=2.5)
    sre = SREAgent(delay=2.0)
    billing = BillingAgent(delay=2.5)
    ordering = OrderingAgent(delay=2.0)
    frontend = FrontendAgent(delay=2.5)
    
    # 1. Chair opens call
    broadcast_message(await chair.open_call(ticket))
    
    # 2. Chair requests assessment
    broadcast_message(await chair.request_assessment())
    
    # 3. Get logs from SRE
    logs = await sre.provide_logs(count=40)
    
    # 4. Main provides assessment
    assessment_msg, affected_services = await main.initial_assessment(logs)
    broadcast_message(assessment_msg)
    
    # 5. Chair requests deploy info
    broadcast_message(await chair.request_deploys())
    
    # 6. SRE provides deploys
    broadcast_message(await sre.recent_deploys())
    
    # 7. SRE provides past incidents
    broadcast_message(await sre.past_incidents())
    
    # 8. Chair routes to experts
    broadcast_message(await chair.route_to_experts(affected_services))
    
    # 9. Billing analyzes
    broadcast_message(await billing.analyze(logs))
    
    # 10. Ordering analyzes
    broadcast_message(await ordering.analyze(logs))
    
    # 11. Chair requests fix from frontend
    broadcast_message(await chair.request_fix())
    
    # 12. Frontend inspects code
    inspect_msg, orig, patch_info = await frontend.inspect_code("demo_frontend")
    broadcast_message(inspect_msg)
    
    if patch_info:
        fixed, diff = patch_info
        
        # 13. Show diff
        broadcast_message(await frontend.show_diff(diff))
        
        # 14. Apply fix
        broadcast_message(await frontend.apply_fix("demo_frontend", fixed))
        
        # 15. Deploy
        broadcast_message(await frontend.simulate_deploy())
        
        # 16. Chair confirms
        broadcast_message(await chair.confirm_fix())
    
    # 17. Chair closes call
    broadcast_message(await chair.close_call())
    
    # 18. Generate RCA
    rca = RCA.from_failure(failure)
    rca_msg = Message(
        agent="System",
        text=rca.format_markdown(),
        timestamp=datetime.now().strftime("%H:%M:%S"),
        message_type="rca"
    )
    broadcast_message(rca_msg)


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
                    msg = q.get(timeout=30)
                    yield f"data: {json.dumps(msg)}\n\n"
                except queue.Empty:
                    yield f"data: {json.dumps({'type': 'ping'})}\n\n"
        finally:
            message_queues.remove(q)
    
    return Response(generate(), mimetype="text/event-stream")


@app.route("/start", methods=["POST"])
def start_triage():
    """Start a new triage session."""
    def run_in_thread():
        run_async(run_triage_session())
    
    thread = threading.Thread(target=run_in_thread)
    thread.start()
    
    return jsonify({"status": "started"})


@app.route("/current-failure")
def current_failure():
    """Get info about current failure mode."""
    injector = get_failure_injector()
    failure = injector.get_current_failure()
    if failure:
        return jsonify({
            "id": failure.id,
            "service": failure.service,
            "error_code": failure.error_code,
            "message": failure.message
        })
    return jsonify({"status": "no failure selected"})


@app.route("/buggy-code")
def buggy_code():
    """Get the current buggy code."""
    try:
        with open("demo_frontend/checkout.ts", "r") as f:
            return jsonify({"code": f.read()})
    except:
        return jsonify({"code": "// No code available"})


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚨 AI Incident Triage Platform")
    print("="*60)
    print("\n📌 Open in browser: http://localhost:5050")
    print("\n[Press Ctrl+C to stop]\n")
    
    app.run(debug=True, port=5050, threaded=True, use_reloader=False)
