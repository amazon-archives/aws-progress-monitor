import redis
from rollupmagic import RedisProgressManager, ProgressMagician, ProgressEvent
pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
r = redis.Redis(connection_pool=pool)
rpm = RedisProgressManager(RedisConnection=r)
pm = ProgressMagician(ProgressManager=rpm)
pm.load('abc')

# pm = ProgressMagician(ProgressManager=rpm, Key='abc')
# a = ProgressEvent(ProgressTotal=10, Key='def')
# b = ProgressEvent(ProgressTotal=10, Key='hij')
# c = ProgressEvent(ProgressTotal=10, Key='123')
# d = ProgressEvent(ProgressTotal=10, Key='456')
# pm.with_event(a)
# pm.with_event(c)
# a.with_event(b)
# c.with_event(d)
