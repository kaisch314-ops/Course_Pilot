from app.iteration import iterate,invalidate,affinity
from copy import deepcopy

def event(i,tag='shared',direction=1):return {'id':str(i),'course':str(i),'tags':[tag],'reason':'interest','direction':direction,'time':f'2026-11-{i+1:02d}'}
doc={'feedback':[event(i,tag=('unique'+str(i)) if i<4 else 'shared') for i in range(10)]}
iterate(doc)
assert doc['iteration']['evaluations'][-1]['status']=='promoted'
assert doc['iteration']['active_gain']==1.5
n=len(doc['iteration']['evaluations']);iterate(doc);assert len(doc['iteration']['evaluations'])==n
invalidate(doc);assert doc['iteration']['active_gain']==1
small={'feedback':[event(0) for _ in range(20)]};iterate(small);assert small['iteration']['evaluations'][-1]['status']=='insufficient_data'
# Contradictory future evidence must not force a promotion.
bad={'feedback':[event(i,tag=('unique'+str(i)) if i<4 else 'shared',direction=1 if i<8 else -1) for i in range(10)]};iterate(bad);assert bad['iteration']['evaluations'][-1]['status']=='rejected'
assert bad['iteration']['active_gain']==1
print('PASS: held-out promotion/rejection, minimum unique-course sample, replay suppression, rollback')

# Editing an already-tested course cannot masquerade as a fresh evaluation.
replay={'feedback':[event(i,tag=('unique'+str(i)) if i<4 else 'shared') for i in range(10)]}
iterate(replay)
replay['feedback'][-1]['direction']=-1
iterate(replay)
assert replay['iteration']['evaluations'][-1]['status']=='waiting_new_test'
print('PASS: previously tested courses cannot be reused as fresh holdout')
