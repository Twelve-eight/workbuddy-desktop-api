# DEVLOG - workbuddy-desktop-api deployment (local WorkBuddy free-model gateway)

Path: `G:\omp works\workbuddy-desktop-api` (clone of Fly143/workbuddy-desktop-api, MIT)
Purpose: expose the logged-in Tencent WorkBuddy Desktop session as an OpenAI/Anthropic-compatible local API, so the free models (e.g. deepseek-v4.1-flash) are usable from omp / codex / any OpenAI client.

## Setup (done 2026-09-12)

- venv: `.venv` on G: (Python 3.14.7); deps installed via `cmd /c ".venv\Scripts\python.exe -m pip install -r requirements.txt"`.
  NOTE: MSYS bash cannot exec the venv python.exe directly ("command not found") - always invoke via `cmd /c` or `start.cmd`.
- Gateway: `start.cmd` (HOST=127.0.0.1, PORT=8080). Admin UI http://127.0.0.1:8080 (admin/admin), API key default `sk-workbuddy`.
- Session auto-imported from `%LOCALAPPDATA%\CodeBuddyExtension\Data\Public\auth\workbuddy-desktop-ai.info` (uid c3c6700e-a67a-4811-85cd-01599937a638, domain www.workbuddy.ai).

## Local patches (commit 765912c)

