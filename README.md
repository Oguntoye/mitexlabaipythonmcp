# mitexlabaipythonmcp

Aggregated MCP (Model Context Protocol) HTTP server for Mitexlab integrations. Mounts WhatsApp, Instagram, Google Workspace, and Mailer tool servers behind a single FastMCP endpoint.

Node appcore connects via `PYTHONAICOREURL` with `Authorization: Bearer ${MCPKEY}`.

## Repository layout

```
mitexlabaipythonmcp/
  main.py                 # Entry point (used by PM2 in production)
  src/
    main.py               # Builds and runs the FastMCP server
    env.py                # Root settings
  packages/
    mitexlab_whatsappmcp/
    mitexlab_instagrammcp/
    mitexlab_googlemcp/
    mitex_mailer_mcp/
```

Mounted MCP prefixes:

| Prefix | Package |
|--------|---------|
| `/googlemcp` | Google Workspace tools |
| `/instagrammcp` | Instagram tools |
| `/whatsappmcp` | WhatsApp tools |
| `/mailermcp` | Email tools |

There is no compile step. Python runs source directly via `uv`.

## Prerequisites

- Python **3.13** (see `.python-version`)
- [uv](https://docs.astral.sh/uv/) package manager
- Redis (all packages use `REDISHOST` / `REDISPORT`)
- A `.env` file at the repo root

## Environment variables

Copy [`.env.example`](.env.example) to `.env` in the repo root. All packages read from the same file. See [SECURITY.md](SECURITY.md) for credential handling.

### Root (`src/env.py`)

| Variable | Description |
|----------|-------------|
| `MCPPORT` | Port the server listens on (e.g. `8000`) |
| `WHICHENV` | Environment label (e.g. `local`, `staging`, `live`) |
| `MCPKEY` | Bearer token for MCP auth (must match Node appcore `MCPKEY`) |
| `REDISHOST` | Redis host |
| `REDISPORT` | Redis port |

### WhatsApp (`packages/mitexlab_whatsappmcp`)

| Variable | Description |
|----------|-------------|
| `WA_APP_ID` | WhatsApp app ID |
| `WA_APP_SECRET` | WhatsApp app secret |

Instagram, Google, and Mailer packages also require `WHICHENV`, `REDISHOST`, and `REDISPORT`.

Example:

```env
MCPPORT=8000
WHICHENV=local
MCPKEY=your-secret-key
REDISHOST=127.0.0.1
REDISPORT=6379
WA_APP_ID=your-app-id
WA_APP_SECRET=your-app-secret
```

If required variables are missing, startup prints validation errors and exits.

## Local setup

```bash
cd mitexlabaipythonmcp

# Install uv if needed:
# curl -LsSf https://astral.sh/uv/install.sh | sh

uv sync

# Optional: include dev tools (mypy)
uv sync --group dev
```

Ensure Redis is running and `.env` exists before starting the server.

## Running locally

### Production-style start

```bash
uv run python main.py
```

Server listens on `http://0.0.0.0:${MCPPORT}`.

Health check (no auth required):

```bash
curl http://localhost:8000/health
# {"status":"healthy","version":"1.0.11"}
```

### Dev with auto-reload and mypy

Watches `src/` and `packages/`. Runs mypy before each restart.

```bash
uv run python _dev.py
```

### Dev with auto-reload only

```bash
uv run python _simpledev.py
```

### Other commands

```bash
# Typecheck (CI runs this on src/)
uv run mypy src

# Sync after dependency changes
uv sync --frozen
```

## Node appcore integration

Point appcore at this server:

```env
PYTHONAICOREURL=http://localhost:8000
MCPKEY=your-secret-key
```

`MCPKEY` must match the value in this repo's `.env`.

## Deployment (VPS + PM2)

Deploys automatically on push to **`main`** via `.github/workflows/deploy.yml`.

Flow:

1. CI runs `uv sync --frozen --no-dev` and `uv run mypy src`
2. Source is zipped and copied to the VPS
3. On the server: `uv sync --frozen --no-dev`, symlink shared `.env`, flip `current` symlink
4. PM2 reloads the process
5. Health check: `curl http://localhost:${MCPPORT}/health`

### VPS layout

```
~/apps/mitexlabaipythonmcp/
  shared/.env              # permanent env (not in deploy zip)
  current/                 # symlink → latest release
  releases/
    <timestamp>/           # each deploy
      main.py
      src/
      packages/
      .venv/
      .env → ../shared/.env
```

### PM2 config (on the server only)

PM2 is configured on the VPS at **`~/ecosystem.config.js`**, not in this repo. Add an entry like:

```javascript
// ~/ecosystem.config.js (on VPS — merge with your other apps)
module.exports = {
  apps: [
    {
      name: "mitexlabaipythonmcp",
      cwd: "/home/deployer/apps/mitexlabaipythonmcp/current",
      script: ".venv/bin/python",
      args: "main.py",
      interpreter: "none",
      autorestart: true,
      max_restarts: 5,
    },
  ],
};
```

First-time setup:

```bash
mkdir -p ~/apps/mitexlabaipythonmcp/shared
# edit ~/apps/mitexlabaipythonmcp/shared/.env (include MCPPORT)

# After adding the entry above to ~/ecosystem.config.js:
pm2 start ~/ecosystem.config.js --only mitexlabaipythonmcp
pm2 save
```

Process runs as:

```bash
cd ~/apps/mitexlabaipythonmcp/current
.venv/bin/python main.py
```

GitHub secrets required: `VPS_HOST`, `VPS_SSH_KEY`.

## Local vs production

| | Local | Production |
|--|-------|------------|
| Install | `uv sync` | `uv sync --frozen --no-dev` |
| Run | `uv run python main.py` or `_dev.py` | PM2: `.venv/bin/python main.py` |
| Env | `./.env` | `~/apps/mitexlabaipythonmcp/shared/.env` |
| Artifact | None (run source) | Zip of source |
| Auto-deploy | — | Push to `main` |
