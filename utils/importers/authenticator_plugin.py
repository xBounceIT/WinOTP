import urllib.parse
import base64
import pyotp # Assuming pyotp is used for validation, add to requirements if needed

def is_valid_base32(s):
    """Check if a string is valid base32."""
    try:
        # Pad if necessary
        s += '=' * (-len(s) % 8)
        base64.b32decode(s.upper(), casefold=True)
        return True
    except Exception:
        return False

def parse_authenticator_plugin_export(file_content, progress_callback=None):
    """
    Parses the content of an Authenticator Browser Plugin export file (one otpauth URI per line).

    Args:
        file_content (str): The string content of the file.
        progress_callback (callable, optional): A function to call with progress updates 
                                                (current_line, total_lines). Defaults to None.

    Returns:
        dict: A dictionary containing:
            - valid_tokens (list): A list of dictionaries, each representing a valid token.
            - skipped (int): Number of lines skipped (not otpauth URIs or empty).
            - failed_validation (int): Number of otpauth URIs that failed parsing or validation.
            - total_lines (int): Total lines processed.
            - status (str): 'success', 'warning', or 'error'.
            - message (str): A summary message.
    """
    lines = file_content.strip().splitlines()
    total_lines = len(lines)
    valid_tokens = []
    skipped_lines = 0
    failed_validation = 0
    
    for i, line in enumerate(lines):
        line = line.strip()
        if progress_callback:
            try:
                progress_callback(i + 1, total_lines)
            except Exception as e:
                print(f"Error in progress callback: {e}") # Log callback error but continue

        if not line:
            skipped_lines += 1
            continue

        if not line.startswith('otpauth://'):
            print(f"Skipping line {i+1}: Does not start with otpauth://")
            skipped_lines += 1
            continue

        try:
            parsed_uri = urllib.parse.urlparse(line)
            params = urllib.parse.parse_qs(parsed_uri.query)
            
            secret = params.get('secret', [None])[0]
            issuer = params.get('issuer', [None])[0]
            
            # Extract label (name)
            path_parts = parsed_uri.path.split(':')
            name = "Unknown Name" # Default
            if len(path_parts) > 1:
                potential_name = urllib.parse.unquote(path_parts[-1].strip('/')) 
                if potential_name:
                    name = potential_name
                # If issuer is not in params, try getting it from the path before the name
                if not issuer and len(path_parts[0].strip('/')) > 0:
                   potential_issuer = urllib.parse.unquote(path_parts[0].strip('/'))
                   # Only use if it's not identical to the name
                   if potential_issuer and potential_issuer != name:
                       issuer = potential_issuer
            elif parsed_uri.path:
                 # Fallback if path format is unexpected but path exists
                 potential_name = urllib.parse.unquote(parsed_uri.path.strip('/'))
                 if potential_name:
                     name = potential_name

            # Clean up issuer and name if needed (e.g. if issuer is in the name part)
            if issuer and name and name.startswith(issuer + ':'):
                 name = name[len(issuer) + 1:].strip()
                 if not name: # Handle case where name becomes empty after stripping issuer
                     name = "Default" # Or some other placeholder

            if not secret:
                print(f"Skipping line {i+1}: No secret found in URI.")
                failed_validation += 1
                continue

            # Validate secret (must be base32)
            if not is_valid_base32(secret):
                 print(f"Skipping line {i+1}: Invalid base32 secret '{secret[:5]}...'.")
                 failed_validation += 1
                 continue

            # Use pyotp to further validate secret (optional but good)
            try:
                pyotp.TOTP(secret).now() 
            except Exception as e:
                print(f"Skipping line {i+1}: Secret '{secret[:5]}...' failed OTP generation check: {e}")
                failed_validation += 1
                continue

            # Assign default values if missing
            issuer = issuer if issuer else "Unknown Issuer"
            # Name already defaulted above

            valid_tokens.append({
                'issuer': issuer,
                'name': name,
                'secret': secret.upper() # Store secrets consistently
            })
            
        except Exception as e:
            print(f"Error parsing line {i+1}: {line} - {e}")
            failed_validation += 1

    # Determine status and message
    status = 'success'
    message = f"Successfully parsed {len(valid_tokens)} tokens."
    if failed_validation > 0:
        message += f" Failed to validate {failed_validation} URIs."
        status = 'warning' if len(valid_tokens) > 0 else 'error'
    if skipped_lines > 0:
         message += f" Skipped {skipped_lines} non-URI/empty lines."
         if status == 'success' and len(valid_tokens) == 0 and failed_validation == 0: # Only skipped lines
              status = 'warning'
              message = f"No valid otpauth URIs found. Skipped {skipped_lines} lines."
    elif len(valid_tokens) == 0 and failed_validation == 0: # Handle empty file case
        status = 'warning'
        message = "The selected file was empty or contained no processable lines."

    return {
        "valid_tokens": valid_tokens,
        "skipped": skipped_lines,
        "failed_validation": failed_validation,
        "total_lines": total_lines,
        "status": status,
        "message": message
    }