import redis
import time
from progressmagician import RedisProgressManager, ProgressMagician, ProgressTracker
pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
r = redis.Redis(connection_pool=pool)
rpm = RedisProgressManager(RedisConnection=r)
pm = ProgressMagician(DbConnection=rpm)
c = ProgressTracker(Name='ConvertVMWorkflow').with_metric(Namespace='test',
                                                          Metric='convert_vm')
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
print c.elapsed_time_in_seconds()
print c.start_time
print c.finish_time
