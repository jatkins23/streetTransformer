

class ProjectError(Exception):
    """Base class for all custom errors in the project."""
    def __init__(self, message="An error occurred", code=None):
        super().__init__(message)
        self.message = message
        self.code = code # Optional: can represent HTTP status or internal error code

    def __str__(self):
        return f"[{self.code}] {self.message}" if self.code else self.message
    
# --- Specific Error Classes --- #
class InvalidFileExtensionError(ProjectError):
    """Raised when a file extension is not allowed."""
    def __init__(self, extension, allowed_extensions=None):
        message = f"Invalid file extension: '{extension}'"
        if allowed_extensions:
            message = message + f"\n\tAllowed extensions: {', '.join(allowed_extensions)}."
        super().__init__(message, code=400)

class ResourceNotFound(ProjectError),:
    """Raised when a requested resource cannot be found."""
    def __init__(self, resource_type, identifier, resources_available=None):
        message = f"{resource_type} with ID '{identifier}' not found."
        if resources_available:
            message = message + f"\n\tPossible values: {', '.join(resources_available)}."
        super().__init__(message, code=404)
