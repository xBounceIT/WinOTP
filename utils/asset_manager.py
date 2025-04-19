import os
import urllib.request
import threading
import time
import requests
import traceback

CURRENT_VERSION = "v0.7.6"  # Define version at module level. Updated to include 'v' for consistency.

# Global variable to store update information
_update_info = {
    "available": False,
    "version": None,
    "notes": None,
    "download_url": None,
    "release_date": None
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
        release_date = latest_release.get("published_at", "Unknown date")
        
        # Get download URL for the portable exe
        download_url = None
        assets = latest_release.get("assets", [])
        for asset in assets:
            # Look for the portable EXE file in assets
            asset_name = asset.get("name", "").lower()
            if asset_name.endswith("-portable.exe") or asset_name.endswith("_portable.exe") or "winotp" in asset_name and asset_name.endswith(".exe"):
                download_url = asset.get("browser_download_url")
                print(f"Found executable asset: {asset_name}")
                break
        
        # If no portable exe found, use the generic release URL
        if not download_url:
            download_url = latest_release.get("html_url")
            print("No executable found in assets, using release page URL as fallback")

        print(f"Current version: {CURRENT_VERSION}")
        print(f"Latest version found: {latest_version}")
        print(f"Release date: {release_date}")
        print(f"Download URL: {download_url}")
        print(f"Release notes:\n{release_notes}")

        # Compare with the current version and store result
        if latest_version != CURRENT_VERSION and latest_version != "Unknown":
            print("A new version is available! Storing info.")
            _update_info = {
                "available": True,
                "version": latest_version,
                "notes": release_notes,
                "download_url": download_url,
                "release_date": release_date
            }
        else:
            print("You are using the latest version or latest couldn't be determined.")
            _update_info = {
                "available": False, 
                "version": None, 
                "notes": None,
                "download_url": None,
                "release_date": None
            }

    except requests.RequestException as e:
        print(f"Error checking for updates: {e}")
        traceback.print_exc()
        _update_info = {
            "available": False, 
            "version": None, 
            "notes": None,
            "download_url": None,
            "release_date": None
        } # Reset on error

def get_update_status():
    """Return the stored update status information."""
    return _update_info