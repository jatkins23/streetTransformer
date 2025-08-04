## move to validators.py ##
from pathlib import Path
from errors import *

def check_file_extension(file_path, allowed_extensions):
    ext = Path(file_path).suffix.lower()

    if ext not in allowed_extensions:
        raise InvalidFileExtensionError(ext, allowed_extensions)

    return True


def check_file_exists(file_path):
    file_path = Path(file_path)
    
    if not file_path.is_file():
        raise ResourceNotFound("File", file_path)
    
    return True

def check_value(value, valid_values, value_name=None):
    value_descr = value_name if value_name else "Value"

    if value not in valid_values:
        raise ResourceNotFound(value_descr, value, valid_values)
    
    return True
