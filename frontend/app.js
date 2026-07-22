const API_BASE = 'https://agent-tribunal.onrender.com';

function weiToOkb(weiString) {
    // Display-only conversion (testnet demo amounts are small) — not used for any on-chain math.
    return (Number(BigInt(weiString)) / 1e18).toString();
}

async function loadLatestEscrow() {
    const escrowIdInput = document.getElementById('escrowIdInput');
    const lockedAmount = document.getElementById('lockedAmount');
    const taskDescDisplay = document.getElementById('taskDescDisplay');
    const submitBtn = document.getElementById('submitBtn');

    try {
        const response = await fetch(`${API_BASE}/api/latest_escrow`);
        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${response.status}`);
        }
        const data = await response.json();

        escrowIdInput.value = data.escrow_id;
        lockedAmount.textContent = `${weiToOkb(data.amount_wei)} OKB`;
        taskDescDisplay.textContent = `"${data.task_description}"`;
        submitBtn.disabled = false;
        submitBtn.textContent = 'Fulfill Request';
    } catch (err) {
        lockedAmount.textContent = '—';
        taskDescDisplay.textContent = `No active escrow found (${err.message}). Fund one with create_test_escrow.py, then reload.`;
        submitBtn.disabled = true;
        submitBtn.textContent = 'No Active Escrow';
    }
}

// app.js loads via a <script> tag at the end of <body>, so the DOM (and DOMContentLoaded)
// is already past by the time this runs — a listener here would never fire.
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadLatestEscrow);
} else {
    loadLatestEscrow();
}

document.getElementById('workForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const submitBtn = document.getElementById('submitBtn');
    const arbiterStatus = document.getElementById('arbiterStatus');
    const aiLoader = document.getElementById('aiLoader');
    const aiResult = document.getElementById('aiResult');

    // UI State: Submitting
    submitBtn.disabled = true;
    submitBtn.textContent = "Fetching...";

    // UI State: Arbiter Analyzing
    setTimeout(() => {
        submitBtn.textContent = "Request Fulfilled";
        arbiterStatus.textContent = "Agents Voting...";
        arbiterStatus.className = "tag warning";
        aiLoader.classList.remove('hidden');
        aiResult.classList.add('hidden');
    }, 500);

    try {
        // Call our Python FastAPI backend
        const escrowIdValue = parseInt(document.getElementById('escrowIdInput').value, 10);
        const response = await fetch(`${API_BASE}/api/fulfill_request`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                escrow_id: escrowIdValue
            })
        });

        const data = await response.json();

        aiLoader.classList.add('hidden');
        aiResult.classList.remove('hidden');
        
        const title = document.getElementById('verdictTitle');
        const reason = document.getElementById('verdictReason');
        const txLink = document.getElementById('txLink');
        const judgesContainer = document.getElementById('judgesContainer');
        const scrapedPreview = document.getElementById('scrapedPreview');
        
        if(data.is_approved) {
            title.textContent = "Approved & Funds Released";
            title.style.color = "var(--okx-green)";
            arbiterStatus.textContent = "Resolved (Success)";
            arbiterStatus.className = "tag success";
        } else {
            title.textContent = "Rejected - Funds Refunded";
            title.style.color = "var(--danger)";
            arbiterStatus.textContent = "Resolved (Failed)";
            arbiterStatus.className = "tag warning";
        }
        
        reason.textContent = data.feedback;
        txLink.textContent = data.tx_hash;
        txLink.href = "https://www.okx.com/explorer/xlayer-test/tx/" + data.tx_hash;

        // Render the scraped data the Data Provider Agent actually fetched (textContent only — this is
        // untrusted third-party page content and must never be interpreted as HTML).
        if (scrapedPreview) {
            scrapedPreview.textContent = data.source_url
                ? `[${data.scraped_title || 'Untitled'}] ${data.source_url}\n\n${data.scraped_preview || ''}`
                : '';
        }

        // Render individual judges
        judgesContainer.innerHTML = '';
        if (data.judges) {
            data.judges.forEach(j => {
                const card = document.createElement('div');
                card.className = `judge-card ${j.approved ? 'approved' : 'rejected'}`;

                const header = document.createElement('div');
                header.className = 'judge-header';

                const nameSpan = document.createElement('span');
                nameSpan.textContent = j.judge_name;

                const verdictSpan = document.createElement('span');
                verdictSpan.style.color = j.approved ? 'var(--okx-green)' : 'var(--danger)';
                verdictSpan.textContent = j.approved ? 'PASS' : 'FAIL';

                header.appendChild(nameSpan);
                header.appendChild(verdictSpan);

                const feedback = document.createElement('div');
                feedback.className = 'judge-feedback';
                feedback.textContent = j.feedback;

                card.appendChild(header);
                card.appendChild(feedback);
                judgesContainer.appendChild(card);
            });
        }

        // This escrow is now resolved — pull in whatever the next active one is (if any)
        // so the demo can chain straight into another fulfillment without a page reload.
        submitBtn.disabled = true;
        loadLatestEscrow();

    } catch (err) {
        alert("Error connecting to Verity backend: " + err);
        submitBtn.disabled = false;
        submitBtn.textContent = "Fulfill Request";
    }
});
