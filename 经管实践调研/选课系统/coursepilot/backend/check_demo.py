"""Regression scenarios for the demonstration, run from backend."""
from app.main import COURSES, OFFERINGS, SEED, bootstrap, solve
from app.models import StudentProfile, Session
from app.solver import _mask

profile = StudentProfile(**bootstrap()["default_profile"])
profile.blocked = [Session(day=3, start=5, end=9, location="实践")]
profile.interests = ["计量", "实证", "量化"]
result = solve(profile)
assert result.schedules, result.diagnostics
first = result.schedules[0]
assert {x.code for x in first.items} >= {"FI3101","FI3102","FI3103","FI3104"}
used = _mask(profile.blocked)
for item in first.items:
    occupied = _mask(item.sessions)
    assert not occupied & used
    used |= occupied
profile.locked = [next(x.offering_id for x in first.items if x.code=="FI3104")]
profile.excluded = [next(x.offering_id for x in first.items if x.code=="FI3101")]
replacement = solve(profile)
assert replacement.schedules, replacement.diagnostics
for s in replacement.schedules:
    chosen = {x.offering_id for x in s.items}
    assert set(profile.locked) <= chosen and not chosen.intersection(profile.excluded)
profile.excluded.extend(o.id for o in OFFERINGS if o.code=="FI3101")
assert not solve(profile).schedules
slot = Session(day=1,start=1,end=2,location="",weeks=[1,3])
assert not _mask([slot]) & _mask([slot.model_copy(update={"weeks":[2,4]})])
print("PASS: required courses, blocked times, locking, replacement, infeasibility, disjoint weeks")
