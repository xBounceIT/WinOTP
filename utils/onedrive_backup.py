import os
import json
import tempfile
import webbrowser
from datetime import datetime
import requests
import msal
from utils.file_io import read_json

# OneDrive API settings
# Using 'common' endpoint to support both personal and business accounts
AUTHORITY = "https://login.microsoftonline.com/common"

# NOTE TO DEVELOPERS: 
# You need to register your application with Microsoft to get a client ID:
# 1. Go to https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade
# 2. Click 'New registration'
# 3. Enter a name for your application (e.g., 'WinOTP')
# 4. Select 'Accounts in any organizational directory (Any Azure AD directory - Multitenant) and personal Microsoft accounts (e.g. Skype, Xbox)'
# 5. Set the redirect URI to 'http://localhost:8000' as a 'Web' platform
# 6. Click 'Register'
# 7. Copy the 'Application (client) ID' and paste it below
# 8. For business accounts, you may need to get admin consent for your organization

CLIENT_ID = "fec71448-5af2-4b56-aa74-114bfb6cd647"  # Replace with your actual client ID
# Using the exact scopes configured in the Azure app
SCOPES = ["Files.ReadWrite"]
REDIRECT_URI = "http://localhost:8000"
TOKEN_PATH = os.path.join(os.path.expandvars('%APPDATA%'), 'WinOTP', 'token_onedrive.json')


def get_auth_token():
    """
    Get the authentication token for OneDrive, either from cache or by authenticating the user.
    """
    # Check if we have a cached token
    if os.path.exists(TOKEN_PATH):
        try:
            # Create MSAL app
            app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY)
            
            # Load the token cache - handle different MSAL versions
            try:
                with open(TOKEN_PATH, 'r') as f:
                    cache_data = f.read()
                try:
                    json_data = json.loads(cache_data)
                    if 'access_token' in json_data:
                        print("Found direct token in cache")
                        return json_data
                except json.JSONDecodeError:
                    pass
                # Try both MSAL cache deserialization methods for compatibility
                try:
                    app.token_cache.deserialize(cache_data)
                    print("Token cache loaded using deserialize() method")
                except AttributeError:
                    try:
                        app.token_cache._deserialize(cache_data)
                        print("Token cache loaded using _deserialize() method (legacy)")
                    except Exception as e2:
                        print(f"Both deserialize methods failed: {e2}")
                        return authenticate_user()
            except Exception as e:
                print(f"Error loading token cache: {e}")
                return authenticate_user()
            
            # Get accounts
            accounts = app.get_accounts()
            if not accounts:
                print("No accounts found in token cache. Forcing re-authentication.")
                return authenticate_user()
            # If account exists, try to get token silently
            try:
                result = app.acquire_token_silent(SCOPES, account=accounts[0])
                if result and 'access_token' in result:
                    print("Token retrieved from cache")
                    return result
                else:
                    print("Token not found in cache or silent acquisition failed. Forcing re-authentication.")
                    return authenticate_user()
            except Exception as e:
                print(f"Exception during acquire_token_silent: {e}. Forcing re-authentication.")
                return authenticate_user()
        except Exception as e:
            print(f"Error loading token from cache: {e}")
            return authenticate_user()

    # If we don't have a valid token, authenticate the user
    print("No valid token found. Forcing re-authentication.")
    return authenticate_user()



