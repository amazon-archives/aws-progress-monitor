import uuid
from rollupmagic import ProgressTracker, ProgressMagician, TrackerBase
from rollupmagic import RedisProgressManager
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
"in_p": "True",
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
    b = ProgressTracker(Name='CreateFolder', ParentId=a.id)
    c = ProgressTracker(Name='CopyFiles', ParentId=b.id)
    pm.with_tracker(a).with_tracker(b).with_tracker(c)
    assert pm.count_children() == 3


def test_can_total_progress_off_one_branch():
    a = setup_basic().find_friendly_id('a')
    assert a.count_children() == 2


def setup_basic():
    pm = ProgressMagician(Name='MainWorkflow',
                          DbConnection=MockProgressManager(),
                          EstimatedSeconds=10)
    a = ProgressTracker(Name='CopyFiles', FriendlyId='a')
    b = ProgressTracker(Name='CreateFolder', ParentId=a.id, FriendlyId='b')
    c = ProgressTracker(Name='CopyFiles', ParentId=b.id, FriendlyId='c')
    pm.with_tracker(a).with_tracker(b).with_tracker(c)
    return pm


def test_not_found_friendly_id_returns_none():
    pm = setup_basic()
    assert not pm.find_friendly_id('f')


def test_find_a_tracker_by_friendly_id():
    pm = setup_basic()
    assert pm.find_friendly_id('a')


def test_find_a_parent_tracker():
    b = setup_basic().find_friendly_id('b')
    assert b.parent().friendly_id == 'a'


def test_start_tracker_sets_in_progress():
    t = setup_basic().find_friendly_id('a')
    t.parent().start()
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
    t.parent().start()
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
    a = pm.find_friendly_id('a')
    b = pm.find_friendly_id('b')
    assert b.get_full_key() == "{}:{}".format(a.id, b.id)


def test_root_full_key_is_just_id():
    pm = setup_basic()
    assert pm.get_full_key() == pm.id


@patch('tests.test_rollupmagic.MockProgressManager')
def test_update_calls_db_update(db_mock):
    pm = setup_basic()
    pm.update()
    assert db_mock.called_once()


@patch('tests.test_rollupmagic.MockProgressManager.update_tracker')
def test_multiple_update_calls_db_update_only_once(db_mock):
    pm = setup_basic()
    pm.update().update()
    assert db_mock.called_once()


@patch('tests.test_rollupmagic.MockProgressManager.update_tracker')
def test_child_object_saves_parent_object(db_mock):
    a = setup_basic().find_friendly_id('a')
    a.update()
    assert db_mock.call_count == 2


def test_child_update_clears_dirty_flag():
    a = setup_basic().find_friendly_id('a')
    a.update()
    assert not a.is_dirty and not a.parent().is_dirty


def test_can_convert_name_from_json():
    n = str(uuid.uuid4())
    a = setup_basic().find_friendly_id('a')
    j = a.with_name(n).to_json()
    t = TrackerBase.from_json(a.id, j)
    assert t.name == n


def test_can_convert_start_time_from_json():
    start = arrow.utcnow()
    pm = setup_basic().start()
    a = pm.find_friendly_id('a').parent().start()
    j = a.start(StartTime=start).to_json()
    t = TrackerBase.from_json(a.id, j)
    assert t.start_time == start


def test_can_convert_children_from_json():
    a = setup_basic().find_friendly_id('a')
    t = TrackerBase.from_json(a.id, a.to_json())
    assert t.children == a.children


def test_can_convert_in_canceled_status_from_json():
    a = setup_basic().find_friendly_id('a').cancel()
    t = TrackerBase.from_json(a.id, a.to_json())
    assert t.status == 'Canceled' and t.done and not t.is_in_progress


def test_can_convert_in_failed_status_from_json():
    a = setup_basic().find_friendly_id('a').fail()
    t = TrackerBase.from_json(a.id, a.to_json())
    assert t.status == 'Failed' and t.done and not t.is_in_progress


def test_can_convert_in_succeed_status_from_json():
    a = setup_basic().find_friendly_id('a').succeed()
    t = TrackerBase.from_json(a.id, a.to_json())
    assert t.status == 'Succeeded' and t.done and not t.is_in_progress


def get_by_id_side_effect(id):
    if id == 'test':
        print 'loading test'
        return json.loads(not_started_json)
    return None


def children_side_effect(id):
    if id == 'test':
        return ['582ab745-2929-47a1-b026-6a09db268688',
                '7acfd432-8392-49d3-867c-d85bb3824e61',
                'c31405c9-d44b-4c28-b4ca-7008de4e468a',
                '6cf22931-d571-41f9-b1db-b47740e680f3',
                '039fe353-2c01-49f4-a743-b09c02c9f683']
    return None


@patch('rollupmagic.RedisProgressManager.get_by_id')
@patch('rollupmagic.RedisProgressManager.get_children')
def test_can_convert_from_db(c_mock, g_mock):
    c_mock.return_value = get_by_id_side_effect
    c_mock.side_effect = children_side_effect
    pm = ProgressMagician(DbConnection=RedisProgressManager())
    pm.load('test')
    assert pm.count_children() == 5


@patch('rollupmagic.RedisProgressManager.get_by_id')
@patch('rollupmagic.RedisProgressManager.get_children')
def test_can_convert_from_db(c_mock, g_mock):
    c_mock.return_value = get_by_id_side_effect
    c_mock.side_effect = children_side_effect
    pm = ProgressMagician(DbConnection=RedisProgressManager())
    pm.load('test')
    assert pm.count_children() == 5

