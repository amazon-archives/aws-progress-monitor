import redis
import time
from progressinsight import RedisProgressManager, ProgressInsight, ProgressTracker
pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
r = redis.Redis(connection_pool=pool)
rpm = RedisProgressManager(RedisConnection=r)
pm = ProgressInsight(DbConnection=rpm)
c = ProgressTracker(Name='TestWorkflow').with_metric(Namespace='dev_testing',
                                                          Metric='OS/Startup')
c.metric.with_dimension('linux_flavor', 'redhat') \
        .with_dimension('version', '6.8')
pm.with_tracker(c)
pm.update_all()
c.start(Parents=True)
pm.update_all()
print 'sleeping'
time.sleep(2)
c.succeed()
pm.update_all()
print c.elapsed_time_in_seconds
print c.start_time
print c.finish_time
