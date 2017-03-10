import uuid
from progressmagician import ProgressTracker, ProgressMagician, TrackerBase
from progressmagician import RedisProgressManager
import time
import pytest
from mock import patch
import json
import arrow

redis_data = """
    {
       "abc:def":
       {
           "key": "abc:def",
           "name": "workflow1",
       },
       "abc:ghi":
       {
           "key": "abc:ghi",
           "name": "workflow2",
       },
       "ghi:jkl":
       {
           "key": "ghi:jkl",
           "name": "workflow3",
       }
    }
"""

not_started_json = """
{
"94a52a41-bf9e-43e3-9650-859f7c263dc8": {
"st": "Not started",
"in_p": "False",
"d": "False",
"name": "None",
"l_u": "2017-03-07T10:41:20.875748+00:00"
},
"7acfd432-8392-49d3-867c-d85bb3824e61": {
"d": "False",
"l_u": "2017-03-07T10:43:56.398706+00:00",
"pid": "94a52a41-bf9e-43e3-9650-859f7c263dc8",
"st": "No Started",
"in_p": "False",
"name": "ConvertVMWorkflow"
},
"582ab745-2929-47a1-b026-6a09db268688": {
"d": "False",
"l_u": "2017-03-07T10:41:20.875748+00:00",
"pid": "7acfd432-8392-49d3-867c-d85bb3824e61",
"st": "Not started",
"in_p": "False",
"name": "NotifyCompleteStatus"
},
"c31405c9-d44b-4c28-b4ca-7008de4e468a": {
"d": "False",
"l_u": "2017-03-07T10:41:20.875748+00:00",
"pid": "7acfd432-8392-49d3-867c-d85bb3824e61",
"st": "Not started",
"in_p": "False",
"name": "ConvertImage"
},
"6cf22931-d571-41f9-b1db-b47740e680f3": {
"d": "False",
"l_u": "2017-03-07T10:41:20.875748+00:00",
"pid": "7acfd432-8392-49d3-867c-d85bb3824e61",
"st": "Not started",
"in_p": "False",
"name": "ExportImage"
},
"039fe353-2c01-49f4-a743-b09c02c9f683": {
"d": "False",
"l_u": "2017-03-07T10:41:20.875748+00:00",
"pid": "7acfd432-8392-49d3-867c-d85bb3824e61",
"st": "Not started",
"in_p": "False",
"name": "UploadImage"
}
}
"""


class MockProgressManager(object):
    def get_all_by_key(self, key):
        return None

    def add_tracker(self, e):
        return None

    def inc_progress(self, e, value):
        return None

    def update_tracker(self, pt):
        return None


def test_can_create_rollup_event():
    r = ProgressTracker(Id='test')
    assert r.id == 'test'


def test_can_total_progress_with_child_events():
    pm = ProgressMagician(DbConnection=MockProgressManager())
    a = ProgressTracker(Name='CopyFiles', FriendlyId='abc')
    b = ProgressTracker(Name='CreateFolder')
    c = ProgressTracker(Name='CopyFiles')
    d = ProgressTracker(Name='SendEmail')
    a.with_tracker(b)
    b.with_tracker(c).with_tracker(d)
    pm.with_tracker(a)
    assert len(pm.all_children) == 4


def test_can_total_progress_off_one_branch():
    a = setup_basic().find_friendly_id('a')
    assert len(a.all_children) == 2


def setup_basic():
    pm = ProgressMagician(Name='MainWorkflow',
                          DbConnection=MockProgressManager(),
                          EstimatedSeconds=10)
    a = ProgressTracker(Name='CopyFiles', FriendlyId='a')
    b = ProgressTracker(Name='CreateFolder', FriendlyId='b')
    c = ProgressTracker(Name='CopyFiles', FriendlyId='c')
    assert a.friendly_id == 'a'
    a.with_tracker(b)
    b.with_tracker(c)
    pm.with_tracker(a)
    return pm


def test_not_found_friendly_id_returns_none():
    pm = setup_basic()
    assert not pm.find_friendly_id('f')


def test_find_a_tracker_by_friendly_id():
    pm = setup_basic()
    assert pm.find_friendly_id('a')


def test_find_a_parent_tracker():
    b = setup_basic().find_friendly_id('b')
    assert b.parent.friendly_id == 'a'


def test_start_tracker_sets_in_progress():
    t = setup_basic().find_friendly_id('a')
    t.parent.start()
    t.start()
    assert t.is_in_progress


def test_starting_tracker_without_starting_parent_throws_error():
    t = setup_basic().find_friendly_id('a')
    with pytest.raises(Exception) as e:
        t.start()

    assert "You can't start a tracker if the parent isn't started" in \
        str(e.value)


def test_start_tracker_starts_timer():
    t = setup_basic().find_friendly_id('a')
    t.parent.start()
    t.start()
    time.sleep(2.1)
    assert t.elapsed_time_in_seconds() > 2 and \
        t.elapsed_time_in_seconds() < 3


