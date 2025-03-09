import json

def read_json(file_path):
    """Read and parse a JSON file
    
    Args:
        file_path (str): Path to the JSON file
        
    Returns:
        dict: The parsed JSON data or an empty dict if file not found or invalid
    """
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            print(f"Successfully loaded {len(data)} tokens from {file_path}")
            return data
    except FileNotFoundError:
        print(f"File not found: {file_path}, creating empty token storage")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from {file_path}: {e}")
        return {}

def write_json(file_path, data):
    """Write data to a JSON file
    
    Args:
        file_path (str): Path to the JSON file
        data (dict): Data to write to the file
    """
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4) 