1. `app/workbuddy_session.py`: `AUTH_FILE_NAME = "workbuddy-desktop-ai.info"` (this machine's file has the `-ai` suffix).
2. `app/workbuddy_session.py`: `API_BASE = "https://www.workbuddy.ai"`, `DEFAULT_DOMAIN = "www.workbuddy.ai"`.
   Why: the WorkBuddy token is issued by realm `www.workbuddy.ai/auth/realms/copilot`; copilot.tencent.com returns 401 for it (probe: 401 vs 400/200 on www.workbuddy.ai).
3. `app/workbuddy_client.py` `_prepare_body`: force `messages[0].role == "system"` (upstream error 11128 otherwise), prepend default system message.
4. `app/routes.py` DESKTOP_MODELS: `deepseek-v4.1-flash` (upstream rejects `deepseek-v4-flash` with 11102).

## Verified (all via actual requests)

- `POST https://www.workbuddy.ai/v2/chat/completions` with local token + system-first + stream: hy3 / hy4-preview / auto / deepseek-v4.1-flash -> 200 SSE.
- Gateway `POST /v1/chat/completions` (stream + non-stream) model=deepseek-v4.1-flash -> "OK".
- `codex exec -c model_provider=workbuddy -c model=deepseek-v4.1-flash "Reply with exactly PONG"` -> PONG (hits gateway /v1/chat/completions 200).
- `omp -p --no-session --model=workbuddy/deepseek-v4.1-flash "Reply with exactly PONG"` -> PONG.
- NOTE: `codex exec --model workbuddy/...` (single flag) does NOT route custom providers in current codex - use `-c model_provider=` or omp `--model`.

## omp integration

- `~/.omp/agent/models.yml`: added provider `workbuddy` (baseUrl http://127.0.0.1:8080/v1, api openai-completions, apiKey WORKBUDDY_API_KEY, model deepseek-v4.1-flash) - source for omp model picker.
- `~/.codex/config.toml`: `[model_providers.workbuddy]` block appended (wire_api responses).
- `~/.codex/omp-model-catalog.json`: rebuilt (was truncated to 0 bytes during an editing accident) with 5 entries: tokenrhythm/deepseek-v4-flash-0731, workbuddy/deepseek-v4.1-flash, agentrouter/{deepseek-v4-flash,glm-5.3,gpt-5.6-sol}. Empty/absent catalog makes bare codex fail with "failed to parse model_catalog_json"; valid catalog restores it.
- Env: `setx WORKBUDDY_API_KEY sk-workbuddy` (new shells). Change key via admin API if needed: `curl -u admin:admin -X POST http://127.0.0.1:8080/api/config -d '{"api_keys":"sk-new"}'`.

## Ops

- **Start (user-side): double-click `gateway-window.cmd`** - opens a visible status window:
  - shows live gateway logs (`[gw]` lines), status line every 30s: `[STATUS] RUNNING pid=... port=8080 open=...`
  - commands: `r`=restart, `s`=stop, `c`=clear screen, `q`=quit (stops child), `?`=help
  - logs are ALSO tee'd to `gateway.log` in the repo root (rotates at 5 MB -> gateway.log.1) - readable from outside the window
- **Autostart:** `install-svc.cmd` copies `WorkBuddyGateway.cmd` into the user Startup folder (no admin needed; schtasks ONLOGON needs elevation on this machine, so this is the chosen mechanism) and opens the window now. `uninstall-svc.cmd` removes the entry.
- Gateway must be running whenever omp uses workbuddy models. If port 8080 is already busy, a second window refuses to spawn a duplicate (`r` force-restarts only its own child).
- Session token refresh is handled inside the gateway (refreshToken in the Desktop info file).
- Accounts: WorkBuddy free quota models; heavy use hits rate limits (upstream 429) - gateway surfaces errors as-is.

## BUGFIX 2026-09-12: deepseek-v4.1-flash "no body output" in omp

**Symptom (user):** v4.1 in omp shows only grey reasoning text, no body; folding the reasoning block leaves nothing; a single call runs for minutes; session history is not persisted; same request sometimes answered twice. Other providers/models fine.

**Root cause (proven by probes):** upstream `www.workbuddy.ai/v2/chat/completions` on **deepseek-v4.1-flash** with ANY `tools` in the body switches to tool-call mode: `reasoning_content` streams, `content` stays 0, hundreds of `tool_calls` chunks, `finish_reason=tool_calls`. `tool_choice="none"` is IGNORED (probe: tools+none -> 82 toolcall chunks, finish=tool_calls). Without tools: content 3864-4817 chars, finish=stop, clean `[DONE]`. omp is an agent and ALWAYS sends tools -> gateway passed them through -> upstream tool loop (omp re-sends the same truncated query, never gets body, call hangs, session never persists; omp's retry then duplicates responses).

**Fix:** `app/routes.py` `chat_completions` - strip `tools_dict` for models whose name starts with `deepseek-v4.1` (tools execute client-side in the agent; upstream only needs to generate text).

**Verified (patched gateway, model=deepseek-v4.1-flash + tools):**
- probe via gateway 8080: `content=13..4067`, `toolcall_chunks=0`, `finish=stop`, `[DONE]` received.
- control: hy3 + tools unchanged (content 4005, finish=stop).
- real omp: `omp -p --model=workbuddy/deepseek-v4.1-flash "维也纳是哪个国家的首都?"` -> "奥地利.维也纳是奥地利的首都." in 4.9s; second run "蒙娜丽莎的作者" -> answered in 5.3s, session file updated (workbuddy model lines present).

**Probe scripts (all removed after use):** `_probe_effort.py` (no-effort vs high-effort field distribution), `_probe_tools.py` / `_probe_tc.py` (tools variants), `_verify_fix.py` (patched gateway check).

## Notes for agent sessions

- `supervisor.py` child decode fix: child stdout is UTF-8 (`PYTHONIOENCODING=utf-8` set in spawn env); read with `encoding="utf-8", errors="replace"` - without this the tail thread dies with `UnicodeDecodeError: 'gbk' codec`.
- Processes started from an agent session get cleaned up when the session/hub ends - the user starts the window themselves; logs stay readable via `gateway.log`.

## RETIREMENT 2026-09-12: full migration to CangShui workbuddy-gateway

User switched omp to CangShui's gateway (`G:\cangshuiworkbuddygateway\workbuddy-gateway-windows-amd64.exe serve`, port 8317, creds in its own `workbuddy.json`). This repo's 8080 gateway is no longer used by omp.

**omjp wiring (final):** `~/.omp/agent/models.yml` workbuddy provider -> `baseUrl: http://127.0.0.1:8317/v1`, model `deepseek-v4.1-flash` (passthrough; the listed `deepseek-v4-flash` id returns upstream 11102 "service info not found"). NO `thinking:` block - adding one made omp hang; plain `reasoning: true` works. Desktop script `I:\Desktop\omp-workbuddy.cmd` now launches the CangShui binary. Verified: simple task 5s, full agent task (read + summarize) 9.7s.

## Retrospective: why OUR gateway had the problems

The definitive difference is architectural. CangShui (and lovingfish/workbuddy-cliproxy) are **stateless transparent relays**: pass model & stream through, fix only auth. Our 8080 gateway **reconstructed the stream** - and every layer of that reconstruction produced a distinct failure:

1. **Text-prompt assembly instead of passthrough.** We concatenated messages into a plain-text `query` (roles flattened to "user: / assistant: / tool: [tool_result id=..]"), embedding tool schemas as prose. That removed the structured tool_calls contract; the "tool loop" we then diagnosed was partly an artifact of that flattening, and our "fix" (strip tools) leaked DSML text when omp's agent prompt still demanded tool use.

2. **Stream reconstitution (THINK_OPEN/THINK_CLOSE wrapping).** We pulled `reasoning_content` out of deltas, wrapped it as ` " thinking..response"` text, re-parsed it out, buffered content, then re-emitted reasoning_content. Every hop is a lossy transform; the correct invariants (reasoning stays in reasoning_content, content stays in content, tool_calls stay structured, finish_reason arrives on the terminal chunk) were each violated or at risk. omp's consumer (openai-completions.ts) strictly requires `finish_reason` and does not understand non-standard delta shapes.

3. **Hardcoded `reasoning_effort=medium`.** Probes proved: with tools, effort=medium made upstream emit content=0 (body eaten by reasoning); CangShui's applyThinkingRules documents the CodeBuddy contract - only forward effort when the client explicitly set it, use `reasoning_summary=auto`, DELETE on off/none. We overrode omp's real effort instead of relaying it.

4. **QueryGuard truncation at 102K.** The 102K window is upstream's trainer-set cap; our truncation dropped early tool round-trips and made the model re-read files (amnesia loop). Compression of tool results helped but treated the symptom of assembling oversized queries at all.

5. **Wrong-dimension "fixes".** strip-tools (commit 4f3228b) misread a normal tool-use turn as a loop; raising the window to 1MB (reverted) contradicted the real 102K cap. The churn itself is the lesson: when a transparent relay exists upstream, don't build a smart middlebox.

**What CangShui does right:** model passthrough, request passthrough (messages/tools/reasoning as-is), SSE passthrough with only empty-field cleanup, account pool + cooldown/auth refresh. It has no query builder, no think-tag parsing, no content buffering. That is the correct shape for this upstream.

**Lessons for future proxies:** relay wire formats unmodified; never convert structured tool_calls/reasoning to text and back; honor client effort parameters (or delete them); keep the gateway stateless unless the upstream forces state.