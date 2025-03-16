import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from .file_io import read_json, write_json

def generate_key_from_password(password: str, salt: bytes = None) -> tuple[bytes, bytes]:
    """
    Generate a Fernet key from a password using PBKDF2
    
    Args:
        password (str): The password to derive the key from
        salt (bytes, optional): Salt for key derivation. If None, generates new salt.
        
    Returns:
        tuple[bytes, bytes]: (key, salt) tuple
    """
    if salt is None:
        salt = os.urandom(16)
        
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,  # High number of iterations for better security
    )
    
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key, salt

def encrypt_data(data: dict, password: str, salt: bytes = None) -> tuple[bytes, bytes]:
    """
    Encrypt dictionary data using a password
    
    Args:
        data (dict): The data to encrypt
        password (str): The password to encrypt with
        salt (bytes, optional): Salt for key derivation. If None, generates new salt.
        
    Returns:
        tuple[bytes, bytes]: (encrypted_data, salt) tuple
    """
    # Generate key from password
    key, salt = generate_key_from_password(password, salt)
    
    # Create Fernet cipher
    f = Fernet(key)
    
    # Convert data to JSON string and encode
    json_data = str(data).encode()
    
    # Encrypt the data
    encrypted_data = f.encrypt(json_data)
    
    return encrypted_data, salt

def decrypt_data(encrypted_data: bytes, password: str, salt: bytes) -> dict:
    """
    Decrypt data using a password
    
    Args:
        encrypted_data (bytes): The encrypted data
        password (str): The password to decrypt with
        salt (bytes): Salt used for key derivation
        
    Returns:
        dict: The decrypted data
    """
    # Generate key from password
    key, _ = generate_key_from_password(password, salt)
    
    # Create Fernet cipher
    f = Fernet(key)
    
    try:
        # Decrypt the data
        decrypted_data = f.decrypt(encrypted_data)
        
        # Convert from string representation back to dict
        # Using eval since we stored the dict as a string representation
        # This is safe since we control the data format
        return eval(decrypted_data.decode())
    except Exception as e:
        print(f"Error decrypting data: {e}")
        return None

def encrypt_tokens_file(tokens_path: str, password: str) -> bool:
    """
    Encrypt the tokens file using the provided password
    
    Args:
        tokens_path (str): Path to the tokens file
        password (str): Password to encrypt with
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Read the current tokens
        tokens = read_json(tokens_path)
        
        # Encrypt the tokens
        encrypted_data, salt = encrypt_data(tokens, password)
        
        # Create encrypted tokens file structure
        encrypted_tokens = {
            "encrypted": True,
            "data": base64.b64encode(encrypted_data).decode(),
            "salt": base64.b64encode(salt).decode()
        }
        
        # Write the encrypted data
        write_json(tokens_path, encrypted_tokens)
        return True
    except Exception as e:
        print(f"Error encrypting tokens file: {e}")
        return False

def decrypt_tokens_file(tokens_path: str, password: str) -> dict:
    """
    Decrypt the tokens file using the provided password
    
    Args:
        tokens_path (str): Path to the tokens file
        password (str): Password to decrypt with
        
    Returns:
        dict: Decrypted tokens or None if decryption fails
    """
    try:
        # Read the encrypted file
        encrypted_tokens = read_json(tokens_path)
        
        # Check if file is encrypted
        if not encrypted_tokens.get("encrypted", False):
            return encrypted_tokens
        
        # Get encrypted data and salt
        encrypted_data = base64.b64decode(encrypted_tokens["data"])
        salt = base64.b64decode(encrypted_tokens["salt"])
        
        # Decrypt the data
        return decrypt_data(encrypted_data, password, salt)
    except Exception as e:
        print(f"Error decrypting tokens file: {e}")
        return None 