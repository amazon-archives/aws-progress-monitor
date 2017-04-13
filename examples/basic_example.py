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
task = ProgressTracker(Name='SingleTask', FriendlyId='MyTask')
pm.with_tracker(task)
print pm.status, task.status
print pm.start()
print pm.status, task.status
time.sleep(1)
print pm.elapsed_time_in_seconds, task.elapsed_time_in_seconds
task.start()
time.sleep(1)
print pm.status, task.status
print pm.elapsed_time_in_seconds, task.elapsed_time_in_seconds
task.succeed()
pm.succeed()
print pm.status, task.status
print pm.elapsed_time_in_seconds, task.elapsed_time_in_seconds

