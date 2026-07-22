import os
import re
import json
import asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response
from pydantic import BaseModel
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import markdownify
from mcp.server import Server
from mcp.server.sse import SseServerTransport

load_dotenv()

app = FastAPI(title="Verity Protocol ASP", description="Verified Live-Data Feed escrow for AI agents on X Layer.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect to X Layer Testnet
w3 = Web3(Web3.HTTPProvider("https://testrpc.xlayer.tech"))
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

private_key = os.getenv("ASP_PRIVATE_KEY")
groq_api_key = os.getenv("GROQ_API_KEY")

openai_client = AsyncOpenAI(
    api_key=groq_api_key,
    base_url="https://api.groq.com/openai/v1"
) if groq_api_key else None
contract_address = os.getenv("CONTRACT_ADDRESS")

escrow_abi = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "_escrowId", "type": "uint256"},
            {"internalType": "bool", "name": "_success", "type": "bool"}
        ],
        "name": "resolveEscrow",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "name": "escrows",
        "outputs": [
            {"internalType": "address", "name": "payer", "type": "address"},
            {"internalType": "address", "name": "payee", "type": "address"},
            {"internalType": "address", "name": "arbiter", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"},
            {"internalType": "string", "name": "taskDescription", "type": "string"},
            {"internalType": "bool", "name": "isFunded", "type": "bool"},
            {"internalType": "bool", "name": "isResolved", "type": "bool"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "nextEscrowId",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

LATEST_ESCROW_SCAN_LIMIT = 25

class FulfillRequest(BaseModel):
    escrow_id: int

class JudgeVote(BaseModel):
    judge_name: str
    approved: bool
    feedback: str

class EvaluationResult(BaseModel):
    escrow_id: int
    source_url: str
    scraped_title: str
    scraped_preview: str
    is_approved: bool
    feedback: str
    judges: list[JudgeVote]
    tx_hash: str

class LatestEscrow(BaseModel):
    escrow_id: int
    task_description: str
    amount_wei: str

URL_PATTERN = re.compile(r"https?://\S+")

# ----------------- Data Provider Agent (scrape logic) -----------------
async def fetch_url(url: str) -> dict:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            # "networkidle" hangs indefinitely on heavy SPAs with persistent analytics/websocket
            # traffic (e.g. CoinGecko never goes idle) — "domcontentloaded" + a fixed settle window
            # is far more reliable across arbitrary target sites.
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(2000)
            html_content = await page.content()
            title = await page.title()
        finally:
            await browser.close()

    soup = BeautifulSoup(html_content, 'html.parser')
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    content = markdownify.markdownify(str(soup), heading_style="ATX").strip()
    return {"title": title, "content": content}

# ----------------- Core Logic -----------------
async def _process_submission(escrow_id: int) -> dict:
    if not private_key or not contract_address or not os.getenv("GROQ_API_KEY"):
        raise Exception("Backend not fully configured (missing keys or contract address).")

    contract = w3.eth.contract(address=contract_address, abi=escrow_abi)

    try:
        escrow_data = contract.functions.escrows(escrow_id).call()
        task_description = escrow_data[4]
        is_funded = escrow_data[5]
        is_resolved = escrow_data[6]
        if not is_funded or is_resolved:
            raise Exception("Escrow is not active or already resolved.")
    except Exception as e:
        raise Exception(f"Failed to fetch escrow: {str(e)}")

    url_match = URL_PATTERN.search(task_description)
    if not url_match:
        raise Exception("Task description does not contain a fetchable URL.")
    source_url = url_match.group(0).rstrip(".,)")

    fetch_error = None
    try:
        fetched = await fetch_url(source_url)
        scraped_content = fetched["content"]
        scraped_title = fetched["title"]
    except Exception as e:
        # A fetch failure is still a verdict, not a dead end — the escrow must resolve
        # (refunding the payer) rather than being left stuck forever with locked funds.
        fetch_error = str(e)
        scraped_content = ""
        scraped_title = ""

    async def evaluate_with_role(role_name: str, system_instruction: str) -> JudgeVote:
        prompt = f"""
        You are part of the Verity Protocol, an AI consensus tribunal that verifies data fetched
        by a Data Provider Agent before an escrow smart contract releases payment.
        Your Specific Role: {role_name}
        {system_instruction}

        Data Request (from the requesting agent): {task_description}
        Source URL Fetched: {source_url}
        Page Title: {scraped_title}
        Scraped Content (truncated): {scraped_content[:4000]}

        Return a JSON object with exactly two keys:
        "approved": boolean (true if the fetched data satisfies your specific criteria, false if it fails)
        "feedback": string (a short 1-sentence reason focusing ONLY on your specific role's criteria)
        """
        try:
            response = await openai_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                response_format={ "type": "json_object" }
            )
            result = json.loads(response.choices[0].message.content)
            return JudgeVote(
                judge_name=role_name,
                approved=result.get("approved", False),
                feedback=result.get("feedback", "No feedback provided.")
            )
        except Exception as e:
            return JudgeVote(judge_name=role_name, approved=False, feedback=f"Judge failed: {str(e)}")

    roles = [
        ("Fetch Integrity Auditor", "Focus strictly on whether the fetch actually succeeded. Reject if the content looks like an error page, a CAPTCHA/block page, or is empty/near-empty."),
        ("Relevance & Completeness Analyst", "Focus strictly on whether the scraped content actually contains the specific data point(s) the data request asked for. Reject if the requested information is missing."),
        ("Accuracy & Sanity Checker", "Focus on whether the extracted data looks plausible and current (e.g. numeric where a number was requested, not an obviously stale placeholder or hallucinated value).")
    ]

    if fetch_error:
        judges_results = [
            JudgeVote(judge_name=name, approved=False, feedback=f"Fetch never happened: {fetch_error}")
            for name, _ in roles
        ]
        is_approved = False
        overall_feedback = f"Data Provider Agent failed to fetch the source: {fetch_error}"
    else:
        try:
            judges_results = []
            for name, instr in roles:
                judges_results.append(await evaluate_with_role(name, instr))
                await asyncio.sleep(1) # Groq handles rate limits better
        except Exception as e:
            raise Exception(f"Consensus evaluation failed: {str(e)}")

        approved_count = sum(1 for j in judges_results if j.approved)
        is_approved = approved_count >= 2
        overall_feedback = f"Consensus reached: {approved_count}/3 judges approved the fetched data."

    acct = w3.eth.account.from_key(private_key)
    try:
        nonce = w3.eth.get_transaction_count(acct.address)
        tx = contract.functions.resolveEscrow(escrow_id, is_approved).build_transaction({
            'from': acct.address,
            'nonce': nonce,
            'gas': 300000,
            'gasPrice': w3.eth.gas_price
        })
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        w3.eth.wait_for_transaction_receipt(tx_hash)

        return {
            "escrow_id": escrow_id,
            "source_url": source_url,
            "scraped_title": scraped_title,
            "scraped_preview": scraped_content[:1500],
            "is_approved": is_approved,
            "feedback": overall_feedback,
            "judges": [j.model_dump() for j in judges_results],
            "tx_hash": tx_hash.hex()
        }
    except Exception as e:
        raise Exception(f"Blockchain transaction failed: {str(e)}")

from mcp.server import Server
from mcp.server.sse import SseServerTransport
import mcp.types as types

# ----------------- MCP Server Setup -----------------
mcp_server = Server("VerityProtocol")
sse = SseServerTransport("/messages")

@mcp_server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="fulfill_data_request",
            description="Fulfills an active data-request escrow on X Layer: fetches the URL embedded in the escrow's task description, then runs the Verity Protocol multi-agent tribunal to verify the fetched data actually satisfies the request. If 2 out of 3 AI judges approve, it automatically releases funds onchain to the Data Provider Agent; otherwise the payer is refunded.",
            inputSchema={
                "type": "object",
                "properties": {
                    "escrow_id": {"type": "integer"}
                },
                "required": ["escrow_id"]
            }
        )
    ]

