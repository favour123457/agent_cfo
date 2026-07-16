document.getElementById('workForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const payload = document.getElementById('workPayload').value;
    const submitBtn = document.getElementById('submitBtn');
    const arbiterStatus = document.getElementById('arbiterStatus');
    const aiLoader = document.getElementById('aiLoader');
    const aiResult = document.getElementById('aiResult');
    
    if(!payload) {
        alert("Please enter some work payload");
        return;
    }

    // UI State: Submitting
    submitBtn.disabled = true;
    submitBtn.textContent = "Submitting...";
    
    // UI State: Arbiter Analyzing
    setTimeout(() => {
        submitBtn.textContent = "Work Submitted";
        arbiterStatus.textContent = "Agents Voting...";
        arbiterStatus.className = "tag warning";
        aiLoader.classList.remove('hidden');
        aiResult.classList.add('hidden');
    }, 500);

    try {
        // Call our Python FastAPI backend
        const response = await fetch('http://127.0.0.1:8000/api/submit_work', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                escrow_id: 1,
                worker_address: "0xWorker...",
                work_payload: payload
            })
        });

        const data = await response.json();

        aiLoader.classList.add('hidden');
        aiResult.classList.remove('hidden');
        
        const title = document.getElementById('verdictTitle');
        const reason = document.getElementById('verdictReason');
        const txLink = document.getElementById('txLink');
        const judgesContainer = document.getElementById('judgesContainer');
        
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

        // Render individual judges
        judgesContainer.innerHTML = '';
        if (data.judges) {
            data.judges.forEach(j => {
                judgesContainer.innerHTML += `
                    <div class="judge-card ${j.approved ? 'approved' : 'rejected'}">
                        <div class="judge-header">
                            <span>${j.judge_name}</span>
                            <span style="color: ${j.approved ? 'var(--okx-green)' : 'var(--danger)'}">
                                ${j.approved ? 'PASS' : 'FAIL'}
                            </span>
                        </div>
                        <div class="judge-feedback">${j.feedback}</div>
                    </div>
                `;
            });
        }
        
    } catch (err) {
        alert("Error connecting to Verity backend: " + err);
        submitBtn.disabled = false;
        submitBtn.textContent = "Submit to Verity";
    }
});
