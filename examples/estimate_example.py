# Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.

# Licensed under the Amazon Software License (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at

#    http://aws.amazon.com/asl/

# or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions and limitations under the License.
import redis
import time
from progressmonitor import RedisProgressManager, ProgressMonitor, \
    ProgressTracker
pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
r = redis.Redis(connection_pool=pool)
rpm = RedisProgressManager(RedisConnection=r)
pm = ProgressMonitor(DbConnection=rpm, Name="MasterWorkflow")
wf_a = ProgressTracker(Name='Workflow A', FriendlyId='WorkflowA')
wf_b = ProgressTracker(Name='Workflow B', FriendlyId='WorkflowB')
wf_b_1 = ProgressTracker(Name='SubWorkflow B1', FriendlyId='WorkflowB1')
wf_b_2 = ProgressTracker(Name='SubWorkflow B2', FriendlyId='WorkflowB2')
task_a1 = ProgressTracker(Name='Task A-1', EstimatedSeconds=10)
task_a2 = ProgressTracker(Name='Task A-2', EstimatedSeconds=10)
task_b2_1 = ProgressTracker(Name='Task B2-1', EstimatedSeconds=10)
task_b2_1_a = ProgressTracker(Name='Task B2-1-a', EstimatedSeconds=10)
pm.with_tracker(wf_a).with_tracker(wf_b)
wf_b.with_tracker(wf_b_1).with_tracker(wf_b_2)
wf_a.with_tracker(task_a1).with_tracker(task_a2)
wf_b_2.with_tracker(task_b2_1)
task_b2_1.with_tracker(task_b2_1_a)
print "Total estimated seconds: {}".format(pm.total_estimate)
task_b2_1.start(Parents=True)
time.sleep(2)
print "Total elapsed time in secs: {}".format(pm.elapsed_time_in_seconds)
print "Total remaining time in secs: {}".format(pm.remaining_time_in_seconds)
print "Workflow B elapsed time: {}".format(wf_b_2.elapsed_time_in_seconds)
print "Workflow B remaining time: {}".format(wf_b_2.remaining_time_in_seconds)

print pm.print_tree()
