import json
import os
import sqlite3
import subprocess
import threading
from datetime import datetime
from typing import Dict, List, Optional

from flask import Flask, render_template, request, jsonify

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "deployments.db")
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
SUPPORTED_DISTROS = ["ubuntu", "debian", "rocky", "fedora"]
TERMINAL_STATUSES = {"success", "failed", "cancelled"}

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["DATABASE"] = DB_PATH


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    os.makedirs(SCRIPTS_DIR, exist_ok=True)
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS deploy_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            distro TEXT NOT NULL,
            target_host TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued',
            details TEXT DEFAULT '',
            exit_code INTEGER,
            started_at TEXT,
            ended_at TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hostname TEXT NOT NULL UNIQUE,
            distro TEXT,
            ip_address TEXT,
            status TEXT NOT NULL DEFAULT 'unknown',
            last_seen TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )

    seed_inventory = [
        ("edge-01", "ubuntu", "10.10.10.11", "online"),
        ("edge-02", "debian", "10.10.10.12", "online"),
        ("web-01", "rocky", "10.10.10.21", "online"),
        ("db-01", "fedora", "10.10.10.31", "online"),
    ]
    for hostname, distro, ip, status in seed_inventory:
        conn.execute(
            """
            INSERT OR IGNORE INTO inventory (hostname, distro, ip_address, status, last_seen)
            VALUES (?, ?, ?, ?, datetime('now'))
            """,
            (hostname, distro, ip, status),
        )
    conn.commit()
    conn.close()


def record_inventory(hostname: str, distro: str, ip_address: str = "unknown", status: str = "online") -> None:
    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO inventory (hostname, distro, ip_address, status, last_seen)
        VALUES (?, ?, ?, ?, datetime('now'))
        ON CONFLICT(hostname) DO UPDATE SET
            distro = excluded.distro,
            ip_address = excluded.ip_address,
            status = excluded.status,
            last_seen = datetime('now')
        """,
        (hostname, distro, ip_address, status),
    )
    conn.commit()
    conn.close()


def add_job(distro: str, target_host: str, status: str = "queued", details: str = "") -> int:
    conn = get_db_connection()
    cursor = conn.execute(
        """
        INSERT INTO deploy_jobs (distro, target_host, status, details, started_at, created_at)
        VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
        """,
        (distro, target_host, status, details),
    )
    job_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return job_id


def update_job(job_id: int, status: str, details: str = "", exit_code: Optional[int] = None) -> None:
    conn = get_db_connection()
    if status in TERMINAL_STATUSES:
        conn.execute(
            """
            UPDATE deploy_jobs
            SET status = ?, details = ?, exit_code = ?, ended_at = datetime('now')
            WHERE id = ?
            """,
            (status, details, exit_code, job_id),
        )
    else:
        conn.execute(
            """
            UPDATE deploy_jobs
            SET status = ?, details = ?, exit_code = ?, ended_at = NULL
            WHERE id = ?
            """,
            (status, details, exit_code, job_id),
        )
    conn.commit()
    conn.close()


def get_jobs(limit: int = 50) -> List[sqlite3.Row]:
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT * FROM deploy_jobs
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return rows


def get_inventory() -> List[sqlite3.Row]:
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM inventory ORDER BY hostname ASC").fetchall()
    conn.close()
    return rows


def get_job(job_id: int) -> Optional[sqlite3.Row]:
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM deploy_jobs WHERE id = ?", (job_id,)).fetchone()
    conn.close()
    return row


def get_dashboard_summary() -> Dict[str, int]:
    conn = get_db_connection()
    counts = {
        "queued": 0,
        "running": 0,
        "success": 0,
        "failed": 0,
        "total": 0,
    }
    rows = conn.execute("SELECT status, COUNT(*) AS c FROM deploy_jobs GROUP BY status").fetchall()
    for row in rows:
        counts[row["status"]] = row["c"]
        counts["total"] += row["c"]
    conn.close()
    return counts


def execute_deployment(job_id: int) -> None:
    job = get_job(job_id)
    if not job:
        return

    distro = job["distro"]
    target_host = job["target_host"]
    script_path = os.path.join(SCRIPTS_DIR, f"{distro}.sh")

    if not os.path.exists(script_path):
        update_job(job_id, "failed", f"Deployment script missing for {distro}: {script_path}", 1)
        return

    update_job(job_id, "running", f"Deployment started for {target_host}")
    record_inventory(target_host, distro, status="deploying")

    try:
        process = subprocess.run(
            ["bash", script_path, target_host],
            capture_output=True,
            text=True,
            timeout=1800,
        )
        output = (process.stdout or "") + ("\n" + process.stderr if process.stderr else "")
        status = "success" if process.returncode == 0 else "failed"
        update_job(job_id, status, output.strip()[:4000], process.returncode)
        record_inventory(target_host, distro, status="online" if process.returncode == 0 else "failed")
    except subprocess.TimeoutExpired:
        update_job(job_id, "failed", "Deployment timed out after 30 minutes", 124)
        record_inventory(target_host, distro, status="failed")
    except Exception as exc:
        update_job(job_id, "failed", f"Deployment exception: {str(exc)}", 1)
        record_inventory(target_host, distro, status="failed")


@app.route("/")
def dashboard():
    summary = get_dashboard_summary()
    jobs = get_jobs(10)
    return render_template("dashboard.html", summary=summary, jobs=jobs)


@app.route("/deployments")
def deployments():
    jobs = get_jobs(50)
    return render_template("deployments.html", jobs=jobs)


@app.route("/inventory")
def inventory():
    items = get_inventory()
    return render_template("inventory.html", inventory=items)


@app.route("/reports")
def reports():
    jobs = get_jobs(50)
    return render_template("deployments.html", jobs=jobs)


@app.route("/health")
def health():
    return jsonify({"status": "ok", "database": DB_PATH})


@app.route("/api/deploy", methods=["POST"])
def api_deploy():
    payload = request.get_json(silent=True) or {}
    distro = payload.get("distro", "").strip().lower()
    target_host = payload.get("target_host") or payload.get("target") or "localhost"

    if distro not in SUPPORTED_DISTROS:
        return jsonify({"error": f"Unsupported distro. Choose one of: {SUPPORTED_DISTROS}"}), 400

    job_id = add_job(distro, target_host, "queued", f"Queued deployment for {target_host}")
    t = threading.Thread(target=execute_deployment, args=(job_id,), daemon=True)
    t.start()
    return jsonify({"job_id": job_id, "status": "queued", "distro": distro, "target_host": target_host})


@app.route("/api/jobs")
def api_jobs():
    jobs = get_jobs(50)
    return jsonify({"jobs": [dict(job) for job in jobs]})


@app.route("/api/inventory")
def api_inventory():
    inventory = get_inventory()
    return jsonify({"inventory": [dict(item) for item in inventory]})


@app.route("/api/health")
def api_health():
    return jsonify({"status": "ok"})


init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
