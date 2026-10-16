class ValidationError(Exception):
    status=422
class VersionConflict(ValidationError):
    status=409
class AllocationExceeded(ValidationError):
    pass
class AlreadyShipped(ValidationError):
    pass
