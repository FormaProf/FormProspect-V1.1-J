from abc import ABC, abstractmethod
from .deployment_batch import DeploymentBatch, DeploymentBatchPlanner
from .deployment_errors import BatchImportError, DeploymentCancelled, DeploymentStateError
from .deployment_progress import DeploymentProgress
from .deployment_report import DeploymentIssue, DeploymentReport, DeploymentStatus
class DeploymentHandler(ABC):
    @abstractmethod
    def handle_batch(self,*,context,batch): raise NotImplementedError
class DeploymentEngine:
    def __init__(self,*,mapper,handler): self.mapper=mapper; self.handler=handler; self._running=False; self._cancel_requested=False
    @property
    def is_running(self): return self._running
    def cancel(self): self._cancel_requested=True
    def run(self,*,context,source_items,start_offset=0,on_progress=None):
        if self._running: raise DeploymentStateError('Un déploiement est déjà en cours.')
        self._running=True; self._cancel_requested=False; issues=[]
        total=max(0,len(source_items)-start_offset); progress=DeploymentProgress(total=total,total_batches=DeploymentBatchPlanner.total_batches(total,context.batch_size))
        try:
            for src in DeploymentBatchPlanner.from_sequence(source_items,batch_size=context.batch_size,start_offset=start_offset):
                if self._cancel_requested: raise DeploymentCancelled('Déploiement annulé.')
                mapped=self.mapper.map_items(src.items,context)
                batch=DeploymentBatch(src.number,src.offset,mapped,src.total_items,src.batch_size)
                try: result=self.handler.handle_batch(context=context,batch=batch)
                except Exception as exc: raise BatchImportError('Le traitement du lot a échoué.',batch_number=batch.number,cause=exc) from exc
                snap=progress.advance(processed=batch.count,created=int(result.get('created',0)),updated=int(result.get('updated',0)),skipped=int(result.get('skipped',0)),failed=int(result.get('failed',0)),current_batch=batch.number)
                if on_progress: on_progress(snap)
            snap=progress.snapshot(); status=DeploymentStatus.PARTIAL if snap.failed else DeploymentStatus.SUCCESS
            return DeploymentReport.build(context=context,status=status,progress=snap)
        except DeploymentCancelled as exc:
            return DeploymentReport.build(context=context,status=DeploymentStatus.CANCELLED,progress=progress.snapshot(),issues=(DeploymentIssue(str(exc),'deployment_cancelled'),))
        except Exception as exc:
            bn=exc.batch_number if isinstance(exc,BatchImportError) else None
            return DeploymentReport.build(context=context,status=DeploymentStatus.FAILED,progress=progress.snapshot(),issues=(DeploymentIssue(str(exc),exc.__class__.__name__,bn),))
        finally: self._running=False
