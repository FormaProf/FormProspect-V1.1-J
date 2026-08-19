from __future__ import annotations
from dataclasses import dataclass
from math import ceil
from typing import Generic, Iterator, Sequence, TypeVar
T=TypeVar('T')
@dataclass(frozen=True)
class DeploymentBatch(Generic[T]):
    number:int; offset:int; items:tuple[T,...]; total_items:int; batch_size:int
    @property
    def count(self): return len(self.items)
    @property
    def is_last(self): return self.offset+self.count>=self.total_items
class DeploymentBatchPlanner:
    @staticmethod
    def total_batches(total_items:int,batch_size:int)->int:
        if batch_size<=0: raise ValueError('batch_size doit être strictement positif.')
        return 0 if total_items<=0 else ceil(total_items/batch_size)
    @staticmethod
    def from_sequence(items:Sequence[T],*,batch_size:int,start_offset:int=0)->Iterator[DeploymentBatch[T]]:
        if batch_size<=0: raise ValueError('batch_size doit être strictement positif.')
        if start_offset<0: raise ValueError('start_offset ne peut pas être négatif.')
        total=len(items); number=(start_offset//batch_size)+1
        for offset in range(start_offset,total,batch_size):
            yield DeploymentBatch(number,offset,tuple(items[offset:offset+batch_size]),total,batch_size); number+=1
