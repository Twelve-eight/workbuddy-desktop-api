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

## Notes for agent sessions

- `supervisor.py` child decode fix: child stdout is UTF-8 (`PYTHONIOENCODING=utf-8` set in spawn env); read with `encoding="utf-8", errors="replace"` - without this the tail thread dies with `UnicodeDecodeError: 'gbk' codec`.
- Processes started from an agent session get cleaned up when the session/hub ends - the user starts the window themselves; logs stay readable via `gateway.log`.