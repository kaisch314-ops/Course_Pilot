from app.main import COURSES,OFFERINGS,bootstrap
from app.models import StudentProfile
from app.solver import score_course
p=StudentProfile(**bootstrap()['default_profile'])
o=next(o for o in OFFERINGS if COURSES[o.code].tags)
c=COURSES[o.code]
p.interests=[]
a=score_course(c,o,p)[0]
p.affinity={t:1 for t in c.tags}
b=score_course(c,o,p)[0]
assert b>a,(a,b)
p.affinity={}
assert score_course(c,o,p)[0]==a
print('PASS: learned affinity changes score and withdrawal restores baseline')
