from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4
class DeploymentMode(str, Enum):
    INITIAL='initial'; RESUME='resume'; INCREMENTAL='incremental'
@dataclass(frozen=True)
class DeploymentContext:
    entity_type:str; project_id:str; organization_id:str; batch_size:int=500
    mode:DeploymentMode=DeploymentMode.INITIAL; initiated_by:str|None=None
    local_project_path:str|None=None; deployment_id:str=field(default_factory=lambda:str(uuid4()))
    started_at:datetime=field(default_factory=lambda:datetime.now(timezone.utc))
    metadata:dict[str,Any]=field(default_factory=dict)
    def __post_init__(self):
        if not self.entity_type.strip(): raise ValueError('entity_type est obligatoire.')
        if not self.project_id.strip(): raise ValueError('project_id est obligatoire.')
        if not self.organization_id.strip(): raise ValueError('organization_id est obligatoire.')
        if self.batch_size<=0: raise ValueError('batch_size doit être strictement positif.')
