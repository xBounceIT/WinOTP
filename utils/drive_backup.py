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
from utils.auth import get_auth_type
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

        print("Preparing data for Google Drive backup...")
        decrypted_tokens = {}
        if isinstance(tokens_data, dict) and tokens_data.get("encrypted", False):
            print("File is encrypted, attempting to decrypt backup payload...")
            try:
                auth_type = get_auth_type()
                auth_config = read_json(AUTH_CONFIG_PATH) or {}
                if auth_type == "pin":
                    decrypted_tokens = decrypt_tokens_file(local_file_path, auth_config.get("pin_hash", "")) or {}
                elif auth_type == "password":
                    decrypted_tokens = decrypt_tokens_file(local_file_path, auth_config.get("password_hash", "")) or {}
                else:
                    decrypted_tokens = {}
            except Exception as decrypt_error:
                print(f"Error decrypting tokens for backup: {decrypt_error}")
                decrypted_tokens = {}
        elif isinstance(tokens_data, dict):
            print("File is not encrypted, using as is")
            decrypted_tokens = tokens_data
        else:
            decrypted_tokens = {}
        
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
        return True
    except Exception as e:
        print(f"Error during Google Drive backup: {e}")
        return False