def authenticate_user():
    """
    Authenticate the user with Microsoft identity platform using device code flow.
    Uses the modal dialog in the UI to display the authentication code.
    """
    # Import webview here to avoid circular imports
    import webview
    import threading
    
    # Create MSAL app
    app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY)
    
    # Use device code flow instead of authorization code flow
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        raise Exception(f"Failed to create device flow: {flow.get('error_description', 'Unknown error')}")
    
    # Get the user code and verification URI
    user_code = flow["user_code"]
    verification_uri = flow["verification_uri"]
    
    print(f"Authentication code: {user_code}")
    print(f"Verification URI: {verification_uri}")
    
    # Show the authentication code in the UI modal
    webview.windows[0].evaluate_js(f'''
        document.getElementById('oneDriveAuthCode').innerText = '{user_code}';
        document.getElementById('oneDriveAuthOpenBtn').onclick = function() {{
            window.open('{verification_uri}', '_blank');
        }};
        document.getElementById('oneDriveAuthModal').style.display = 'flex';
    ''')
    
    # Open the verification URI in the default browser
    webbrowser.open(verification_uri)
    
    # Poll for token in a background thread
    result_container = {}
    auth_completed = threading.Event()
    
    def token_acquisition_thread():
        try:
            # Poll for token
            result = app.acquire_token_by_device_flow(flow)
            result_container['result'] = result
            
            # Signal that authentication is complete
            auth_completed.set()
            
            # Hide the modal dialog
            webview.windows[0].evaluate_js('''
                document.getElementById('oneDriveAuthModal').style.display = 'none';
            ''')
        except Exception as e:
            result_container['error'] = str(e)
            auth_completed.set()
    
    # Start the token acquisition thread
    thread = threading.Thread(target=token_acquisition_thread)
    thread.daemon = True
    thread.start()
    
    # Wait for authentication to complete
    auth_completed.wait()
    
    # Check for errors
    if 'error' in result_container:
        # Hide the modal dialog in case of error
        webview.windows[0].evaluate_js('''
            document.getElementById('oneDriveAuthModal').style.display = 'none';
        ''')
        raise Exception(f"Error in authentication: {result_container['error']}")
    
    result = result_container.get('result', {})
    if "error" in result:
        # Hide the modal dialog in case of error
        webview.windows[0].evaluate_js('''
            document.getElementById('oneDriveAuthModal').style.display = 'none';
        ''')
        raise Exception(f"Error getting token: {result.get('error_description', result.get('error'))}")
    
    # Cache the token - handle different MSAL versions
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
    try:
        # First attempt: Try the public serialize() method (newer MSAL versions)
        try:
            cache_data = app.token_cache.serialize()
            if isinstance(cache_data, bytes):
                cache_data = cache_data.decode('utf-8')
            with open(TOKEN_PATH, 'w') as f:
                f.write(cache_data)
            print("Token cache saved successfully using serialize() method")
        except (AttributeError, TypeError) as e1:
            print(f"Could not use serialize() method: {e1}")
            
            # Second attempt: Try to directly access the cache data
            # This is a fallback that doesn't rely on specific methods
            try:
                # Try to get the internal cache data
                if hasattr(app.token_cache, '_cache'):
                    cache_data = app.token_cache._cache
                    with open(TOKEN_PATH, 'w') as f:
                        json.dump(cache_data, f)
                    print("Token cache saved successfully using direct cache access")
                else:
                    # Last resort: Just save the token itself
                    with open(TOKEN_PATH, 'w') as f:
                        json.dump(result, f)
                    print("Saved only the token result as fallback")
            except Exception as e2:
                print(f"Warning: Could not save token cache: {e2}")
    except Exception as e:
        print(f"Error saving token cache: {e}")
    
    # Save the token cache after authentication
    try:
        cache_data = None
        # Try public serialize() first
        if hasattr(app.token_cache, 'serialize'):
            cache_data = app.token_cache.serialize()
            print("Token cache serialized using serialize()")
        elif hasattr(app.token_cache, '_serialize'):
            cache_data = app.token_cache._serialize()
            print("Token cache serialized using _serialize() (legacy)")
        if cache_data:
            with open(TOKEN_PATH, 'w') as f:
                f.write(cache_data if isinstance(cache_data, str) else cache_data.decode('utf-8'))
            print(f"Token cache saved successfully to {TOKEN_PATH}")
        else:
            # Last resort: Save the token result as JSON
            with open(TOKEN_PATH, 'w') as f:
                json.dump(result, f)
            print("Saved only the token result as fallback (no cache serialization available)")
    except Exception as e:
        print(f"Warning: Could not save token cache after authentication: {e}")
    print("Authentication successful")
    return result


def get_backup_filename():
    """
    Returns the backup filename for today's date.
    """
    current_date = datetime.now().strftime("%Y-%m-%d")
    return f"tokens_backup_{current_date}.json"


def check_backup_exists(folder_name="WinOTP Backups"):
    """
    Checks if today's backup file exists on OneDrive.
    Returns True if the file exists, False otherwise.
    """
    try:
        # Get authentication token
        token_result = get_auth_token()
        if not token_result or "access_token" not in token_result:
            print("Failed to get authentication token")
            return False
        
        access_token = token_result["access_token"]
        
        # Get backup filename
        backup_filename = get_backup_filename()
        
        # First, check if the folder exists
        folder_id = get_or_create_folder(access_token, folder_name)
        if not folder_id:
            return False
        
        # Check if the file exists in the folder
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Search for the file in the folder
        search_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{folder_id}/children?$filter=name eq '{backup_filename}'"
        response = requests.get(search_url, headers=headers)
        
        if response.status_code != 200:
            print(f"Error searching for file: {response.text}")
            return False
        
        # Check if any files were found
        result = response.json()
        return len(result.get("value", [])) > 0
    
    except Exception as e:
        print(f"Error checking if backup exists: {e}")
        return False


