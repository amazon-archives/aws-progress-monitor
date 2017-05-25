# Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.

# Licensed under the Amazon Software License (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at

#    http://aws.amazon.com/asl/

# or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions and limitations under the License.
import redis
import time
from progressinsight import RedisProgressManager, ProgressInsight, \
    ProgressTracker
pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
r = redis.Redis(connection_pool=pool)
rpm = RedisProgressManager(RedisConnection=r)
pm = ProgressInsight(DbConnection=rpm, Name="MasterWorkflow")
task_a = ProgressTracker(Name='Task A', FriendlyId='TaskA')
task_b = ProgressTracker(Name='Task B', FriendlyId='TaskB')
task_c = ProgressTracker(Name='Task C', FriendlyId='TaskC')
pm.with_tracker(task_a).with_tracker(task_b).with_tracker(task_c)
print pm.status, task_a.status
print pm.start()
print pm.status, task_a.status, task_b.status, task_c.status
time.sleep(1)
task_a.start()
time.sleep(1)
task_b.start()
time.sleep(1)
task_c.start()
print pm.elapsed_time_in_seconds, \
      task_a.elapsed_time_in_seconds, \
      task_b.elapsed_time_in_seconds, \
      task_c.elapsed_time_in_seconds

task_a.succeed(Message='This task succeeded')
task_b.fail(Message='This task failed')
task_c.cancel(Message='This task canceled')
pm.fail()
print pm.status, task_a.status, task_b.status, task_c.status
print pm.elapsed_time_in_seconds, \
      task_a.elapsed_time_in_seconds, \
      task_b.elapsed_time_in_seconds, \
      task_c.elapsed_time_in_seconds
print task_b.status_msg
