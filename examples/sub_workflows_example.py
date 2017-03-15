import redis
from progressinsight import RedisProgressManager, ProgressInsight, \
    ProgressTracker
pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
r = redis.Redis(connection_pool=pool)
rpm = RedisProgressManager(RedisConnection=r)
pm = ProgressInsight(DbConnection=rpm, Name="MasterWorkflow")
wf_a = ProgressTracker(Name='Workflow A', FriendlyId='WorkflowA')
wf_b = ProgressTracker(Name='Workflow B', FriendlyId='WorkflowB')
wf_b_1 = ProgressTracker(Name='SubWorkflow B1', FriendlyId='WorkflowB1')
wf_b_2 = ProgressTracker(Name='SubWorkflow B2', FriendlyId='WorkflowB2')
task_a1 = ProgressTracker(Name='Task A-1', FriendlyId='TaskA1')
task_a2 = ProgressTracker(Name='Task A-2', FriendlyId='TaskA2')
task_b2_1 = ProgressTracker(Name='Task B2-1', FriendlyId='TaskB21')
pm.with_tracker(wf_a).with_tracker(wf_b)
wf_b.with_tracker(wf_b_1).with_tracker(wf_b_2)
wf_a.with_tracker(task_a1).with_tracker(task_a2)
wf_b_2.with_tracker(task_b2_1)
print "Total items in workflow: {}".format(pm.all_children_count)
print "Total items not started: {}".format(pm.not_started_count)
print task_b2_1.status, wf_b_2.status, wf_b.status, pm.status
task_b2_1.start(Parents=True)
print "Total items started: {}".format(pm.in_progress_count)
print "Percentage started: {}".format(pm.in_progress_pct)
print task_b2_1.status, wf_b_2.status, wf_b.status, pm.status
task_b2_1.succeed()
print "Total items done: {}".format(pm.done_count)
print "Total Percentage done: {}".format(pm.done_pct)
print "Subworkflow B2 total items: {}".format(wf_b_2.all_children_count)
print "Subworkflow B2 items done: {}".format(wf_b_2.done_count)
print "Subworkflow B2 percentage done: {}".format(wf_b_2.done_pct)
print task_b2_1.status, wf_b_2.status, wf_b.status, pm.status