@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    if name == "fulfill_data_request":
        try:
            result = await _process_submission(arguments["escrow_id"])
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
        except Exception as e:
            return [types.TextContent(type="text", text=json.dumps({"error": str(e)}))]
    raise ValueError(f"Unknown tool: {name}")

@app.get("/sse")
async def handle_sse(request: Request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
        await mcp_server.run(streams[0], streams[1], mcp_server.create_initialization_options())
    return Response()

@app.post("/messages")
async def handle_messages(request: Request):
    await sse.handle_post_message(request.scope, request.receive, request._send)

# ----------------- REST API (For Web Demo) -----------------
@app.post("/api/fulfill_request", response_model=EvaluationResult)
async def fulfill_request(request: FulfillRequest):
    try:
        result = await _process_submission(request.escrow_id)
        return EvaluationResult(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/latest_escrow", response_model=LatestEscrow)
async def latest_escrow():
    if not contract_address:
        raise HTTPException(status_code=500, detail="Backend not fully configured (missing contract address).")

    contract = w3.eth.contract(address=contract_address, abi=escrow_abi)
    try:
        next_id = contract.functions.nextEscrowId().call()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read nextEscrowId: {str(e)}")

    oldest_id_to_check = max(-1, next_id - 1 - LATEST_ESCROW_SCAN_LIMIT)
    for escrow_id in range(next_id - 1, oldest_id_to_check, -1):
        try:
            escrow_data = contract.functions.escrows(escrow_id).call()
        except Exception:
            continue
        amount, task_description, is_funded, is_resolved = escrow_data[3], escrow_data[4], escrow_data[5], escrow_data[6]
        if is_funded and not is_resolved:
            return LatestEscrow(escrow_id=escrow_id, task_description=task_description, amount_wei=str(amount))

    raise HTTPException(status_code=404, detail=f"No active (funded, unresolved) escrow found in the last {LATEST_ESCROW_SCAN_LIMIT} escrows.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
