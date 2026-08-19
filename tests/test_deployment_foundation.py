import unittest
from services.deployment import DeploymentBatchPlanner, DeploymentContext, DeploymentEngine, DeploymentHandler, DeploymentMapper, DeploymentStatus
class Mapper(DeploymentMapper):
    def map_item(self,item,context): return {'value':item,'project_id':context.project_id}
class Handler(DeploymentHandler):
    def __init__(self): self.items=[]
    def handle_batch(self,*,context,batch): self.items.extend(batch.items); return {'created':batch.count}
class Tests(unittest.TestCase):
    def test_batches(self):
        b=list(DeploymentBatchPlanner.from_sequence(list(range(12)),batch_size=5)); self.assertEqual([x.count for x in b],[5,5,2]); self.assertTrue(b[-1].is_last)
    def test_engine(self):
        c=DeploymentContext(entity_type='prospect',project_id='p1',organization_id='o1',batch_size=2); h=Handler(); r=DeploymentEngine(mapper=Mapper(),handler=h).run(context=c,source_items=[1,2,3,4,5]); self.assertEqual(r.status,DeploymentStatus.SUCCESS); self.assertEqual(r.progress.created,5)
    def test_invalid_batch(self):
        with self.assertRaises(ValueError): DeploymentContext(entity_type='prospect',project_id='p1',organization_id='o1',batch_size=0)
