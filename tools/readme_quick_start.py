import redis
from progressmagician import RedisProgressManager, ProgressMagician, ProgressTracker
pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
rpm = RedisProgressManager(RedisConnection=redis.Redis(connection_pool=pool))
pm = ProgressMagician(DbConnection=rpm)
c = ProgressTracker(Name='ConvertVMWorkflow')
e = ProgressTracker(Name='ExportImage', ParentId=c.id)
f = ProgressTracker(Name='ConvertImage', ParentId=c.id)
g = ProgressTracker(Name='UploadImage', ParentId=c.id)
h = ProgressTracker(Name='NotifyCompleteStatus', ParentId=c.id)
pm.with_tracker(c).with_tracker(e).with_tracker(f).with_tracker(g) \
   .with_tracker(h)
pm.update_all()
print pm.count_children()

# pm = ProgressMagician(ProgressManager=rpm, Key='abc')
# a = ProgressEvent(ProgressTotal=10, Key='def')
# b = ProgressEvent(ProgressTotal=10, Key='hij')
# c = ProgressEvent(ProgressTotal=10, Key='123')
# d = ProgressEvent(ProgressTotal=10, Key='456')
# pm.with_event(a)
# pm.with_event(c)
# a.with_event(b)
# c.with_event(d)
