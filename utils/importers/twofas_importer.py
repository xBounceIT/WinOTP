import json
from datetime import datetime
import base64 # Needed for base32 validation check via Token model
from models.token import Token  # Import Token for validation

def parse_2fas_json(file_content, progress_callback=None):
    """
    Parses a JSON string expected to contain 2FAS backup data.

    Args:
        file_content: The JSON string content of the 2FAS backup.
        progress_callback: An optional function to call for progress updates.
                           It should accept (current_item, total_items).

    Returns:
        A dictionary with status, message, list of valid_tokens, skipped count,
        and failed_validation count.
    """
    try:
        import_data = json.loads(file_content)

        if not isinstance(import_data, dict) or "services" not in import_data or not isinstance(import_data["services"], list):
            return {"status": "error", "message": "Invalid 2FAS backup format: Expected JSON object with a 'services' list",
                    "valid_tokens": [], "skipped": 0, "failed_validation": 0}

        services = import_data["services"]
        total_services = len(services)
        valid_tokens = []
        skipped = 0
        failed_validation = 0

        for index, service_data in enumerate(services):
            try:
                # Basic structure check
                if not isinstance(service_data, dict) or "secret" not in service_data or "otp" not in service_data or not isinstance(service_data["otp"], dict):
                    skipped += 1
                    continue

                secret = service_data.get("secret")
                otp_details = service_data.get("otp", {})
                issuer = otp_details.get("issuer", "Unknown")
                account_name = otp_details.get("account", "") or service_data.get("name", "Unknown") # Original logic

                # Validate required fields
                if not secret:
                    failed_validation += 1
                    print(f"Skipping 2FAS token due to missing secret. Issuer: {issuer}, Name: {account_name}")
                    continue

                # Validate that the secret is a valid base32 string
                if not Token.validate_base32_secret(secret):
                    failed_validation += 1
                    print(f"Skipping 2FAS token due to invalid base32 secret. Issuer: {issuer}, Name: {account_name}")
                    continue

                # Add validated token data to list
                valid_tokens.append({
                    "issuer": issuer,
                    "name": account_name,
                    "secret": secret
                    # "created" timestamp will be added when adding to the main dict
                })

            except Exception as inner_e:
                failed_validation += 1 # Count as validation failure if parsing an entry fails
                print(f"Error processing a single 2FAS token entry: {str(inner_e)}")
                # Attempt to get some identifying info for the failed token
                try:
                    temp_issuer = service_data.get("otp", {}).get("issuer", "Unknown")
                    temp_name = service_data.get("otp", {}).get("account", "") or service_data.get("name", "Unknown")
                    print(f"    Failed 2FAS token details (if available): Issuer={temp_issuer}, Name={temp_name}")
                except Exception:
                    print("    Could not extract details for the failed 2FAS token entry.")

            # --- Progress Reporting ---
            if progress_callback and callable(progress_callback):
                # Report progress every 10 items or on the last item
                if (index + 1) % 10 == 0 or (index + 1) == total_services:
                    try:
                        progress_callback(index + 1, total_services)
                    except Exception as cb_e:
                         print(f"Error executing progress callback: {cb_e}")


        # Determine overall status based *only* on parsing results here
        final_status = "warning" # Default if nothing found
        message_parts = []
        if valid_tokens:
             message_parts.append(f"Parsed {len(valid_tokens)} potential tokens")
             final_status = "success"
        if failed_validation > 0:
             message_parts.append(f"{failed_validation} failed validation")
             if final_status != "success": final_status = "error" # Prioritize error if no success
        if skipped > 0:
             message_parts.append(f"{skipped} skipped due to structure")
             if final_status == "warning": final_status = "warning" # If only skipped, it's warning

        final_message = ", ".join(message_parts) + "." if message_parts else "No valid tokens found in the 2FAS file to import."

        return {
            "status": final_status,
            "message": final_message, # Initial parse message
            "valid_tokens": valid_tokens,
            "skipped": skipped,
            "failed_validation": failed_validation
        }

    except json.JSONDecodeError:
        return {"status": "error", "message": "Invalid JSON format in 2FAS file",
                "valid_tokens": [], "skipped": 0, "failed_validation": 0}
    except Exception as e:
        return {"status": "error", "message": f"Failed to parse 2FAS JSON: {str(e)}",
                "valid_tokens": [], "skipped": 0, "failed_validation": 0} 