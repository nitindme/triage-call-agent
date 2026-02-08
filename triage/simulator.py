import asyncio
from .agents import (
    Ticket,
    ChairAgent,
    MainAgent,
    SREAgent,
    BillingAgent,
    OrderingAgent,
    FrontendAgent,
)
from .sample_logs import generate_logs


async def run_demo():
    # build ticket
    ticket = Ticket(
        id="INC-2026-021",
        severity="SEV-2",
        env="production",
        summary="Users unable to place orders after checkout",
        first_detected="2026-02-08T14:02:00",
    )

    # instantiate agents
    chair = ChairAgent("ChairAgent")
    main = MainAgent("MainAgent")
    sre = SREAgent("SREAgent")
    billing = BillingAgent("BillingAgent")
    ordering = OrderingAgent("OrderingAgent")
    frontend = FrontendAgent("FrontendAgent")

    conversation = []

    # Open call
    conversation.append(await chair.open_call(ticket))

    # Main does initial assessment with a few logs
    logs = await sre.provide_logs(ticket, count=50)
    conversation.append(await main.initial_assessment(ticket, logs))

    # SRE reports recent deploys
    conversation.append(await sre.recent_deploys())

    # Billing and Ordering analyze logs
    conversation.append(await billing.analyze(logs))
    conversation.append(await ordering.analyze(logs))

    # Frontend inspects code
    speak_result, orig, patch_info = await frontend.inspect_code("demo_frontend")
    conversation.append(speak_result)

    if patch_info is not None:
        fixed, diff = patch_info
        # include diff in conversation
        conversation.append({"agent": "FrontendAgent", "ts": "", "text": "Patch diff:\n" + diff})
        # apply fix
        conversation.append(await frontend.apply_fix("demo_frontend", fixed))
        # simulate deploy
        deploy_logs = await frontend.simulate_vercel_deploy()
        conversation.append({"agent": "FrontendAgent", "ts": "", "text": "Vercel deploy logs:\n" + "\n".join(deploy_logs)})

    # Chair closes the call
    conversation.append(await chair.close_call())

    # Build RCA
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

    # print everything Slack-style
    print("\n=== INCIDENT TRIAGE TRANSCRIPT ===\n")
    for m in conversation:
        agent = m.get("agent", "System")
        ts = m.get("ts", "")
        text = m.get("text", "")
        print(f"[{ts}] *{agent}*: {text}\n")

    print("\n=== RCA ===\n")
    for k, v in rca.items():
        print(f"{k}: {v}\n")


if __name__ == "__main__":
    asyncio.run(run_demo())
