# Project Onboarding: Verity Protocol (OKX AI Hackathon)

This document serves as a complete context brief for the Verity Protocol. It contains everything needed to onboard a new developer or an AI assistant to the project's current state.

## 1. The Hackathon Context
We are participating in an **OKX.AI Hackathon**, which focuses on building **Agentic Service Providers (ASPs)** using the OKX Onchain OS. The goal is to create autonomous AI agents that can interact with blockchain smart contracts, negotiate, and deliver services on the X Layer (OKX's Ethereum Layer 2 network). Specifically, we are building an **A2A (Agent-to-Agent)** service where payments are held in an on-chain escrow and released based on AI evaluation.

**Note on positioning:** a `BuildX Hackathon Season 2 Agent Track.docx` in the repo root (past season's winners list) showed that "3-AI-consensus" agents (*TriMind Agent*) and generic "A2A service marketplaces" (*X Layer Agent Nexus*) had already placed 3rd before. We pivoted the framing below (Verified Live-Data Feed) specifically to avoid that overlap — see section 2.

## 2. What is the ASP (Verity Protocol)?
Our project is the **Verity Protocol — a Verified Live-Data Feed ASP**.
An agent that needs fresh, trustworthy real-world data (a live price, a page's current state, etc.) creates an escrow whose task description embeds a target URL. Our backend's **Data Provider Agent** fetches that URL live (Playwright + BeautifulSoup, originally built as the standalone `scraper_asp/` project, now living in this repo as a subdirectory and merged in-process into the backend), and a tribunal of three AI personas verifies the fetch actually satisfies the request before funds are released:
1. **Fetch Integrity Auditor**: Did the fetch actually succeed (not an error page, CAPTCHA/bot wall, or empty body)?
2. **Relevance & Completeness Analyst**: Does the content actually contain the specific data point(s) requested?
3. **Accuracy & Sanity Checker**: Does the extracted value look plausible and current, not stale or hallucinated?

If 2/3 judges approve, the backend signs a transaction releasing escrow funds to the Data Provider Agent. If the fetch fails outright or the judges reject it, the escrow still resolves — the payer is refunded automatically rather than funds staying locked forever.

(Earlier prototype: workers pasted a text payload — e.g. a market-sentiment writeup — and judges graded its quality/style/completeness. That flow is fully replaced by the above; it's kept in git history only.)

## 3. What We Have Built So Far
We have successfully built and **deployed to production** a full end-to-end decentralized application:

- **Smart Contract (`AgentEscrow.sol`)**: Deployed on the OKX X Layer Testnet, unchanged by the pivot — `taskDescription` is a free-form string, generic enough to carry a data-request spec instead of a work-grading spec. Handles escrow creation, locking funds, and releasing them upon AI approval.
- **Backend (Python/FastAPI, `backend/main.py`)**: **Live on Render at `agent-tribunal.onrender.com`**, running the pivoted code. Reads the escrow's task description, regex-extracts a target URL, fetches it live via Playwright/BeautifulSoup/markdownify (lifted from the `scraper_asp/` subdirectory of this same repo and merged in-process rather than called as a second deployed service, to avoid a network-hop failure point during live demos), runs the 3-judge tribunal, and resolves the escrow on-chain. Also exposes `GET /api/latest_escrow` so the frontend can auto-detect the active escrow instead of requiring manual ID entry.
- **AI Integration (Groq API)**: `llama-3.1-8b-instant` via the OpenAI-compatible client. `GROQ_API_KEY` is set both locally and on Render.
- **Frontend Dashboard (`index.html`)**: "Requester Agent" panel auto-populates from the latest active on-chain escrow (ID, amount, task description) on page load — no manual input. "Data Provider Agent" panel is a single "Fulfill Request" button; after each fulfillment it automatically re-polls for the next active escrow.
- **OKX.AI Registration**: Installed the OKX `onchainos` CLI, verified the developer wallet via OTP, uploaded a generated avatar to the OKX CDN, and minted the official ASP identity on the blockchain.
  - **Official Agent ID:** `6498`
  - **Registration Transaction Hash:** `0x8c4b923f15eac05b7afbf52d3096eb919e37c663dda08772fae5117ba6fb1116`
  - **Description** updated via `onchainos agent update` to match the pivot: *"AI tribunal that verifies live-fetched web data before releasing on-chain escrow payments — X Layer."* (update tx `0xb55cabd9825344221f43980d873089de13a685afb6945e3cbfe2c94010c9fdb9`). Name (`Verity Protocol`) and avatar were left unchanged.
  - Updating the identity required installing and initializing the `okx-a2a` daemon (`npm i -g @okxweb3/a2a-node` + `okx-a2a doctor --fix`) — it's now running locally with systemd autostart configured, which incidentally is also the exact prerequisite for the "A2A Integration" roadmap item below. It wasn't reachable from a sandboxed shell (npm registry egress was blocked); needed running outside that restriction.
- **Demo script** (`DEMO_SCRIPT.md`): ~3 minute walkthrough tied to the live UI, pre-demo checklist (warm up Render's cold start, fund a fresh escrow, don't rely on live-triggering the bot-wall reject case), and anticipated judge Q&A.

## 4. Current Project State & How it Works
The pivoted flow is **built, deployed to Render, and verified end-to-end in production** on X Layer testnet, both outcomes:
- **Reject path** (escrow #18, local testing): task pointed at a CoinGecko webpage that served a Cloudflare bot-check page. All 3 judges correctly caught it as blocked/error content and rejected — payer refunded on-chain (`tx 5d9ad59c81125343e12ddf800ccebb7fbb3c2ac2426cfec462a9462f83567121`).
- **Approve path** (escrow #24, live on Render): task pointed at CoinGecko's public JSON price API instead. Clean fetch, all 3 judges approved, funds released (`tx 18153b592e3b969a437ca59d1a1ec4b13bf585f66d58469ba11c47540a52ee23`).

Fixed along the way:
- `create_test_escrow.py` was calling a nonexistent `escrowCounter()` (the contract's counter is `nextEscrowId`).
- Playwright's `networkidle` wait hung indefinitely on CoinGecko's web page — switched to `domcontentloaded` + fixed settle window.
- A fetch failure used to abort before ever calling `resolveEscrow`, permanently locking the escrow's funds — now it resolves as an automatic reject/refund instead.
- A frontend `DOMContentLoaded` listener never fired because `app.js` loads via a `<script>` tag at the end of `<body>`, by which point that event has already passed — fixed with a `document.readyState` guard.
- Render's build successfully downloaded Chromium, but the runtime container couldn't find it — Render's native Python build/runtime don't reliably share the default `~/.cache/ms-playwright` path. Fixed by setting `PLAYWRIGHT_BROWSERS_PATH=0` on Render, which co-locates the browser binaries with the installed package instead.

**Known operational quirk:** Render's free tier cold-starts after inactivity — first request can take ~55s vs ~3-5s warm. Worth pinging the service a few minutes before any live demo.

**Tech Stack:**
- **Blockchain:** OKX X Layer Testnet (`https://testrpc.xlayer.tech`)
- **Backend:** Python (FastAPI, Web3.py, AsyncOpenAI wrapper, Playwright + BeautifulSoup + markdownify), deployed on Render
- **AI Inference:** Groq API (`llama-3.1-8b-instant`)
- **Frontend:** Vanilla HTML/CSS/JS
- **Agent Identity/A2A:** OKX `onchainos` CLI + `okx-a2a` daemon (installed, running, autostart configured)

## 5. Next Steps / Handoff
Everything from the original pivot punch list is done: Render deployment, frontend auto-detect, demo script, and on-chain identity description are all live and verified. Remaining items are genuinely optional/longer-term:
1. **A2A Integration**: The `okx-a2a` daemon is now installed and running — the actual work of wiring direct peer-to-peer Agent negotiation through it (instead of the web dashboard) hasn't been built yet.
2. **Dynamic Personas**: Expanding the tribunal to dynamically generate judge roles based on the specific data request, rather than 3 fixed roles.
3. **ASP listing/approval**: The on-chain identity currently shows `status: not listed` / `Review not submitted` — worth checking whether submitting for review/listing matters for hackathon judging visibility.
5. **Dynamic Personas (longer-term)**: Expanding the tribunal to dynamically generate judge roles based on the specific data request, rather than 3 fixed roles.
