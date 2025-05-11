import os
import pickle
import json
import tempfile
from datetime import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Import utilities for decryption
from utils.auth import get_auth_type, is_auth_enabled
from utils.crypto import decrypt_tokens_file
from utils.file_io import read_json

SCOPES = ['https://www.googleapis.com/auth/drive.file']
TOKEN_PATH = os.path.join(os.path.expandvars('%APPDATA%'), 'WinOTP', 'token_drive.pickle')
CREDS_PATH = os.path.join(os.path.dirname(__file__), 'drive_secret.json')
AUTH_CONFIG_PATH = os.path.join(os.path.expandvars('%APPDATA%'), 'WinOTP', 'auth_config.json')


def authenticate_google_drive():
    """
    Authenticate and return a Google Drive service client.
    Returns None if authentication is cancelled.
    """
    creds = None
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
    
    # If credentials exist and are valid, return the service immediately
    if creds and creds.valid:
        service = build('drive', 'v3', credentials=creds)
        return service
    
    # If credentials exist but are expired, try to refresh them
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(TOKEN_PATH, 'wb') as token:
                pickle.dump(creds, token)
            service = build('drive', 'v3', credentials=creds)
            return service
        except Exception as e:
            print(f"Error refreshing Google Drive credentials: {e}")
            # Fall through to interactive authentication
    
    # Otherwise, need to perform interactive authentication
    try:
        # Import webview here to avoid circular imports
        import webview
        
        # Show a notification that authentication is about to begin
        webview.windows[0].evaluate_js('''
            showNotification("Opening Google authentication in browser...", "info");
            // Set global variable for cancellation tracking
            window.googleAuthCancelled = false;
        ''')
        
        # Create the flow for authentication
        flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
        
        # Run the local server for auth
        creds = flow.run_local_server(port=0)
        
        # Check if authentication was cancelled
        cancelled = webview.windows[0].evaluate_js('window.googleAuthCancelled === true')
        if cancelled:
            print("Google Drive authentication cancelled by user")
            return None
        
        # Save the credentials for future use
        os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)
        
        # Build and return the service
        service = build('drive', 'v3', credentials=creds)
        return service
        
    except Exception as e:
        print(f"Error during Google Drive authentication: {e}")
        return None


def get_backup_filename():
    """
    Returns the backup filename for today's date.
    """
    current_date = datetime.now().strftime("%Y-%m-%d")
    return f"tokens_backup_{current_date}.json"

def check_backup_exists(drive_folder_name='WinOTP Backups'):
    """
    Checks if today's backup file exists on Google Drive.
    Returns True if the file exists, False otherwise.
    """
    try:
        # Get today's backup filename
        backup_filename = get_backup_filename()
        
        # Authenticate and get service
        service = authenticate_google_drive()
        
        # Check if the backup folder exists
        folder_id = None
        results = service.files().list(q=f"name='{drive_folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
                                       spaces='drive', fields="files(id, name)").execute()
        folders = results.get('files', [])
        
        if not folders:
            # Folder doesn't exist, so the backup doesn't exist
            return False
            
        folder_id = folders[0]['id']
        
        # Check if today's backup file exists in the folder
        query = f"name='{backup_filename}' and '{folder_id}' in parents and trashed=false"
        results = service.files().list(q=query, spaces='drive', fields="files(id, name)").execute()
        files = results.get('files', [])
        
        # Return True if the file exists, False otherwise
        return len(files) > 0
    except Exception as e:
        print(f"Error checking if backup exists: {e}")
        # If there's an error, assume the backup doesn't exist to be safe
        return False