def test_multiple_trackers_track_separately():
    pm = setup_basic()
    pm.start()
    a = pm.find_friendly_id('a')
    b = pm.find_friendly_id('b')
    a.start()
    time.sleep(2.1)
    b.start()
    time.sleep(2.1)
    assert b.elapsed_time_in_seconds() > 2 and \
        b.elapsed_time_in_seconds() < 3
    assert a.elapsed_time_in_seconds() > 4 and \
        a.elapsed_time_in_seconds() < 5


def test_can_set_status():
    a = setup_basic().find_friendly_id('a').with_status_msg('test status')
    assert a.status_msg == 'test status'


def test_no_estimate_returns_none_remaining_time():
    a = setup_basic()
    a.start()
    time.sleep(1)
    assert a.remaining_time_in_seconds() is None


def test_remaining_returns_actual_minus_estimate():
    pm = setup_basic()
    pm.start()
    time.sleep(1.5)
    assert pm.remaining_time_in_seconds() < 9


def test_can_get_full_key():
    pm = setup_basic()
    b = pm.find_friendly_id('b')
    assert b.get_full_key() == b.id


def test_root_full_key_is_just_id():
    pm = setup_basic()
    assert pm.get_full_key() == pm.id


@patch('tests.test_progressmagician.MockProgressManager')
def test_update_calls_db_update(db_mock):
    pm = setup_basic()
    pm.update()
    assert db_mock.called_once()


@patch('tests.test_progressmagician.MockProgressManager.update_tracker')
def test_multiple_update_calls_db_update_only_once(db_mock):
    pm = setup_basic()
    pm.update().update()
    assert db_mock.called_once()


@patch('tests.test_progressmagician.MockProgressManager.update_tracker')
def test_child_object_saves_parent_object(db_mock):
    a = setup_basic().find_friendly_id('a')
    a.update()
    assert db_mock.call_count == 2


def test_child_update_clears_dirty_flag():
    a = setup_basic().find_friendly_id('a')
    a.update()
    assert not a.is_dirty and not a.parent.is_dirty


def test_with_metric_sets_has_metric_flag():
    a = setup_basic().find_friendly_id('a')
    a.with_metric(Namespace='ns', Metric='m')
    assert a.has_metric()


def test_no_metric_sets_has_no_metric_flag():
    a = setup_basic().find_friendly_id('a')
    assert not a.has_metric()


@patch('fluentmetrics.metric.FluentMetric.seconds')
@patch('fluentmetrics.metric.FluentMetric.count')
def test_success_logs_two_metrics(s_mock, c_mock):
    a = setup_basic().find_friendly_id('a').with_metric(Namespace='ns',
                                                        Metric='m')
    a.start(Parents=True)
    time.sleep(.5)
    a.succeed()
    assert s_mock.call_count == 1 and c_mock.call_count == 1 and \
        a.status == 'Succeeded' and a.is_done and not a.is_in_progress and \
        a.finish_time


@patch('fluentmetrics.metric.FluentMetric.seconds')
@patch('fluentmetrics.metric.FluentMetric.count')
def test_success_stops_timer(s_mock, c_mock):
    a = setup_basic().find_friendly_id('a').with_metric(Namespace='ns',
                                                        Metric='m')
    a.start(Parents=True)
    time.sleep(.25)
    a.succeed()
    f = a.finish_time
    time.sleep(.25)
    assert a.finish_time == f


@patch('fluentmetrics.metric.FluentMetric.seconds')
@patch('fluentmetrics.metric.FluentMetric.count')
def test_failed_logs_two_metrics(s_mock, c_mock):
    a = setup_basic().find_friendly_id('a').with_metric(Namespace='ns',
                                                        Metric='m')
    a.start(Parents=True)
    time.sleep(.5)
    a.fail()
    assert s_mock.call_count == 1 and c_mock.call_count == 1 and \
        a.status == 'Failed' and a.is_done and not a.is_in_progress and \
        a.finish_time


@patch('fluentmetrics.metric.FluentMetric.seconds')
@patch('fluentmetrics.metric.FluentMetric.count')
def test_fail_stops_timer(s_mock, c_mock):
    a = setup_basic().find_friendly_id('a').with_metric(Namespace='ns',
                                                        Metric='m')
    a.start(Parents=True)
    time.sleep(.25)
    a.fail()
    f = a.finish_time
    time.sleep(.25)
    assert a.finish_time == f


@patch('fluentmetrics.metric.FluentMetric.seconds')
@patch('fluentmetrics.metric.FluentMetric.count')
def test_canceled_logs_two_metrics(s_mock, c_mock):
    a = setup_basic().find_friendly_id('a').with_metric(Namespace='ns',
                                                        Metric='m')
    a.start(Parents=True)
    time.sleep(.5)
    a.cancel()
    assert s_mock.call_count == 1 and c_mock.call_count == 1 and \
        a.status == 'Canceled' and a.is_done and not a.is_in_progress and \
        a.finish_time


def test_can_convert_name_from_json():
    n = str(uuid.uuid4())
    a = setup_basic().find_friendly_id('a')
    j = a.with_name(n).to_json()
    t = TrackerBase.from_json(a.id, j)
    assert t.name == n


