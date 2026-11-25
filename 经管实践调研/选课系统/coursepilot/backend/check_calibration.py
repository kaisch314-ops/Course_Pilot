from app.main import COURSES, SEED
from app.calibration import calibrate
from app.iteration import iterate
from copy import deepcopy
courses=list(COURSES.values())[:3]
doc={'outcomes':{}}
original={c.code:c.profile.weekly_hours for c in courses}
for i,c in enumerate(courses):doc['outcomes'][c.code]={'id':str(i),'course':c.code,'term':SEED['term'],'status':'completed','actual_weekly_hours':c.profile.weekly_hours*2,'predicted_weekly_hours':c.profile.weekly_hours}
p,a=calibrate(doc,COURSES,SEED['term']);assert a['factor']==1.2
assert p[courses[0].code].profile.weekly_hours==round(original[courses[0].code]*1.2,2)
assert all(c.profile.weekly_hours==original[c.code] for c in courses)
assert calibrate({},COURSES,SEED['term'])[1]['factor']==1
assert calibrate(doc,COURSES,'other-term')[1]['samples']==0
del doc['outcomes'][courses[0].code]
assert calibrate(doc,COURSES,SEED['term'])[1]['factor']==1
for r in doc['outcomes'].values():r['status']='not_selected'
assert calibrate(doc,COURSES,SEED['term'])[1]['samples']==0
print('PASS: personal-only calibration, cap, sample threshold, withdrawal, term and status isolation')
