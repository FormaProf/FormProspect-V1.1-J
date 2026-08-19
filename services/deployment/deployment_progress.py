from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock
@dataclass(frozen=True)
class DeploymentProgressSnapshot:
    total:int; processed:int; created:int; updated:int; skipped:int; failed:int
    current_batch:int; total_batches:int; started_at:datetime; updated_at:datetime
    @property
    def percentage(self): return 100.0 if self.total<=0 else round(min(100.0,self.processed/self.total*100),2)
class DeploymentProgress:
    def __init__(self,*,total,total_batches):
        now=datetime.now(timezone.utc); self._lock=RLock(); self.total=total; self.processed=0; self.created=0; self.updated=0; self.skipped=0; self.failed=0; self.current_batch=0; self.total_batches=total_batches; self.started_at=now; self.updated_at=now
    def advance(self,*,processed,created=0,updated=0,skipped=0,failed=0,current_batch=None):
        with self._lock:
            self.processed+=processed; self.created+=created; self.updated+=updated; self.skipped+=skipped; self.failed+=failed
            if self.processed>self.total: raise ValueError('Le nombre traité dépasse le total annoncé.')
            if current_batch is not None: self.current_batch=current_batch
            self.updated_at=datetime.now(timezone.utc); return self.snapshot()
    def snapshot(self):
        return DeploymentProgressSnapshot(self.total,self.processed,self.created,self.updated,self.skipped,self.failed,self.current_batch,self.total_batches,self.started_at,self.updated_at)