def test_can_convert_start_time_from_json():
    start = arrow.utcnow()
    pm = setup_basic()
    a = pm.find_friendly_id('a')
    j = a.start(Parents=True, StartTime=start).to_json()
    t = TrackerBase.from_json(a.id, j)
    print t.start_time
    print start
    assert t.start_time == start


def test_can_convert_in_canceled_status_from_json():
    a = setup_basic().find_friendly_id('a').cancel()
    t = TrackerBase.from_json(a.id, a.to_json())
    assert t.status == 'Canceled' and t.is_done and not t.is_in_progress


def test_can_convert_in_failed_status_from_json():
    a = setup_basic().find_friendly_id('a').fail()
    t = TrackerBase.from_json(a.id, a.to_json())
    assert t.status == 'Failed' and t.is_done and not t.is_in_progress


def test_can_convert_in_succeed_status_from_json():
    a = setup_basic().find_friendly_id('a').succeed()
    t = TrackerBase.from_json(a.id, a.to_json())
    assert t.status == 'Succeeded' and t.is_done and not t.is_in_progress


def get_by_id_side_effect(id):
    items = json.loads(not_started_json)
    if id in items.keys():
        return items[id]
    return None


def children_side_effect(id):
    if id == '94a52a41-bf9e-43e3-9650-859f7c263dc8':
        return ['7acfd432-8392-49d3-867c-d85bb3824e61']

    if id == '7acfd432-8392-49d3-867c-d85bb3824e61':
        return ['582ab745-2929-47a1-b026-6a09db268688',
                'c31405c9-d44b-4c28-b4ca-7008de4e468a',
                '6cf22931-d571-41f9-b1db-b47740e680f3',
                '039fe353-2c01-49f4-a743-b09c02c9f683']

    return None


@patch('progressmagician.RedisProgressManager.get_by_id')
@patch('progressmagician.RedisProgressManager.get_children')
def test_can_convert_from_db(c_mock, g_mock):
    g_mock.side_effect = get_by_id_side_effect
    c_mock.side_effect = children_side_effect
    pm = ProgressMagician(DbConnection=RedisProgressManager())
    pm = pm.load('94a52a41-bf9e-43e3-9650-859f7c263dc8')
    assert len(pm.all_children) == 5


@patch('progressmagician.RedisProgressManager.get_by_id')
@patch('progressmagician.RedisProgressManager.get_children')
def test_can_start_all_parents(c_mock, g_mock):
    g_mock.side_effect = get_by_id_side_effect
    c_mock.side_effect = children_side_effect
    pm = ProgressMagician(DbConnection=RedisProgressManager())
    pm = pm.load('94a52a41-bf9e-43e3-9650-859f7c263dc8')
    t = pm.find_id('039fe353-2c01-49f4-a743-b09c02c9f683')
    assert t
    t.start(Parents=True)
    assert t.parent.status == 'In Progress'
    print t.parent.id
    assert t.parent.parent.status == 'In Progress'


def test_getting_elapsed_time_at_parent_returns_longest_child():
    main = setup_basic().main
    b = main.find_friendly_id('b')
    c = main.find_friendly_id('c')
    b.start(Parents=True)
    time.sleep(1.25)
    c.start(Parents=True)
    time.sleep(2)
    assert main.elapsed_time_in_seconds() > 3


def test_start_with_status_msg_updates_msg():
    s = str(uuid.uuid4())
    a = setup_basic().find_friendly_id('a')
    a.start(Message=s, Parents=True)
    assert a.status_msg == s


def test_fail_with_status_msg_updates_msg():
    s = str(uuid.uuid4())
    a = setup_basic().find_friendly_id('a')
    assert a.start(Parents=True).fail(Message=s).status_msg == s


def test_cancel_with_status_msg_updates_msg():
    s = str(uuid.uuid4())
    a = setup_basic().find_friendly_id('a')
    assert a.start(Parents=True).cancel(Message=s).status_msg == s


def test_succeed_with_status_msg_updates_msg():
    s = str(uuid.uuid4())
    a = setup_basic().find_friendly_id('a')
    assert a.start(Parents=True).succeed(Message=s).status_msg == s


def test_can_get_in_progress_trackers():
    pm = setup_basic()
    a = pm.find_friendly_id('a')
    c = pm.find_friendly_id('c')
    c.start(Parents=True)
    assert a.in_progress_count == 2


def test_can_get_canceled_trackers():
    pm = setup_basic()
    a = pm.find_friendly_id('a')
    c = pm.find_friendly_id('c')
    c.start(Parents=True).cancel()
    assert a.canceled_count == 1


def test_no_started_returns_0_canceled_trackers():
    pm = setup_basic()
    assert pm.not_started_count == 3


def test_no_in_progress_returns_0_in_progress_trackers():
    pm = setup_basic()
    assert pm.in_progress_count == 0


def test_no_canceled_returns_0_canceled_trackers():
    pm = setup_basic()
    assert pm.canceled_count == 0


def test_can_get_started_pct_correctly():
    pm = setup_basic()
    pm.find_friendly_id('a').start(Parents=True)
    assert pm.in_progress_pct == .33


def test_can_get_not_started_pct_correctly():
    pm = setup_basic()
    assert pm.not_started_pct == 1
