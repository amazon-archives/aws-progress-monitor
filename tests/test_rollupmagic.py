from rollupmagic import ProgressTracker, ProgressMagician
import time
import pytest


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
    r = ProgressTracker(Key='test')
    assert r.key == 'test'


def test_can_total_progress_with_child_events():
    pm = ProgressMagician(ProgressManager=MockProgressManager())
    a = ProgressTracker(Name='CopyFiles', FriendlyId='abc')
    b = ProgressTracker(Name='CreateFolder', ParentId=a.id)
    c = ProgressTracker(Name='CopyFiles', ParentId=b.id)
    pm.with_tracker(a).with_tracker(b).with_tracker(c)
    assert pm.count_children() == 3


def test_can_total_progress_off_one_branch():
    pm = ProgressMagician(ProgressManager=MockProgressManager())
    a = ProgressTracker(Name='CopyFiles')
    b = ProgressTracker(Name='CreateFolder', ParentId=a.id)
    c = ProgressTracker(Name='CopyFiles', ParentId=b.id)
    d = ProgressTracker(Name='ImportVM')
    pm.with_tracker(a).with_tracker(b).with_tracker(c).with_tracker(d)
    assert a.count_children() == 2


def setup_basic():
    pm = ProgressMagician(ProgressManager=MockProgressManager(),
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
    assert t.is_in_progress()


def test_starting_tracker_without_starting_parent_throws_error():
    t = setup_basic().find_friendly_id('a')
    with pytest.raises(Exception) as e:
        t.start()

    assert "You can't start a tracker if the parent isn't started" in \
        str(e.value)


def test_start_tracker_starts_timer():
    t = setup_basic().find_friendly_id('a')
    t.start()
    time.sleep(2.1)
    assert t.elapsed_time_in_seconds() > 2 and \
        t.elapsed_time_in_seconds() < 3


def test_multiple_trackers_track_separately():
    a = setup_basic().find_friendly_id('a')
    b = setup_basic().find_friendly_id('b')
    a.start()
    time.sleep(2.1)
    b.start()
    time.sleep(2.1)
    assert b.elapsed_time_in_seconds() > 2 and \
        b.elapsed_time_in_seconds() < 3
    assert a.elapsed_time_in_seconds() > 4 and \
        a.elapsed_time_in_seconds() < 5


def test_can_set_status():
    a = setup_basic().find_friendly_id('a').with_status('test status')
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

