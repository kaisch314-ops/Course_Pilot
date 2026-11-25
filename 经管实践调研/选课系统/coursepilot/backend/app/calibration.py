"""Personal workload calibration, separate from official course descriptions."""
from statistics import median

def calibrate(doc, courses, term):
    records={}
    for r in doc.get('outcomes',{}).values():
        if (r.get('term')==term and r['status']=='completed' and r.get('actual_weekly_hours') is not None and r.get('predicted_weekly_hours',0)>0):
            records[r['course']]=r
    samples=list(records.values())
    factor=1.0
    if len(samples)>=3:
        ratio=median(r['actual_weekly_hours']/r['predicted_weekly_hours'] for r in samples)
        # Shrink toward baseline; bounded personal adjustment, not a causal estimate.
        factor=max(.8,min(1.2,1+(ratio-1)*len(samples)/(len(samples)+5)))
    audit={'method':'median_ratio_shrinkage_v1','samples':len(samples),'factor':factor,'source_ids':[r['id'] for r in samples],'status':'applied' if len(samples)>=3 else 'insufficient_data'}
    personal={}
    for code,course in courses.items():
        clone=course.model_copy(deep=True)
        clone.profile.weekly_hours=round(course.profile.weekly_hours*factor,2)
        if factor!=1:clone.profile.summary+=f' 个人负荷估计参考 {len(samples)} 门已完成课程的自报投入校准，非官方课程说明。'
        personal[code]=clone
    return personal,audit
