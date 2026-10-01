# Linux Deployment Server

An enterprise-ready starter for a Linux deployment and reporting server. This project provides:

- a local menu-driven deployment launcher on the machine
- a built-in Flask web dashboard for deployment activity and reports
- background deployment execution with status tracking
- distro-specific deployment scripts for Ubuntu, Debian, Rocky Linux, and Fedora
- inventory tracking for target systems
- a sample reporting interface for operations teams

## Features

- Multi-distro deployment menu
- Queue-based deployment jobs
- Web UI for deployment and inventory reporting
- SQLite-backed job storage
- Local TUI menu launcher
- pluggable distro scripts for custom deployment logic

## Project layout

- `app.py` — Flask web app and deployment engine
- `menu.py` — local terminal menu for launching deployments
- `scripts/` — OS-specific deployment scripts
- `templates/` — dashboard and report pages
- `static/style.css` — dashboard styling

## Quick start

1. Create a Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Make scripts executable:

```bash
chmod +x scripts/*.sh
```

4. Start the deployment server:

```bash
python3 app.py
```

5. Open the dashboard in your browser:

```text
http://localhost:5000/
```

6. Launch the local menu-driven deploy tool:

```bash
python3 menu.py
```

## Example deployment API

Trigger a deployment:

```bash
curl -X POST http://localhost:5000/api/deploy \
  -H "Content-Type: application/json" \
  -d '{"distro":"ubuntu","target_host":"web-01"}'
```

Get jobs:

```bash
curl http://localhost:5000/api/jobs
```

## Default distros

- ubuntu
- debian
- rocky
- fedora

## Production notes

This is a starter enterprise deployment server designed for internal operations teams. For production use, you would typically add:

- user authentication and RBAC
- queue persistence and scheduler
- actual PXE or imaging workflow integration
- secure secret handling
- systemd service configuration
- remote host inventory polling
- real automation templates (Kickstart, preseed, autoinstall, Ansible)

## License

MIT
