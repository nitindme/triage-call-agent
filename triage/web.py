"""
Flask web server that streams triage conversation to the browser via SSE.
Run with: python -m triage.web   (from project root)
"""
import asyncio
import json
import random
import threading
from queue import Queue
from flask import Flask, Response, render_template

from .agents import (
    Ticket,
    ChairAgent,
    MainAgent,
    SREAgent,
    BillingAgent,
    OrderingAgent,
    FrontendAgent,
)

app = Flask(__name__)


def run_triage(q: Queue):
    """Run the triage asynchronously and push messages to queue."""

    async def _run():
        ticket = Ticket(
            id="INC-2026-021",
            severity="SEV-2",
            env="production",
            summary="Users unable to place orders after checkout",
            first_detected="2026-02-08T14:02:00",
        )

        chair = ChairAgent("ChairAgent")
        main = MainAgent("MainAgent")
        sre = SREAgent("SREAgent")
        billing = BillingAgent("BillingAgent")
        ordering = OrderingAgent("OrderingAgent")
        frontend = FrontendAgent("FrontendAgent")

        async def send(msg):
            q.put({"type": "msg", **msg})
            await asyncio.sleep(random.uniform(1.2, 2.0))  # realistic delay

        await send(await chair.open_call(ticket))

        logs = await sre.provide_logs(ticket, count=50)
        await send(await main.initial_assessment(ticket, logs))

        await send(await sre.recent_deploys())

        await send(await billing.analyze(logs))
        await send(await ordering.analyze(logs))

        speak_result, orig, patch_info = await frontend.inspect_code("demo_frontend")
        await send(speak_result)

        if patch_info is not None:
            fixed, diff = patch_info
            await send({"agent": "FrontendAgent", "ts": "", "text": "Patch diff:\n" + diff})
            await asyncio.sleep(1.0)
            await send(await frontend.apply_fix("demo_frontend", fixed))
            deploy_logs = await frontend.simulate_vercel_deploy()
            await send({"agent": "FrontendAgent", "ts": "", "text": "Vercel deploy logs:\n" + "\n".join(deploy_logs)})

        await send(await chair.close_call())

        rca = {
            "what_happened": "Frontend stopped sending required 'currency' field to create-order endpoint after recent backend validation change.",
            "why_it_happened": "Backend validation was tightened to require 'currency'. Frontend code did not include currency in the POST payload.",
            "why_not_caught": "No contract tests covering this payload field and no end-to-end tests in CI that validated create-order payloads.",
            "customer_impact": "Orders failing at checkout with 400 — users unable to place orders.",
            "fix_applied": "Frontend patched to include currency in the request body and deployed to production (simulated).",
            "preventive_actions": [
                "Add contract tests between frontend and backend for critical APIs",
                "Add end-to-end CI scenarios for payment flows",
                "Add monitoring alert for 4xx spikes on /api/create-order",
            ],
        }
        q.put({"type": "rca", "rca": rca})

    asyncio.run(_run())


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/stream")
def stream():
    q: Queue = Queue()

    def generate():
        # start triage in background thread
        t = threading.Thread(target=run_triage, args=(q,), daemon=True)
        t.start()
        while True:
            item = q.get()
            yield f"data: {json.dumps(item)}\n\n"
            if item.get("type") == "rca":
                break

    return Response(generate(), mimetype="text/event-stream")


def main():
    print("Starting triage web server at http://127.0.0.1:5050")
    app.run(host="127.0.0.1", port=5050, debug=False, threaded=True)


if __name__ == "__main__":
    main()
