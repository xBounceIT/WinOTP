import os
import urllib.request
import threading
import time
import requests

def check_for_updates():
    """Check for the latest release on GitHub."""
    repo_url = "https://api.github.com/repos/xBounceIT/WinOTP/releases/latest"
    try:
        response = requests.get(repo_url, timeout=10)
        response.raise_for_status()
        latest_release = response.json()

        # Extract the latest version tag
        latest_version = latest_release.get("tag_name", "Unknown")
        release_notes = latest_release.get("body", "No release notes available.")

        print(f"Latest version: {latest_version}")
        print(f"Release notes:\n{release_notes}")

        # Compare with the current version
        current_version = "0.1"  # Replace with dynamic version retrieval if available
        if latest_version != current_version:
            print("A new version is available! Please update.")
        else:
            print("You are using the latest version.")
    except requests.RequestException as e:
        print(f"Error checking for updates: {e}")