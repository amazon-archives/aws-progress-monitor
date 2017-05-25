# Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.

# Licensed under the Amazon Software License (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at

#    http://aws.amazon.com/asl/

# or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions and limitations under the License.
import redis
import time
from progressmonitor import RedisProgressManager, ProgressMonitor, ProgressTracker
pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
r = redis.Redis(connection_pool=pool)
rpm = RedisProgressManager(RedisConnection=r)
pm = ProgressMonitor(DbConnection=rpm)
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
