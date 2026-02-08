# AI Incident Triage Platform

**AI-Driven Incident Management System** — Simulate, detect, diagnose, and resolve production incidents using autonomous AI agents that follow real engineering processes.

## 🚀 Features

- **Autonomous incident detection** — Alert engine monitors logs and auto-creates tickets
- **AI-chaired triage calls** — ChairAgent runs structured incident response
- **Domain-specific agents** — Billing, Ordering, Frontend, SRE experts with editable runbooks
- **Real failures** — Random failure injection makes each demo unique
- **Live code fixes** — FrontendAgent inspects code, generates patches, deploys to Vercel (simulated)
- **Automated RCA** — Full root cause analysis generated at end of triage

## 📁 Project Structure

```
triage/
├── runbooks/           # Editable agent runbooks (JSON)
├── services/           # Dummy billing/ordering services + failure injection
├── alert_engine/       # Alert detection + ticket creation
├── incident_ai/        # AI agents with LLaMA-style prompts
├── web/                # Flask web UI with SSE streaming
├── demo_frontend/      # Buggy Next.js code for demo
├── run_web.py          # Launch web UI
└── run_demo.py         # CLI demo
```

## 🏃 Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Web UI

```bash
python run_web.py
```

Open http://localhost:5050 in your browser.

### 3. Start a Demo Incident

Click **"Start Demo Incident"** to watch AI agents:
- Open a triage call
- Analyze logs and deployments
- Identify root cause
- Generate and apply a code fix
- Deploy to production
- Produce an RCA

## 📖 Agent Runbooks

Runbooks define how each agent thinks and acts. Edit them live at `/runbooks`:

- `runbooks/chair_agent.json` — Incident commander protocol
- `runbooks/billing_agent.json` — Payment/Stripe expertise
- `runbooks/ordering_agent.json` — Order processing knowledge
- `runbooks/frontend_agent.json` — Frontend code ownership
- `runbooks/sre_agent.json` — Infrastructure and observability

## 🎲 Random Failure Injection

No hardcoded scenarios! Each demo triggers random failures based on probability:

```json
{
  "service": "billing",
  "type": "schema_mismatch",
  "error_code": "BILLING_400",
  "probability": 0.25
}
```

Edit `services/failure_policy.json` to customize failure modes.

## 🧠 Architecture

```
Alert Engine → Ticket → ChairAgent opens call
                            ↓
                      MainAgent assessment
                            ↓
                  SRE: deploys + past incidents
                            ↓
            BillingAgent + OrderingAgent analysis
                            ↓
                FrontendAgent: fix + deploy
                            ↓
                    ChairAgent closes call
                            ↓
                        RCA generated
```

## 🔮 Future: LLaMA Integration

Agents are designed for LLaMA integration. Each agent's `get_prompt()` method returns a system prompt built from their runbook:

```python
from incident_ai import BillingAgent

agent = BillingAgent()
prompt = agent.get_prompt()  # LLaMA-ready system prompt
```

No paid APIs required — use LLaMA 3 locally or hosted.

---

## 🌐 Deployment

### Railway (Recommended)
```bash
npm install -g @railway/cli
railway login
railway init
railway up
```

### Render
1. Push to GitHub
2. Go to [render.com](https://render.com) → New Web Service
3. Connect your repo
4. Build: `pip install -r requirements.txt`
5. Start: `python run_web.py`

### Fly.io
```bash
brew install flyctl
fly launch
fly deploy
```

### Vercel (Next.js Demo Only)
```bash
cd vercel_demo
npm install
npx vercel
```

---

Built for demos, learning, and the future of SRE.
