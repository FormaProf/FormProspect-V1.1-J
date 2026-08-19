from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from .deployment_errors import MappingError
S=TypeVar('S'); T=TypeVar('T')
class DeploymentMapper(ABC,Generic[S,T]):
    @abstractmethod
    def map_item(self,item,context): raise NotImplementedError
    def map_items(self,items,context):
        out=[]
        for i,item in enumerate(items):
            try: out.append(self.map_item(item,context))
            except MappingError: raise
            except Exception as exc: raise MappingError(f"Impossible de convertir l'élément à l'index {i}.") from exc
        return tuple(out)