def get_or_create_folder(access_token, folder_name):
    """
    Get or create a folder in OneDrive root.
    Returns the folder ID if successful, None otherwise.
    """
    print(f"Looking for or creating folder: '{folder_name}'")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # List all children in root and filter for folder by name in Python
    search_url = "https://graph.microsoft.com/v1.0/me/drive/root/children"
    print(f"Listing children with URL: {search_url}")
    print(f"Using headers: {headers}")
    try:
        response = requests.get(search_url, headers=headers)
        print(f"Folder list response status code: {response.status_code}")
        print(f"Folder list response: {response.text}")
        if response.status_code == 200:
            items = response.json().get("value", [])
            for item in items:
                if item["name"] == folder_name and "folder" in item:
                    print(f"Found existing folder '{folder_name}' with ID: {item['id']}")
                    return item["id"]
        else:
            print(f"Error listing children: {response.text}")
    except Exception as e:
        print(f"Exception during folder search: {str(e)}")
        return None
    
    # Folder not found, create it
    print(f"Folder '{folder_name}' not found, creating it...")
    create_url = "https://graph.microsoft.com/v1.0/me/drive/root/children"
    create_data = {
        "name": folder_name,
        "folder": {},
        "@microsoft.graph.conflictBehavior": "rename"
    }
    print(f"Creating folder with URL: {create_url}")
    print(f"Create folder data: {create_data}")
    try:
        print(f"Sending POST request to create folder: {create_url}")
        response = requests.post(create_url, headers=headers, json=create_data)
        print(f"Folder creation response status code: {response.status_code}")
        print(f"Folder creation response: {response.text}")
        return None
    except Exception as e:
        print(f"Exception during folder creation: {str(e)}")
        return None


