import os
import urllib.request
import threading
import time
import requests
import traceback

CURRENT_VERSION = "v0.5.1"  # Define version at module level. Updated to include 'v' for consistency.

# Global variable to store update information
_update_info = {
    "available": False,
    "version": None,
    "notes": None
}

def check_for_updates():
    """Check for the latest release on GitHub and store the result."""
    global _update_info
    print("Attempting to check for updates...")
    # Use the /releases endpoint to get all releases, including pre-releases
    repo_url = "https://api.github.com/repos/xBounceIT/WinOTP/releases"
    try:
        response = requests.get(repo_url, timeout=10)
        response.raise_for_status()
        releases = response.json()

        if not releases:
            print("No releases found for this repository.")
            return

        # Get the latest release (first in the list)
        latest_release = releases[0]

        # Extract the latest version tag
        latest_version = latest_release.get("tag_name", "Unknown")
        release_notes = latest_release.get("body", "No release notes available.")

        print(f"Current version: {CURRENT_VERSION}")
        print(f"Latest version found: {latest_version}")
        print(f"Release notes:\n{release_notes}")

        # Compare with the current version and store result
        if latest_version != CURRENT_VERSION and latest_version != "Unknown":
            print("A new version is available! Storing info.")
            _update_info = {
                "available": True,
                "version": latest_version,
                "notes": release_notes
            }
        else:
            print("You are using the latest version or latest couldn't be determined.")
            _update_info = {"available": False, "version": None, "notes": None}

    except requests.RequestException as e:
        print(f"Error checking for updates: {e}")
        traceback.print_exc()
        _update_info = {"available": False, "version": None, "notes": None} # Reset on error

def get_update_status():
    """Return the stored update status information."""
    return _update_info