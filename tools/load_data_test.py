import redis
from progressmagician import RedisProgressManager, ProgressMagician
pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
r = redis.Redis(connection_pool=pool)
rpm = RedisProgressManager(RedisConnection=r)
pm = ProgressMagician(DbConnection=rpm)
pm.load('7b3aa95f-d6df-48db-876a-3e6b2f669aed')
print pm.main.start_time
print pm.main.elapsed_time_in_seconds()

