# ProgressInsight
## First Things First
Please make sure to review the [current AWS CloudWatch Custom Metrics pricing]( https://aws.amazon.com/cloudwatch/pricing/) before proceeding. 
## Overview
`ProgressInsight` is an easy-to-use Python module that gives you a powerful way to track real-time progress and metrics around the progress of multi-level workflow processes.
## Features
* Unlimited levels of workflows and tasks
* Track progress at any level from the root workflow to a specific task
* View % done, % remaining, time completed, time remaining on the entire workflow or any sub-workflow/task
* Dynamically add new workflows/tasks at any time
* Automatically log metrics to CloudWatch Custom Metrics as workflows/tasks are completed
* Supports parallel workflows
* User-provided estimates at the task level
* ElastiCache data store manages each workflow/task as a separate record for minimal collision
## Installation
You can install directly from PyPI:
```sh
pip install progressinsight
```
## What problem are we trying to solve?
Imagine long-running step functions or a workflow that has many child workflows (e.g., syncing all of my S3 buckets, importing several VM instances, etc.), each with many processes running across many machines. How do you know the progress of the entire workflow? How do you easily log metrics that tie back to the workflow? `ProgressInsight` uses ElastiCache and CloudWatch Custom Metrics to solve the problem of managing the real-time status of the entire workflow or any part of the workflow.
## `ProgressInsight` Simply Explained
In the simplest of terms, `ProgressInsight` is a nested set of `ProgressTracker` objects that mirror your tasks and workflows. All you need to do is add trackers as children to other trackers. You can add estimated times for the tasks. After that, all you need to do is start and stop trackers as work is done. `ProgressInsight` does all the magic of rolling up the progress and status across the entire workflow.  
## Terminology
`ProgressInsight` is meant to provide simplicity to progress tracking, so at its core, it uses a single `ProgressTracker` class. A `ProgressTracker` represents any distinct unit of work, either a workflow or a specific task.
### Examples
#### Example: Single Task
This is the most basic of basic applications. We create a `ProgressInsight` object (which is a `ProgressTracker`), which is required to create a new workflow tracker. Then we create another tracker called `SingleTask`. Each tracker has an `id` property that is an automatically generated `uuid`. If you want to use your own unique ID as well (from some other process), you can pass in a `FriendlyId` as well, which is accessible by the `friendly_id` property. All we need to do is call `with_tracker` and the `SingleTask` tracker is attached to the root workflow.

```sh
import redis
import time
from progressinsight import RedisProgressManager, ProgressInsight, \
    ProgressTracker
pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
r = redis.Redis(connection_pool=pool)
# this is this data store manager for ProgressInsight
redispm = RedisProgressManager(RedisConnection=r)

# create the master workflow using Redis as the backing store
root_workflow = ProgressInsight(DbConnection=redispm, Name="MasterWorkflow")

# this is a single task that we want to track
task = ProgressTracker(Name='SingleTask', FriendlyId='MyTask')

# this magic command adds the task to the main workflow
root_workflow.with_tracker(task)
print root_workflow.status, task.status

# start the main workflow, but don't start the task yet
print root_workflow.start()
print root_workflow.status, task.status
time.sleep(1)

# we can see elapsed time on any tracker
print root_workflow.elapsed_time_in_seconds(), task.elapsed_time_in_seconds()

# now we start the task
task.start()
time.sleep(1)

# the task is now one second behind the main workflow
print root_workflow.status, task.status
print root_workflow.elapsed_time_in_seconds(), task.elapsed_time_in_seconds()

# we're going to mark the task and the main workflow successfully done, which stops the timer
task.succeed()
root_workflow.succeed()
print root_workflow.status, task.status
print root_workflow.elapsed_time_in_seconds(), task.elapsed_time_in_seconds()
```
#### Example: Single Task (Output)
```sh
Not started Not started
MasterWorkflow
In Progress Not started
1.001271 0
In Progress In Progress
2.003592 1.002901
Succeeded Succeeded
2.007596 1.004904
```
#### Example: Multiple Tasks
We're now adding three tasks to the root workflow. This also demonstrates how you can stop a task with `succeed`, `fail` or `cancel` with a status message.
```sh
import redis
import time
from progressinsight import RedisProgressManager, ProgressInsight, ProgressTracker
pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
r = redis.Redis(connection_pool=pool)
redispm = RedisProgressManager(RedisConnection=r)
root_wf = ProgressInsight(DbConnection=redispm, Name="MasterWorkflow")

# we're creating three separate tasks
task_a = ProgressTracker(Name='Task A', FriendlyId='TaskA')
task_b = ProgressTracker(Name='Task B', FriendlyId='TaskB')
task_c = ProgressTracker(Name='Task C', FriendlyId='TaskC')

# all three tasks are added to the main workflow
root_wf.with_tracker(task_a).with_tracker(task_b).with_tracker(task_c)
print root_wf.status, task_a.status
print root_wf.start()
print root_wf.status, task_a.status, task_b.status, task_c.status
time.sleep(1)

# each task is started and tracked independently from the other tasks
task_a.start()
time.sleep(1)
task_b.start()
time.sleep(1)
task_c.start()
print root_wf.elapsed_time_in_seconds(), \
      task_a.elapsed_time_in_seconds(), \
      task_b.elapsed_time_in_seconds(), \
      task_c.elapsed_time_in_seconds()

# any task can succeed, fail, cancel or pause, all of which stop the timer
# any task can also take a status Message parameter, which is saved with the task to provide a custom real-time status message along with the actual Status
task_a.succeed(Message='This task succeeded')
task_b.fail(Message='This task failed')
task_c.cancel(Message='This task canceled')
root_wf.fail()
print root_wf.status, task_a.status, task_b.status, task_c.status
print root_wf.elapsed_time_in_seconds(), \
      task_a.elapsed_time_in_seconds(), \
      task_b.elapsed_time_in_seconds(), \
      task_c.elapsed_time_in_seconds()
print task_b.status_msg
```
#### Example: Multiple Tasks (Output)
```sh
Not started Not started
MasterWorkflow
In Progress Not started Not started Not started
3.006041 2.001023 1.00046 0.0
Failed Succeeded Failed Canceled
3.007544 2.001507 1.001963 0.001503
This task failed
```
#### Example: Sub-Workflows
We're starting to add some complexity here by adding subworkflows and tasks. Notice that both workflows and tasks are `ProgressTracker` objects. The only difference between a "workflow" and a "task" is that a workflow has child trackers. 
```sh
import redis
from progressinsight import RedisProgressManager, ProgressInsight, \
    ProgressTracker
pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
r = redis.Redis(connection_pool=pool)
redispm = RedisProgressManager(RedisConnection=r)
root_wf = ProgressInsight(DbConnection=redispm, Name="MasterWorkflow")

# we're creating two progress trackers under the master progress tracker
wf_a = ProgressTracker(Name='Workflow A', FriendlyId='WorkflowA')
wf_b = ProgressTracker(Name='Workflow B', FriendlyId='WorkflowB')

# we're creating two progress trackers under Workflow B
wf_b_1 = ProgressTracker(Name='SubWorkflow B1', FriendlyId='WorkflowB1')
wf_b_2 = ProgressTracker(Name='SubWorkflow B2', FriendlyId='WorkflowB2')

# we're creating two progress trackers under Workflow A
task_a1 = ProgressTracker(Name='Task A-1', FriendlyId='TaskA1')
task_a2 = ProgressTracker(Name='Task A-2', FriendlyId='TaskA2')

# we're creating a progress tracker under SubWorkflow B1
task_b2_1 = ProgressTracker(Name='Task B2-1', FriendlyId='TaskB21')

# wire up all the trackers
root_wf.with_tracker(wf_a).with_tracker(wf_b)
wf_b.with_tracker(wf_b_1).with_tracker(wf_b_2)
wf_a.with_tracker(task_a1).with_tracker(task_a2)
wf_b_2.with_tracker(task_b2_1)

# every tracker has the same properties
print "Total items in workflow: {}".format(root_wf.all_children_count)
print "Total items not started: {}".format(root_wf.not_started_count)
print task_b2_1.status, wf_b_2.status, wf_b.status, root_wf.status

# when you start a tracker, the parent has to be started as well . . . `Parents=True` tells `ProgressInsight` to automatically start all parents up the tree
task_b2_1.start(Parents=True)

# we can print out _count and _pct for any metric and it will include all children . . . in this case, we're getting all in_progress items in the entire tree 
print "Total items started: {}".format(root_wf.in_progress_count)
print "Percentage started: {}".format(root_wf.in_progress_pct)
print task_b2_1.status, wf_b_2.status, wf_b.status, root_wf.status
task_b2_1.succeed()

# we've succeeded only one task in the tree . . .we can get the status of the whole workflow and/or the status of Subworkflow B2, which is now 100% done
print "Total items done: {}".format(root_wf.done_count)
print "Percentage done: {}".format(root_wf.done_pct)
print "Subworkflow B2 total items: {}".format(wf_b_2.all_children_count)
print "Subworkflow B2 items done: {}".format(wf_b_2.done_count)
print "Subworkflow B2 percentage done: {}".format(wf_b_2.done_pct)
print task_b2_1.status, wf_b_2.status, wf_b.status, root_wf.status
```
#### Example: Sub-Workflows (OUTPUT)
```sh
Total items in workflow: 7
Total items not started: 7
Not started Not started Not started Not started
Total items started: 3
Percentage started: 0.43
In Progress In Progress In Progress In Progress
Total items done: 1
Total Percentage done: 0.14
Subworkflow B2 total items: 1
Subworkflow B2 items done: 1
Subworkflow B2 percentage done: 1.0
Succeeded In Progress In Progress In Progress
```
#### Example: Saving to ElastiCache (Redis)
In this example, we're saving the current state of the workflow with `update_all`. To maximize performance, every tracker has an `is_dirty` flag. When you call `update_all`, only trackers that are changed will be saved. So if you have 1,000 trackers in your workflow and only one has changed, we'll only make a single update call. 
```sh
import redis
from progressinsight import RedisProgressManager, ProgressInsight, \
    ProgressTracker
pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
r = redis.Redis(connection_pool=pool)
redispm = RedisProgressManager(RedisConnection=r)

# create the same trackers as the previous example
root_wf = ProgressInsight(DbConnection=redispm, Name="MasterWorkflow")
wf_a = ProgressTracker(Name='Workflow A', FriendlyId='WorkflowA')
wf_b = ProgressTracker(Name='Workflow B', FriendlyId='WorkflowB')
wf_b_1 = ProgressTracker(Name='SubWorkflow B1', FriendlyId='WorkflowB1')
wf_b_2 = ProgressTracker(Name='SubWorkflow B2', FriendlyId='WorkflowB2')
task_a1 = ProgressTracker(Name='Task A-1', FriendlyId='TaskA1')
task_a2 = ProgressTracker(Name='Task A-2', FriendlyId='TaskA2')
task_b2_1 = ProgressTracker(Name='Task B2-1', FriendlyId='TaskB21')
root_wf.with_tracker(wf_a).with_tracker(wf_b)
wf_b.with_tracker(wf_b_1).with_tracker(wf_b_2)
wf_a.with_tracker(task_a1).with_tracker(task_a2)
wf_b_2.with_tracker(task_b2_1)
task_b2_1.start(Parents=True)

# print current values for comparison
print "Total items started: {}".format(root_wf.in_progress_count)
print "Percentage started: {}".format(root_wf.in_progress_pct)

# the update_all command saves all children to ElastiCache
root_wf.update_all()

# every tracker generates a GUID . . . let's grab this so we can load it from the DB 
id = root_wf.id

# create a new tracker with no children
pm2 = ProgressInsight(DbConnection=redispm)
print "Total items: {}".format(pm2.all_children_count)

# load the tracker and all children from ElastiCache by ID
pm2 = pm2.load(id)
print "Total items started: {}".format(pm2.in_progress_count)
print "Percentage started: {}".format(pm2.in_progress_pct)
```
#### Example: Saving to ElastiCache (OUTPUT)
```sh
Total items started: 3
Percentage started: 0.43
Total items: 0
Total items started: 3
Percentage started: 0.43
```
#### Example: Working with a single subworkflow
Suppose you have a very large complex workflow with lots and lots of subworkflows and tasks. You have a process that only works on a specific workflow or task. it doesn't make any sense to load the entirety of the massive workflow just to track the progress of a single workflow or task. `ProgressInsight` makes this easy. You can pass in the `id` of any tracker and the `ProgressInsight` object will return just that workflow.
```sh
import redis
from progressinsight import RedisProgressManager, ProgressInsight, \
    ProgressTracker
pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
r = redis.Redis(connection_pool=pool)
redispm = RedisProgressManager(RedisConnection=r)

# setup all the trackers
root_wf = ProgressInsight(DbConnection=redispm, Name="MasterWorkflow")
wf_a = ProgressTracker(Name='Workflow A', FriendlyId='WorkflowA')
wf_b = ProgressTracker(Name='Workflow B', FriendlyId='WorkflowB')
wf_b_1 = ProgressTracker(Name='SubWorkflow B1', FriendlyId='WorkflowB1')
wf_b_2 = ProgressTracker(Name='SubWorkflow B2', FriendlyId='WorkflowB2')
task_a1 = ProgressTracker(Name='Task A-1', FriendlyId='TaskA1')
task_a2 = ProgressTracker(Name='Task A-2', FriendlyId='TaskA2')
task_b2_1 = ProgressTracker(Name='Task B2-1', FriendlyId='TaskB21')
root_wf.with_tracker(wf_a).with_tracker(wf_b)
wf_b.with_tracker(wf_b_1).with_tracker(wf_b_2)
wf_a.with_tracker(task_a1).with_tracker(task_a2)
wf_b_2.with_tracker(task_b2_1)
task_b2_1.start(Parents=True)

# here we are printing the total in-progress items in the entire workflow
print "Total items started: {}".format(root_wf.in_progress_count)
print "Percentage started: {}".format(root_wf.in_progress_pct)
root_wf.update_all()

# grab the id from Workflow B
id = wf_b.id

# we're going to just load Workflow B
pm2 = root_wf.load(id)

# so now we are only working with Workflow B
print "Total items started: {}".format(pm2.in_progress_count)
print "Percentage started: {}".format(pm2.in_progress_pct)
```
#### Example: Workin with a single subworkflow (OUTPUT)
```sh
Total items started: 3
Percentage started: 0.43
Total items: 0
Total items started: 2
Percentage started: 0.67
```
#### Example: Using estimates
When you create a tracker, you can pass in an estimated number of seconds that you believe the tracker will run. Estimates are only added at the task level, meaning that if you create a tracker with an estimated time and then add child trackers, you'll have a conflict. If you have a `BackupFolder` tracker with two child trackers `CreateFolder` and `CopyFiles`, you *can't* have an estimated time on `CreateFolder` and `CopyFiles` *as well as* `BackupFolder`. Estimated times are ignored for a tracker if that tracker has child trackers.
```sh
import redis
import time
from progressinsight import RedisProgressManager, ProgressInsight, \
    ProgressTracker
pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
r = redis.Redis(connection_pool=pool)
redispm = RedisProgressManager(RedisConnection=r)

# setup the trackers
root_wf = ProgressInsight(DbConnection=redispm, Name="MasterWorkflow")
wf_a = ProgressTracker(Name='Workflow A', FriendlyId='WorkflowA')
wf_b = ProgressTracker(Name='Workflow B', FriendlyId='WorkflowB')
wf_b_1 = ProgressTracker(Name='SubWorkflow B1', FriendlyId='WorkflowB1')
wf_b_2 = ProgressTracker(Name='SubWorkflow B2', FriendlyId='WorkflowB2')

# each of these tasks has a 10 second estimate
task_a1 = ProgressTracker(Name='Task A-1', EstimatedSeconds=10)
task_a2 = ProgressTracker(Name='Task A-2', EstimatedSeconds=10)
task_b2_1 = ProgressTracker(Name='Task B2-1', EstimatedSeconds=10)
root_wf.with_tracker(wf_a).with_tracker(wf_b)
wf_b.with_tracker(wf_b_1).with_tracker(wf_b_2)
wf_a.with_tracker(task_a1).with_tracker(task_a2)
wf_b_2.with_tracker(task_b2_1)
print "Total estimated seconds: {}".format(root_wf.total_estimate)
task_b2_1.start(Parents=True)
time.sleep(2)

# we can elapsed and remaining time at any level
print "Elapsed time in seconds: {}".format(root_wf.elapsed_time_in_seconds)
print "Remaining time in seconds: {}".format(root_wf.remaining_time_in_seconds)
print "Workflow B elapsed time: {}".format(wf_b_2.elapsed_time_in_seconds)
print "Workflow B remaining time: {}".format(wf_b_2.remaining_time_in_seconds)
```
#### Example: Using estimates (OUTPUT)
```sh
Total estimated seconds: 30
Total elapsed time in secs: 2.000171
Total remaining time in secs: 27.99955
Workflow B elapsed time: 2.00171
Workflow B remaining time: 7.997763
```
#### Example: Using parallel workflows with estimates
When you want to run work workflows in parallel, obviously we don't want to add up all the estimates. We want to estimate based on running in parallel. In this case, we estimate a total of each parallel workflow and return the longest estimate.
```sh
import redis
from progressinsight import RedisProgressManager, ProgressInsight, \
    ProgressTracker
pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
r = redis.Redis(connection_pool=pool)
redispm = RedisProgressManager(RedisConnection=r)
root_wf = ProgressInsight(DbConnection=redispm, Name="MasterWorkflow")

# we need to flag that this workflow's children run in parallel
wf_a = ProgressTracker(Name='Workflow A', FriendlyId='WorkflowA',
                       HasParallelChildren=True)
wf_b = ProgressTracker(Name='Workflow B', FriendlyId='WorkflowB')
wf_b_1 = ProgressTracker(Name='SubWorkflow B1', FriendlyId='WorkflowB1')
wf_b_2 = ProgressTracker(Name='SubWorkflow B2', FriendlyId='WorkflowB2')

# Workflow A Task A-1 has a 10-second estimate 
task_a1 = ProgressTracker(Name='Task A-1', EstimatedSeconds=10)
wf_a_1 = ProgressTracker(Name='SubWorkflow A1')

# Workflow A, Subworkflow A1 has a total of 50 seconds estimate
wf_a1_1 = ProgressTracker(Name='SubWorkflow A1, Task 1', EstimatedSeconds=20)
wf_a1_2 = ProgressTracker(Name='SubWorkflow A1, Task 2', EstimatedSeconds=30)
root_wf.with_tracker(wf_a).with_tracker(wf_b)
wf_b.with_tracker(wf_b_1).with_tracker(wf_b_2)
wf_a_1.with_tracker(wf_a1_1).with_tracker(wf_a1_2)
wf_a.with_tracker(task_a1).with_tracker(wf_a_1)

# total_estimate automatically finds the longest estimate under the parallel workflows
print "Total estimated seconds: {}".format(root_wf.total_estimate)
```
#### Example: Using parallel workflows with estimates (OUTPUT)
```sh
Total estimated seconds: 50
```
#### Example: Automatically logging metrics
One of the really valuable aspects of `ProgressInsight` is the ability to log performance metrics to CloudWatch. This allows `ProgressInsight` to be not only a real-time progress visibility tool, but also a performance insight tool as well. All you need to do is attach a metric namespace and metric name to any tracker you want metrics and `ProgressInsight` does the rest. When you start and stop a tracker, the timing is automatically logged to CloudWatch with the metric name you provide. Additionally, if you want more dimensions to the metrics, you can easily add those as well to generate richer data.

```sh
import redis
import time
from progressinsight import RedisProgressManager, ProgressInsight, ProgressTracker
pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
r = redis.Redis(connection_pool=pool)
rpm = RedisProgressManager(RedisConnection=r)
pm = ProgressInsight(DbConnection=rpm)

# Create a tracker and attach to the 'OS/Startup' metric in the 'dev_testing' namespace 
c = ProgressTracker(Name='TestWorkflow').with_metric(Namespace='dev_testing',
                                                          Metric='OS/Startup')

# adding Linux flavor and version to create a few richer metrics
c.metric.with_dimension('linux_flavor', 'redhat') \
        .with_dimension('version', '6.8')
        
# notice that we no longer refer to the metrics -- it's all behind-the-scenes now
pm.with_tracker(c)
pm.update_all()
c.start(Parents=True)
pm.update_all()
print 'sleeping'
time.sleep(2)

# this command will automatically check if there is a metrics and log to CloudWatch
c.succeed()
pm.update_all()
print c.elapsed_time_in_seconds
print c.start_time
print c.finish_time
```