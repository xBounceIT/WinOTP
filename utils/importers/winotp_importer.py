import json
from datetime import datetime
import base64 # Needed for base32 validation check via Token model
from models.token import Token  # Import Token for validation

def parse_winotp_json(json_str):
    """
    Parses a JSON string expected to contain WinOTP token data.

    Args:
        json_str: The JSON string to parse.

    Returns:
        A dictionary with status, message, and a list of valid_tokens (dicts).
    """
    try:
        import_data = json.loads(json_str)

        if not isinstance(import_data, dict):
            return {"status": "error", "message": "Invalid import format: Expected a JSON object", "valid_tokens": []}

        valid_tokens = []
        processed_ids = set() # To keep track if needed, though we generate new IDs later

        for token_id, token_data in import_data.items():
            try:
                if not isinstance(token_data, dict) or not token_data.get("secret"):
                    print(f"Skipping token '{token_id}' due to missing data or secret.")
                    continue # Skip invalid entries silently based on original logic

                secret = token_data.get("secret")
                if not Token.validate_base32_secret(secret):
                    print(f"Skipping token '{token_id}' due to invalid base32 secret.")
                    continue # Skip invalid secrets silently

                valid_tokens.append({
                    "issuer": token_data.get("issuer", "Unknown"),
                    "name": token_data.get("name", "Unknown"),
                    "secret": secret
                    # "created" timestamp will be added when adding to the main dict
                })
                processed_ids.add(token_id)

            except Exception as e:
                print(f"Error processing individual token '{token_id}' during WinOTP import: {e}")
                continue # Skip on error processing single item

        if not valid_tokens:
             return {"status": "warning", "message": "No valid tokens found in the import file", "valid_tokens": []}

        return {"status": "success", "message": f"Parsed {len(valid_tokens)} potential tokens.", "valid_tokens": valid_tokens}

    except json.JSONDecodeError:
        return {"status": "error", "message": "Invalid JSON format", "valid_tokens": []}
    except Exception as e:
        return {"status": "error", "message": f"Failed to parse WinOTP JSON: {str(e)}", "valid_tokens": []} 