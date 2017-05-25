# Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.

# Licensed under the Amazon Software License (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at

#    http://aws.amazon.com/asl/

# or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions and limitations under the License.
import redis
from progressmonitor import RedisProgressManager, ProgressMonitor, \
    ProgressTracker
pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
r = redis.Redis(connection_pool=pool)
rpm = RedisProgressManager(RedisConnection=r)
pm = ProgressMonitor(DbConnection=rpm, Name="MasterWorkflow")
wf_a = ProgressTracker(Name='Workflow A', FriendlyId='WorkflowA',
                       HasParallelChildren=True)
wf_b = ProgressTracker(Name='Workflow B', FriendlyId='WorkflowB')
wf_b_1 = ProgressTracker(Name='SubWorkflow B1', FriendlyId='WorkflowB1')
wf_b_2 = ProgressTracker(Name='SubWorkflow B2', FriendlyId='WorkflowB2')
task_a1 = ProgressTracker(Name='Task A-1', EstimatedSeconds=10)
wf_a_1 = ProgressTracker(Name='SubWorkflow A1', HasParallelChildren=True)
wf_a1_1 = ProgressTracker(Name='SubWorkflow A1, Task 1', EstimatedSeconds=20)
wf_a1_2 = ProgressTracker(Name='SubWorkflow A1, Task 2', EstimatedSeconds=30)
pm.with_tracker(wf_a).with_tracker(wf_b)
wf_b.with_tracker(wf_b_1).with_tracker(wf_b_2)
wf_a_1.with_tracker(wf_a1_1).with_tracker(wf_a1_2)
wf_a.with_tracker(task_a1).with_tracker(wf_a_1)
print "Total estimated seconds: {}".format(pm.total_estimate)
