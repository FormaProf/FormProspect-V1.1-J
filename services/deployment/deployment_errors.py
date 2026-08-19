class DeploymentError(RuntimeError): pass
class DeploymentStateError(DeploymentError): pass
class DeploymentCancelled(DeploymentError): pass
class DeploymentInterrupted(DeploymentError): pass
class SynchronizationError(DeploymentError): pass
class MappingError(DeploymentError): pass
class BatchImportError(DeploymentError):
    def __init__(self, message, *, batch_number=None, cause=None):
        super().__init__(message); self.batch_number=batch_number; self.cause=cause
