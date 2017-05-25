# Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.

# Licensed under the Amazon Software License (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at

#    http://aws.amazon.com/asl/

# or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions and limitations under the License.
from progressmonitor import ProgressMonitor, ProgressTracker, DynamoDbDriver
root = ProgressMonitor(DbConnection=DynamoDbDriver(TablePrefix='test'),
                       Name="MasterWorkflow")
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
task_b2_1.start(Parents=True)
print "Total items started: {}".format(root.in_progress_count)
print "Percentage started: {}".format(root.in_progress_pct)
root.update_all()
id = root.id
root2 = ProgressMonitor(DbConnection=DynamoDbDriver)
print "Total items: {}".format(root2.all_children_count)
root2 = root.load(id)
print "Total items started: {}".format(root2.in_progress_count)
print "Percentage started: {}".format(root2.in_progress_pct)
print "Refreshing . . ."
root2.refresh()
print "Total items started: {}".format(root2.in_progress_count)
print "Percentage started: {}".format(root2.in_progress_pct)
