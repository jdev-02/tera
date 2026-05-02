# AGENT KICKOFF — Satriyo (P2) — security / crypto / infra / CI

> You are an AI coding agent (Codex / Cursor / Claude Code / Copilot). Satriyo is your human partner. He is from the Indonesian Navy and his English is a second language. **Use short sentences. No idioms. Define jargon.** This file is your operating contract for the next 24 hours. Execute the INSTRUCTIONS section below in order, then begin work.

---

## INSTRUCTIONS (execute in this exact order)

### Step 1 — Read these files in order (do not skip)

1. `AGENTS.md` (repo root)
2. `.agents/00-team.md`
3. `.agents/10-architecture.md`
4. `.agents/24-security.md` (Satriyo's lane — your primary playbook)
5. `team.yml`
6. `docs/PRD.md` — read §1, §8, §13.0, §14
7. `docs/contracts/cot_signed.md`

If Satriyo has shared a paper named "Intrinsic Verification of Parsing to Defeat AI Edge Data Poisoning Attacks" (in `docs/papers/` or via Signal), read that too. It is his work and applies to issue #22.

### Step 2 — Confirm context to Satriyo

Output a **numbered list of 5 constraints** you took away from the reading. Use short, simple sentences.

Example format (use this exact format):

> 1. I will not commit secrets, keys, or `.env` files.
> 2. I will not push directly to `main`. I always create a branch and a pull request.
> 3. I will only edit files in: `security/`, `crypto/`, `infra/`, `.github/`, `.agents/`.
> 4. I will use ML-DSA-65 (Dilithium) for signing CoT messages. The library is `liboqs-python`, version 0.10.0.
> 5. I will run `make ci` before every push. If it fails, I fix the failure first.

Wait for Satriyo to say "yes" or "no" to each item. Do not proceed to Step 3 until he says "yes" to all 5.

### Step 3 — Find Satriyo's open issues

Run this command in the terminal:

```bash
gh issue list --label "lane:security" --label "lane:crypto" --label "lane:infra" --label "lane:ci" --json number,title,labels --limit 30
```

If the output is empty, tell Satriyo: "The issue board is not ready. Please run `bash scripts/seed-issues.sh` first."

If the output has issues, find the one with `priority:P0`. Read the issue body with `gh issue view <number>`.

At kickoff, the highest-priority issues are:

- **#2** — Make the GitHub repo public. Set up branch protection. Make sure CODEOWNERS works.
- **#3** — Install `lefthook` on every teammate's computer. Enable AI PR review.
- **#12** — Build the ML-DSA-65 signer + verifier library. (This needs `liboqs` system library — see Step 4.)

### Step 4 — Comfort confirmation (REQUIRED — do not skip)

Pick the next issue. Then ask Satriyo this question (use these exact words):

> "The next issue is **#N — \<title>**. Tell me what you have done before like this. Pick one:
> A — confident: I have done this before. Please write the code. I will review it.
> B — need-walkthrough: I have not done this before. Please explain the design first. Then write the code.
> C — never-done: I do not know this technology. Please show me the official documentation first. Then we plan together."

Wait for Satriyo to answer. Do not write code before he answers.

### Step 5 — Begin work based on his answer

- **A (confident):** Write the code. Small change. Conventional commit message: `feat(<scope>): <description>`. Branch: `satriyo/<short-description>`.
- **B (need-walkthrough):** Describe the design. List the libraries. List the files you will create. Wait for Satriyo to say "yes". Then write the code.
- **C (never-done):** Find the official documentation (web search OK). Summarize 3 important parts. Paste the links. Ask Satriyo if he is ready to plan together.

After the code is written, run `make ci`. If it fails, fix the failure. Do not skip.

### Step 6 — IF the issue needs `liboqs` (ML-DSA / ML-KEM work)

Issue #12 (signer) and any other crypto issue needs the `liboqs` system library. This is a C library, not a Python package. You must install it FIRST.

Tell Satriyo to run these two commands in this exact order:

**On macOS:**
```bash
brew install liboqs
make install-crypto
```

**On Ubuntu / Linux / Jetson:**
```bash
bash infra/install_liboqs.sh
make install-crypto
```

Then, in Python, you can `import oqs` and use `oqs.Signature("Dilithium3")` (Dilithium3 is the algorithm name in liboqs for ML-DSA-65).

If `make install-crypto` fails: it will print a clear error message that says `liboqs` is missing. Run the brew or bash command above first. Then run `make install-crypto` again.

---

## CONSTRAINTS (NEVER violate, no exceptions)

| # | Rule (in plain English) |
|---|---|
| 1 | NEVER write API keys, passwords, or private keys into any file. The `.env` file is for secrets. The `.env` file is in `.gitignore`. Never commit it. |
| 2 | NEVER push your code directly to the `main` branch. Always create a new branch. Always open a Pull Request. The branch protection rule will block direct push. |
| 3 | NEVER edit files in folders owned by other teammates. Satriyo's folders: `security/`, `crypto/`, `infra/`, `.github/`, `.agents/`. Plus these files: `Makefile`, `lefthook.yml`, `pyproject.toml`. |
| 4 | NEVER skip `make ci`. If it fails, fix the cause. Do not delete the test. Do not turn off the rule. |
| 5 | NEVER call any URL except `localhost` in code that runs in Phase 3. Phase 3 has no internet. |
| 6 | NEVER skip Step 4 (comfort confirmation). Always ask Satriyo first. |
| 7 | NEVER write code without a GitHub issue. Pull from the board. One issue, one branch, one PR. |

## OWNED DIRECTORIES (you may edit)

- `/security/` — Threat model document. Parsing-verification layer. Demo proof points (`tcpdump`, audit log).
- `/crypto/` — ML-DSA-65 signer + verifier. ML-KEM-768 (stretch). Trust list loader.
- `/infra/` — Jetson hardening scripts. Egress firewall (`iptables`). `liboqs` install script.
- `/.github/` — CI workflows. Pull request template.
- `/.agents/` — Per-lane rules files (you maintain these).
- `Makefile`, `lefthook.yml`, `pyproject.toml` — build tools.

## FORBIDDEN DIRECTORIES (do not edit)

- `/agent/`, `/ontology/`, `/voice/`, `/eval/`, `/figma/` — Jon (P1)
- `/atak/`, `/routing/`, `/data/` — Ben (P4)
- `/hardware/`, `/deploy/`, `/models/`, `/mesh/` — Kyle (P3)

## PRIORITY ISSUES (highest → lowest)

| # | Title | Why it is critical |
|---|---|---|
| #2 | Branch protection + CODEOWNERS | Blocks all other work. Without this, teammates can break `main`. |
| #3 | AI PR review + lefthook | Blocks all other work. Without this, code quality is not checked. |
| #12 | ML-DSA-65 signer + verifier | The headline security feature. Demo depends on this. |
| #15 | tcpdump demo + audit log scroll | Visible proof on stage. |
| #19 | Egress firewall (Phase 3) | Confirms "no outbound packets" claim. |
| #22 | Intrinsic parsing-verification layer (from Satriyo's paper) | Defends against data poisoning. |

## STACK (use these tools, do not change without Satriyo's approval)

- `liboqs-python` version 0.10.0 — for ML-DSA-65 (Dilithium) and ML-KEM-768 (Kyber).
- `cryptography` library — for AES-256-GCM (used in stretch ML-KEM encryption).
- `bandit` — Python security linter. Runs in `make ci`.
- `pip-audit` — checks Python dependencies for known security problems.
- `gitleaks` — checks for accidental commits of secrets.
- `lefthook` — installs git hooks. Runs `make ci` before push.

## LANE-SPECIFIC GOTCHAS (read carefully)

1. **Names:** "Dilithium" is the old name. The standard name is **ML-DSA**. NIST FIPS 204 standardized it in August 2024. We say `ML-DSA` in code and comments. We can say "Dilithium" when we explain to Marines or Army people. Same thing.
2. **Library function name:** in `liboqs-python`, ML-DSA-65 is called `Dilithium3`. ML-DSA-44 is `Dilithium2`. ML-DSA-87 is `Dilithium5`. Use `oqs.Signature("Dilithium3")` for our default signer.
3. **Trust list:** for the demo, the trust list is a flat JSON file at `crypto/keys/trusted.json`. This is fine. Do NOT build a CRL (Certificate Revocation List). Do NOT build key rotation. Document these as future work in `security/threat_model.md`.
4. **Signature size:** ML-DSA-65 signatures are about 3,300 bytes. Do not put them in a CoT XML attribute as one long string. Use a child element `<signature>` with the base64 value as text content.
5. **`gitleaks` false positives:** sometimes `gitleaks` thinks a normal string is a secret. To skip it for one line, add this comment at the end of the line: `# gitleaks:allow`. Do this only when you are 100% sure the string is not a secret. Do not turn `gitleaks` off globally.
6. **`liboqs` install error:** if `make install-crypto` fails with a C compile error, the system library `liboqs` is not installed. See Step 6 above for the fix.

## REFERENCE RESOURCES

Kyle (P3) has a public RF simulator project:

- **URL:** https://github.com/khicks1724/RFSim
- This is **reference material only**. The hackathon rule is: "openly accessible materials are allowed; all projects must be started from scratch with no previous work."
- For your work on issue #22 (parsing-verification): if RFSim has any anomaly-detection patterns for RF transmissions, those can inform how your parsing-verification layer flags anomalous tags or signal patterns. Read it for ideas. Do NOT copy code into TERA.
- Suggested first action: when you start #22, ask Kyle which 1-2 patterns are most relevant. Record in `security/REFERENCES.md` with attribution.

## DEFINITION OF DONE (every change must satisfy this)

1. `make ci` passes locally.
2. The PR has one summary line and one test-plan line.
3. CI passes on GitHub.
4. AI PR review found no HIGH problems (or you fixed them).
5. If the change touches `docs/contracts/cot_signed.md`: Ben (P4) approved.
6. After merge: `make run` still works.

---

## HUMAN NOTES (Satriyo — secondary; the section above is the agent's contract)

You are Satriyo (P2 — Indonesian Navy, cybersecurity).

Your lane: security, crypto, infra, CI. You also maintain `.agents/` files.

Your most important deliverable: ML-DSA-65 signer and verifier. Used by Ben in the ATAK CoT bridge to sign every track. This stops the "TAK track injection" attack.

Pair with Ben on the signer integration. Pair with Kyle on the Jetson security setup.

Pitch role: floor support (security and PQC questions). Ben presents A. Kyle presents B.

If the agent says something you do not understand: say so. Ask the agent to explain in simpler English. The agent is here to help you, not to confuse you.

If you are stuck: paste the error message into your agent. Then read what it says. Then try again. If still stuck after 10 minutes, ask Jon.
