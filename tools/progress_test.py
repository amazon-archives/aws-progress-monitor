import redis
from rollupmagic import RedisProgressManager, ProgressMagician, ProgressTracker
pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
r = redis.Redis(connection_pool=pool)
rpm = RedisProgressManager(RedisConnection=r)
pm = ProgressMagician(DbConnection=rpm)
pm.load('92567a99-edd3-4338-9175-57e82593e1b2')
pm.start()
pm.update_all()
exit()
print pm.count_children()
c = pm.find_id('887098c0-59eb-43d7-87af-ead1af79ac8b')
print c.parent().id
c.parent().start()
c.start()
print c.parent().parent().status
print c.parent().status
print c.status
pm.update_all()
# c = pm.find_id('7acfd432-8392-49d3-867c-d85bb3824e61')
#pm.load('0fba41ac-1e0b-46c4-95da-4369e0b2d541')
#c = pm.find_id('87cecef3-aa34-4da3-bda9-e2ccb7d0fff8')
# c.start()
#print c.status
#c.update()
exit()
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
