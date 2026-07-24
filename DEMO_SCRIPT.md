# Verity Protocol — Demo Script

Target: ~3 minutes live demo + Q&A buffer. Cut markers below show what to drop first if you're given less time.

---

## 0. Before you're on stage (do this ~10 min ahead, not during your slot)

1. **Warm up Render** — hit `https://agent-tribunal.onrender.com/api/latest_escrow` once. Free tier cold-starts take ~55s; you do not want that happening live.
2. **Fund a fresh escrow** — run `create_test_escrow.py` so there's an active, unresolved escrow ready. Each escrow can only be fulfilled once, and you don't want to discover mid-demo that the last one you tested with is already spent.
3. **Have the explorer tab pre-opened** to `https://www.okx.com/explorer/xlayer-test/address/<AgentEscrow contract address>` so you can flip to it instantly after the tx fires, instead of fumbling with a search box on stage.
4. **Don't rely on the reject-case (bot-wall) demo live.** CoinGecko's Cloudflare challenge is their infrastructure, not yours — it's not guaranteed to trigger on demand, and a live "well, it usually rejects garbage, let me try again" moment kills momentum. Take a screenshot or short screen recording of the earlier reject run now (tx `5d9ad59c81125343e12ddf800ccebb7fbb3c2ac2426cfec462a9462f83567121` on the explorer, plus the judge verdicts from that run) and have it ready as a static slide/backup instead.

---

## 1. The Hook (~25s)

> "AI agents are starting to pay each other for work — but if Agent A pays Agent B for data, how does Agent A know Agent B didn't just make it up, or scrape a broken page and call it done? Right now, that trust either doesn't exist, or it's a human checking invoices after the fact."

**[Cut first if short on time]** — you can skip straight to section 2 if needed.

---

## 2. What Verity Protocol Is (~25s)

> "Verity Protocol is a Verified Live-Data Feed ASP on OKX's X Layer. One agent requests real-world data — a live price, a page's current state — funds an on-chain escrow for it. A second agent, our Data Provider Agent, actually goes and fetches it. Before any money moves, a tribunal of three independent AI judges checks that what was fetched actually satisfies the request. Only then does the smart contract release funds — automatically, no human in the loop."

Key phrase to land: **"no human in the loop"** — this is the whole pitch. Escrow resolution is fully automated by verifiable AI judgment, not a person reviewing invoices.

---

## 3. Live Demo (~90s)

Walk through the actual dashboard at `agent-tribunal` frontend (or wherever you're hosting `index.html`).

1. **Point at the Requester Agent panel.** "This escrow is already funded — the Escrow ID, locked amount, and data request were all pulled live from X Layer, nobody typed them in." *(This is the auto-detect feature — call it out explicitly, it's what makes this look autonomous rather than a filled-in form.)*
2. **Point at the Data Request text.** Read it aloud: *"Fetch [URL] and report the current USD price of OKB."* — "That's the only instruction. No one tells the Data Provider Agent how to parse the page."
3. **Click "Fulfill Request."** While it's running (~10-25s): "Right now, our Data Provider Agent is actually launching a headless browser, fetching that URL live, and handing the result to three separate AI judges — a Fetch Integrity Auditor checking the fetch didn't hit an error or a bot-wall, a Relevance judge checking the data's actually in there, and a Sanity Checker catching anything that looks fabricated or stale."
4. **When results land:** point at the three judge cards — PASS/FAIL, one-line reasoning each. "3 out of 3 approved — consensus reached, and that's not decorative: watch what happens when it isn't clean data." *(cue the reject-case backup slide here)*
5. **Show the reject-case backup** (screenshot/recording from pre-demo prep): "This is a real run from testing — we pointed it at CoinGecko's regular webpage instead of their API, it happened to serve a bot-check page, and all three judges caught it and rejected. The payer got refunded automatically, on-chain, no one had to notice or intervene."
6. **Click the tx hash link** from the live approve-case run → explorer tab. "That's a real transaction, right now, on X Layer testnet, releasing escrow funds based purely on AI consensus."

**[Cut second if short on time]** — steps 2 and 5 are the first to trim; steps 3, 4, and 6 are the core proof and should stay.

---

## 4. Close (~25s)

> "The contract itself never changed — `taskDescription` is just a string, so this same escrow primitive can back any kind of verifiable agent-to-agent work, not just data feeds. What's novel here isn't 'AI judges a thing' — it's that the thing being judged is real, live, fetched on demand, and the escrow always resolves — approve or reject, funds always move, nothing gets stuck."

If you want to gesture at roadmap without over-promising:
> "Next: direct agent-to-agent negotiation over OKX's a2a daemon instead of a web form, and dynamic judge personas generated per request instead of three fixed roles."

---

## 5. Anticipated Judge Questions

**"What stops the Data Provider Agent from just lying about what it fetched?"**
The tribunal doesn't trust the provider's word — it independently re-evaluates the actual scraped content against the original request. The provider can't hand-wave a summary; the raw fetched data goes into the judge prompts directly.

**"Why not just use a price oracle?"**
Oracles work for a small set of pre-registered feeds. This works for *any* URL and *any* natural-language ask — a price, a headline, a page's live status — without needing that data source pre-integrated anywhere.

**"What happens if the fetch fails?"**
The escrow still resolves — automatically refunds the payer rather than leaving funds locked forever. We hit this for real during testing (a bot-walled page) and fixed exactly this failure mode: every request reaches finality, approve or reject.

**"Does this scale beyond one data source at a time?"**
Architecturally yes — nothing about the judge tribunal or the contract is single-source-specific. That's exactly the "dynamic personas" roadmap item: today it's 3 fixed roles, next is generating roles per request type.

**"What's your on-chain identity?"**
Registered via OKX's `onchainos` CLI — Agent ID `6498`, wallet-verified, avatar minted on-chain.

---

## Fallback plan if live demo breaks

If Render is unreachable, Groq is rate-limited, or the network flakes: fall back entirely to the pre-recorded approve-case run (escrow #24, tx `18153b592e3b969a437ca59d1a1ec4b13bf585f66d58469ba11c47540a52ee23`, live on X Layer testnet explorer) plus the reject-case screenshot. Narrate over the static screenshots using the same script above — judges care about the mechanism being real and proven, not that it's happening live in that exact second.