def upload_tokens_json_to_onedrive(local_file_path='tokens.json', folder_name='WinOTP Backups'):
    """
    Uploads tokens.json to OneDrive in a specific folder. Creates/updates the file as needed.
    The backup file will be decrypted and include the current date in the filename.
    """
    try:
        print(f"===== ONEDRIVE BACKUP PROCESS STARTED =====")
        print(f"Starting OneDrive backup process for {local_file_path}")
        print(f"Backup folder name: {folder_name}")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Local file exists: {os.path.exists(local_file_path)}")
        print(f"Local file absolute path: {os.path.abspath(local_file_path)}")
        # Print MSAL version for debugging
        print(f"MSAL version: {msal.__version__ if hasattr(msal, '__version__') else 'Unknown'}")
        print(f"Token path: {TOKEN_PATH}")
        print(f"Token file exists: {os.path.exists(TOKEN_PATH)}")
        os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
        tokens_data = read_json(local_file_path)
        is_encrypted = tokens_data.get("encrypted", False) if isinstance(tokens_data, dict) else False
        print(f"File is encrypted: {is_encrypted}")
        decrypted_tokens = {}
        if is_encrypted:
            print("File is encrypted, creating unencrypted backup...")
            try:
                import sys
                parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                if parent_dir not in sys.path:
                    sys.path.append(parent_dir)
                from main import Api
                temp_api = Api()
                if not temp_api._tokens_loaded:
                    temp_api.load_tokens()
                if hasattr(temp_api, 'tokens') and temp_api.tokens:
                    for token_id, token_data in temp_api.tokens.items():
                        decrypted_tokens[token_id] = {
                            "issuer": token_data.get("issuer", "Unknown"),
                            "name": token_data.get("name", "Unknown"),
                            "secret": token_data.get("secret", ""),
                            "created": token_data.get("created", "")
                        }
                    print(f"Successfully extracted {len(decrypted_tokens)} tokens from memory")
                else:
                    print("No tokens found in memory")
                    decrypted_tokens = {}
            except Exception as e:
                print(f"Error accessing tokens from memory: {e}")
                decrypted_tokens = {}
        else:
            print("File is not encrypted, using as is")
            decrypted_tokens = tokens_data
        # Create a temporary file with the tokens
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
            json.dump(decrypted_tokens, temp_file, indent=4)
            temp_file_path = temp_file.name
        backup_filename = get_backup_filename()
        print(f"Backup filename: {backup_filename}")
        print("Getting authentication token...")
        token_result = get_auth_token()
        if not token_result or "access_token" not in token_result:
            print("Failed to get authentication token")
            return False
        print("Authentication token obtained successfully")
        access_token = token_result["access_token"]
        print(f"Getting or creating backup folder '{folder_name}'...")
        folder_id = get_or_create_folder(access_token, folder_name)
        if not folder_id:
            print(f"Failed to get or create folder '{folder_name}'")
            return False
        headers = {"Authorization": f"Bearer {access_token}"}
        # Check if file exists
        search_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{folder_id}/children?$filter=name eq '{backup_filename}'"
        try:
            response = requests.get(search_url, headers=headers)
            if response.status_code != 200:
                print(f"Error searching for file: {response.text}")
                return False
            result = response.json()
            files = result.get("value", [])
        except Exception as e:
            print(f"Exception during file search: {e}")
            return False
        with open(temp_file_path, 'rb') as f:
            file_content = f.read()
        if files:
            file_id = files[0]["id"]
            print(f"Updating existing file with ID: {file_id}")
            update_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}/content"
            try:
                response = requests.put(update_url, headers=headers, data=file_content)
                if response.status_code not in [200, 201]:
                    print(f"Error updating file: {response.text}")
                    return False
                print(f"File updated successfully with status code: {response.status_code}")
                print(f"File URL: {response.json().get('webUrl', 'Unknown')}")
            except Exception as e:
                print(f"Exception during file update: {e}")
                return False
        else:
            print(f"Creating new file '{backup_filename}'")
            upload_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{folder_id}:/{backup_filename}:/content"
            try:
                response = requests.put(upload_url, headers=headers, data=file_content)
                if response.status_code not in [200, 201]:
                    print(f"Error creating file: {response.text}")
                    return False
                print(f"File created successfully with status code: {response.status_code}")
                print(f"File URL: {response.json().get('webUrl', 'Unknown')}")
            except Exception as e:
                print(f"Exception during file creation: {e}")
                return False
        try:
            os.unlink(temp_file_path)
        except Exception as e:
            print(f"Warning: Could not delete temporary file {temp_file_path}: {e}")
        print(f"OneDrive backup complete: {backup_filename}")
        return True
    except Exception as e:
        print(f"Error during OneDrive backup: {e}")
        # (Removed invalid code fragment)

        # Check if the file already exists
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        print(f"Checking if file '{backup_filename}' already exists...")
        search_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{folder_id}/children?$filter=name eq '{backup_filename}'"
        print(f"File search URL: {search_url}")
        print(f"File search headers: {headers}")
        
        try:
            response = requests.get(search_url, headers=headers)
            print(f"File search response status code: {response.status_code}")
            print(f"File search response: {response.text}")
            
            if response.status_code != 200:
                raise Exception(f"Error searching for file: {response.text}")
            
            result = response.json()
            files = result.get("value", [])
            
            print(f"Found {len(files)} existing files with name '{backup_filename}'")
        except Exception as e:
            print(f"Exception during file search: {str(e)}")
            raise Exception(f"Error during file search: {str(e)}")
        
        # Upload the file
        print(f"Reading temporary file from {temp_file_path}")
        with open(temp_file_path, 'rb') as f:
            file_content = f.read()
        
        print(f"File content size: {len(file_content)} bytes")
        
        if files:
            # File exists, update it
            file_id = files[0]["id"]
            print(f"Updating existing file with ID: {file_id}")
            update_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}/content"
            print(f"File update URL: {update_url}")
            
            try:
                update_headers = {"Authorization": f"Bearer {access_token}"}
                print(f"File update headers: {update_headers}")
                print(f"File content size: {len(file_content)} bytes")
                
                response = requests.put(update_url, headers=update_headers, data=file_content)
                print(f"File update response status code: {response.status_code}")
                print(f"File update response: {response.text}")
                
                if response.status_code not in [200, 201]:
                    raise Exception(f"Error updating file: {response.text}")
                
                print(f"File updated successfully with status code: {response.status_code}")
                print(f"Response: {response.json()}")
                print(f"File URL: {response.json().get('webUrl', 'Unknown')}")
            except Exception as e:
                print(f"Exception during file update: {str(e)}")
                raise Exception(f"Error during file update: {str(e)}")
        else:
            # File doesn't exist, create it
            print(f"Creating new file '{backup_filename}'")
            upload_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{folder_id}:/"
            upload_url += f"{backup_filename}:/content"
            print(f"File upload URL: {upload_url}")
            
            try:
                upload_headers = {"Authorization": f"Bearer {access_token}"}
                print(f"File upload headers: {upload_headers}")
                print(f"File content size: {len(file_content)} bytes")
                
                response = requests.put(upload_url, headers=upload_headers, data=file_content)
                print(f"File creation response status code: {response.status_code}")
                print(f"File creation response: {response.text}")
                
                if response.status_code not in [200, 201]:
                    raise Exception(f"Error creating file: {response.text}")
                
                print(f"File created successfully with status code: {response.status_code}")
                print(f"Response: {response.json()}")
                print(f"File URL: {response.json().get('webUrl', 'Unknown')}")
            except Exception as e:
                print(f"Exception during file creation: {str(e)}")
                raise Exception(f"Error during file creation: {str(e)}")
        
        # Clean up the temporary file
        try:
            os.unlink(temp_file_path)
        except Exception as e:
            print(f"Warning: Could not delete temporary file {temp_file_path}: {e}")
        
        print(f"OneDrive backup complete: {backup_filename}")
        return True
    
    except Exception as e:
        print(f"Error during OneDrive backup: {e}")
        return False
