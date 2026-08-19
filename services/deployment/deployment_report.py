from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
class DeploymentStatus(str,Enum): SUCCESS='success'; PARTIAL='partial'; CANCELLED='cancelled'; FAILED='failed'
@dataclass(frozen=True)
class DeploymentIssue:
    message:str; code:str='deployment_error'; batch_number:int|None=None; item_reference:str|None=None; details:dict[str,Any]=field(default_factory=dict)
@dataclass(frozen=True)
class DeploymentReport:
    context:object; status:DeploymentStatus; progress:object; finished_at:datetime; issues:tuple=(); metadata:dict=field(default_factory=dict)
    @classmethod
    def build(cls,*,context,status,progress,issues=(),metadata=None): return cls(context,status,progress,datetime.now(timezone.utc),issues,dict(metadata or {}))
