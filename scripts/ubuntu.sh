#!/usr/bin/env python3
import sys
import time

import requests

API_URL = "http://127.0.0.1:5000/api/deploy"
DISTROS = ["ubuntu", "debian", "rocky", "fedora"]


def main():
    print("Linux Deployment Server")
    print("=" * 28)
    print("Select a distro to deploy:")

    for index, distro in enumerate(DISTROS, start=1):
        print(f"  {index}. {distro}")

    try:
        choice = input("Enter choice [1-4]: ").strip()
    except KeyboardInterrupt:
        print("\nCancelled")
        sys.exit(0)

    if choice not in {str(i) for i in range(1, len(DISTROS) + 1)}:
        print("Invalid selection")
        sys.exit(1)

    distro = DISTROS[int(choice) - 1]
    target_host = input("Enter target hostname or identifier [localhost]: ").strip() or "localhost"

    try:
        response = requests.post(
            API_URL,
            json={"distro": distro, "target_host": target_host},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        print(f"Deployment queued successfully for {distro} on {target_host}")
        print(f"Job ID: {payload.get('job_id')}")
        print("You can monitor it in the web dashboard at http://localhost:5000/")
    except Exception as exc:
        print(f"Deployment request failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