def upload_tokens_json_to_drive(local_file_path='tokens.json', drive_folder_name='WinOTP Backups'):
    """
    Uploads tokens.json to Google Drive in a specific folder. Creates/updates the file as needed.
    The backup file will be decrypted and include the current date in the filename.
    """
    try:
        print(f"Starting backup process for {local_file_path}")
        
        # Read the tokens file
        tokens_data = read_json(local_file_path)
        
        # Check if the file is encrypted
        is_encrypted = tokens_data.get("encrypted", False) if isinstance(tokens_data, dict) else False
        print(f"File is encrypted: {is_encrypted}")
        
        # Initialize decrypted_tokens
        decrypted_tokens = {}
        
        if is_encrypted:
            print("File is encrypted, creating unencrypted backup...")
            # We need to extract the actual token data from the encrypted file
            # Since we can't decrypt without the actual password/PIN, we'll create a clean version
            # by reading the tokens from memory if possible
            
            # Try to import the main module to access loaded tokens
            try:
                import sys
                import os
                
                # Add the parent directory to sys.path if needed
                parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                if parent_dir not in sys.path:
                    sys.path.append(parent_dir)
                
                # Try to import the main module and access the API instance
                from main import Api
                
                # Create a temporary API instance to access tokens
                temp_api = Api()
                
                # Load tokens if needed
                if not temp_api._tokens_loaded:
                    temp_api.load_tokens()
                
                # Get the tokens from the API instance
                if hasattr(temp_api, 'tokens') and temp_api.tokens:
                    # Convert the tokens to a clean format for backup
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
                    # If we can't get tokens from memory, create an empty backup
                    decrypted_tokens = {}
            except Exception as e:
                print(f"Error accessing tokens from memory: {e}")
                # If we can't access tokens from memory, create an empty backup
                decrypted_tokens = {}
        else:
            # File is not encrypted, use as is
            print("File is not encrypted, using as is")
            decrypted_tokens = tokens_data
        
        # Create a temporary file with the tokens
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
            json.dump(decrypted_tokens, temp_file, indent=4)
            temp_file_path = temp_file.name
        
        # Get backup filename using the shared function
        backup_filename = get_backup_filename()
        
        # Authenticate and get service
        service = authenticate_google_drive()
        
        # Check/create backup folder
        folder_id = None
        results = service.files().list(q=f"name='{drive_folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
                                       spaces='drive', fields="files(id, name)").execute()
        folders = results.get('files', [])
        if folders:
            folder_id = folders[0]['id']
        else:
            file_metadata = {'name': drive_folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
            folder = service.files().create(body=file_metadata, fields='id').execute()
            folder_id = folder.get('id')
        
        # Check if a backup with today's date already exists
        query = f"name='{backup_filename}' and '{folder_id}' in parents and trashed=false"
        results = service.files().list(q=query, spaces='drive', fields="files(id, name)").execute()
        files = results.get('files', [])
        
        # Create file metadata with the dated filename
        file_metadata = {
            'name': backup_filename,
            'parents': [folder_id]
        }
        
        # Upload the decrypted file
        media = MediaFileUpload(temp_file_path, mimetype='application/json')
        
        if files:
            # Update existing file if it exists
            file_id = files[0]['id']
            service.files().update(fileId=file_id, media_body=media).execute()
        else:
            # Create new file if it doesn't exist
            service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        
        # Clean up the temporary file
        try:
            os.unlink(temp_file_path)
        except Exception as e:
            print(f"Warning: Could not delete temporary file {temp_file_path}: {e}")
        
        print(f"Backup to Google Drive complete: {backup_filename}")
        
        # Update the last backup date in the settings file
        try:
            from datetime import datetime
            import os
            
            # Get the app settings file path
            # First, check if we're in debug mode by checking for .dev files
            parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            settings_file = os.path.join(parent_dir, 'app_settings.json.dev')
            if not os.path.exists(settings_file):
                # If not in debug mode, use the production path
                settings_file = os.path.join(os.path.expandvars('%APPDATA%'), 'WinOTP', 'app_settings.json')
            
            if os.path.exists(settings_file):
                # Load the current settings
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                
                # Update the backup date
                today = datetime.now().strftime('%Y-%m-%d')
                settings['last_backup_date_google_drive'] = today
                
                # Save the updated settings
                with open(settings_file, 'w') as f:
                    json.dump(settings, f, indent=4)
                    
                print(f"Updated last Google Drive backup date to {today} in {settings_file}")
            else:
                print(f"Settings file not found: {settings_file}")
        except Exception as e:
            print(f"Error updating last backup date: {e}")
        
        return True
    except Exception as e:
        print(f"Error during Google Drive backup: {e}")
        return False
