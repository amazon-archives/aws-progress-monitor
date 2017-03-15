import redis
import time
from progressinsight import RedisProgressManager, ProgressInsight, \
    ProgressTracker
pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
r = redis.Redis(connection_pool=pool)
rpm = RedisProgressManager(RedisConnection=r)
pm = ProgressInsight(DbConnection=rpm, Name="MasterWorkflow")
task = ProgressTracker(Name='SingleTask', FriendlyId='MyTask')
pm.with_tracker(task)
print pm.status, task.status
print pm.start()
print pm.status, task.status
time.sleep(1)
print pm.elapsed_time_in_seconds(), task.elapsed_time_in_seconds()
task.start()
time.sleep(1)
print pm.status, task.status
print pm.elapsed_time_in_seconds(), task.elapsed_time_in_seconds()
task.succeed()
pm.succeed()
print pm.status, task.status
print pm.elapsed_time_in_seconds(), task.elapsed_time_in_seconds()

