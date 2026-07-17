import os
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
from mcp.server import Server
from mcp.server.sse import SseServerTransport

load_dotenv()

app = FastAPI(title="Verity Protocol ASP")

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
gemini_api_key = os.getenv("GEMINI_API_KEY")

openai_client = AsyncOpenAI(
    api_key=gemini_api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
) if gemini_api_key else None
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
    }
]

class WorkSubmission(BaseModel):
    escrow_id: int
    worker_address: str
    work_payload: str

class JudgeVote(BaseModel):
    judge_name: str
    approved: bool
    feedback: str

class EvaluationResult(BaseModel):
    escrow_id: int
    is_approved: bool
    feedback: str
    judges: list[JudgeVote]
    tx_hash: str

# ----------------- Core Logic -----------------
async def _process_submission(escrow_id: int, worker_address: str, work_payload: str) -> dict:
    if not private_key or not contract_address or not os.getenv("GEMINI_API_KEY"):
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

    async def evaluate_with_role(role_name: str, system_instruction: str) -> JudgeVote:
        prompt = f"""
        You are part of the Verity Protocol, an AI consensus tribunal for an escrow smart contract.
        Your Specific Role: {role_name}
        {system_instruction}
        
        Task Description: {task_description}
        Worker's Submission: {work_payload}
        
        Return a JSON object with exactly two keys:
        "approved": boolean (true if the work passes your specific criteria, false if it fails)
        "feedback": string (a short 1-sentence reason focusing ONLY on your specific role's criteria)
        """
        try:
            response = await openai_client.chat.completions.create(
                model="gemini-2.0-flash",
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
        ("Security & Correctness Auditor", "Focus strictly on whether the logic/work is fundamentally correct, accurate, and secure. Reject if there are logical flaws, inaccuracies, or security risks."),
        ("Requirements & Completeness Analyst", "Focus strictly on whether the submission meets every single requirement asked for in the task description. Reject if anything is missing, no matter how small."),
        ("Quality & Maintainability Expert", "Focus on style, edge cases, readability, and overall professional quality. Reject if the work is sloppy, poorly formatted, or lacks polish.")
    ]

    try:
        judges_results = await asyncio.gather(*(evaluate_with_role(name, instr) for name, instr in roles))
    except Exception as e:
        raise Exception(f"Consensus evaluation failed: {str(e)}")

    approved_count = sum(1 for j in judges_results if j.approved)
    is_approved = approved_count >= 2
    overall_feedback = f"Consensus reached: {approved_count}/3 judges approved the submission."

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
            name="evaluate_submission",
            description="Evaluates a worker's submission against an active escrow task on X Layer. Uses the Verity Protocol multi-agent consensus panel. If 2 out of 3 AI judges approve, it automatically releases funds onchain.",
            inputSchema={
                "type": "object",
                "properties": {
                    "escrow_id": {"type": "integer"},
                    "worker_address": {"type": "string"},
                    "work_payload": {"type": "string"}
                },
                "required": ["escrow_id", "worker_address", "work_payload"]
            }
        )
    ]

@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    if name == "evaluate_submission":
        try:
            result = await _process_submission(arguments["escrow_id"], arguments["worker_address"], arguments["work_payload"])
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
@app.post("/api/submit_work", response_model=EvaluationResult)
async def submit_work(submission: WorkSubmission):
    try:
        result = await _process_submission(submission.escrow_id, submission.worker_address, submission.work_payload)
        return EvaluationResult(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
