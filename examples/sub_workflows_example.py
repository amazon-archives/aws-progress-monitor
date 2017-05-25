# Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.

# Licensed under the Amazon Software License (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at

#    http://aws.amazon.com/asl/

# or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions and limitations under the License.
import redis
from progressinsight import RedisProgressManager, ProgressInsight, \
    ProgressTracker
pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
r = redis.Redis(connection_pool=pool)
rroot = RedisProgressManager(RedisConnection=r)
root = ProgressInsight(DbConnection=rroot, Name="MasterWorkflow")
wf_a = ProgressTracker(Name='Workflow A', FriendlyId='WorkflowA')
wf_b = ProgressTracker(Name='Workflow B', FriendlyId='WorkflowB')
wf_b_1 = ProgressTracker(Name='SubWorkflow B1', FriendlyId='WorkflowB1')
wf_b_2 = ProgressTracker(Name='SubWorkflow B2', FriendlyId='WorkflowB2')
task_a1 = ProgressTracker(Name='Task A-1', FriendlyId='TaskA1')
task_a2 = ProgressTracker(Name='Task A-2', FriendlyId='TaskA2')
task_b2_1 = ProgressTracker(Name='Task B2-1', FriendlyId='TaskB21')
root.with_tracker(wf_a).with_tracker(wf_b)
wf_b.with_tracker(wf_b_1).with_tracker(wf_b_2)
wf_a.with_tracker(task_a1).with_tracker(task_a2)
wf_b_2.with_tracker(task_b2_1)
print "Total items in workflow: {}".format(root.all_children_count)
print "Total items not started: {}".format(root.not_started_count)
print task_b2_1.status, wf_b_2.status, wf_b.status, root.status
task_b2_1.start(Parents=True)
print "Total items started: {}".format(root.in_progress_count)
print "Percentage started: {}".format(root.in_progress_pct)
print task_b2_1.status, wf_b_2.status, wf_b.status, root.status
task_b2_1.succeed()
print "Total items done: {}".format(root.done_count)
print "Total Percentage done: {}".format(root.done_pct)
print "Subworkflow B2 total items: {}".format(wf_b_2.all_children_count)
print "Subworkflow B2 items done: {}".format(wf_b_2.done_count)
print "Subworkflow B2 percentage done: {}".format(wf_b_2.done_pct)
print task_b2_1.status, wf_b_2.status, wf_b.status, root.status
