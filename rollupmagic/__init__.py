import uuid
import arrow
import logging


class TrackerState(object):
    def __init__(self):
        self.totals = {}
        self.is_in_progress = False
        self.is_done = False
        self.is_failed = False
        self.is_errored = False
        self.is_cancelled = False
        self.is_partially_failed = False
        self.percent_done = 0
        self.start_time = None

    def start(self, **kwargs):
        self.start_time = arrow.utcnow()
        self.is_in_progress = True
        secs = kwargs.get("EstimatedSeconds", None)
        if secs:
            self.estimated_seconds = int(secs)
        else:
            self.estimated_seconds = None

    def elapsed_time_in_seconds(self):
        if not self.start_time:
            return 0
        return (arrow.utcnow() - self.start_time).total_seconds()

    def remaining_time_in_seconds(self):
        if self.estimated_seconds:
            if self.estimated_seconds > self.elapsed_time_in_seconds:
                return self.estimated_seconds - self.elapsed_time_in_seconds
        return None


class RedisProgressManager(object):
    def __init__(self, **kwargs):
        self.redis = kwargs.get('RedisConnection')

    def update_tracker(self, e):
        pipe = self.redis.pipeline(True)
        pipe.hmset(e.get_full_key(), e.to_json())
        pipe.hset(e.get_full_key(), 'prog_tot', e.progress_total)
        pipe.hset(e.get_full_key(), 'curr_prog', e.current_progress)
        pipe.execute()

    def get_all_by_key(self, key):
        items = {}
        # get all the items and sub-items for this key
        for k in sorted(self.redis.scan_iter('{}:*'.format(key))):
            # get all the data for this key
            data = self.redis.hgetall(k)
            print k, data
            items[k] = data

        return items

    def inc_progress(self, e, value=1):
        self.redis.hincrby(e.get_full_key(), "curr_prog", value)


class TrackerBase(object):
    def __init__(self, **kwargs):
        self.friendly_id = kwargs.get('FriendlyId', uuid.uuid4)
        self.id = str(uuid.uuid4())
        self.name = kwargs.get('Name')
        self.children = []
        self.state = TrackerState()
        self.estimated_seconds = kwargs.get('EstimatedSeconds', None)
        self.parent_id = kwargs.get('ParentId', None)

    def get_tracker_progress_total(self, pe=None):
        t = 0
        c = 0
        if pe is None:
            pe = self
        for k in pe.progress_trackers.keys():
            e = pe.progress_trackers[k]
            t = t + e.progress_total
            c = c + e.current_progress
        return c, t

    def get_progress_remaining(self):
        c, t = self.get_tracker_progress_total()
        return 1-(c/t)

    def get_progress_complete(self):
        c, t = self.get_tracker_progress_total()
        return c/t

    def get_full_key(self):
        if not self.parent_key:
            return self.friendly_id
        else:
            return "{}:{}".format(self.parent_id, self.id)

    def inc_progress(self, val=1):
        self.progress_manager.inc_progress(val)

    def count_children(self, id=None):
        tot = 0
        if id:
            t = self.trackers[id]
        else:
            t = self.trackers[self.id]
        if len(t.children):
            for k in t.children:
                tot = tot + self.count_children(k)
        tot = tot + len(t.children)
        print t.name, tot
        return tot

    def parent(self):
        if self.parent_id in self.trackers.keys():
            return self.trackers[self.parent_id]

    def is_in_progress(self):
        return self.state.is_in_progress

    def start(self):
        if not self.parent():
            self.state.start()
            return self

        if not self.parent().is_in_progress():
            raise Exception("You can't start a tracker if the parent isn't " +
                            'started')
        self.state.start(EstimatedSeconds=self.estimated_seconds)
        return self

    def with_status(self, msg):
        self.status_msg = msg
        return self

    def remaining_time_in_seconds(self):
        return self.state.remaining_time_in_seconds()

    def elapsed_time_in_seconds(self):
        return self.state.elapsed_time_in_seconds()


class ProgressTracker(TrackerBase):
    def __init__(self, **kwargs):
        self.start_time = kwargs.get('StartTime', arrow.utcnow().isoformat())
        self.done = False
        self.is_dirty = True
        super(ProgressTracker, self).__init__(**kwargs)

    def with_name(self, n):
        if not self.name == n:
            self.name = n
            self.dirty = True
        return self

    def with_message(self, m):
        if not self.message == m:
            self.message = m
            self.dirty = True
        return self

    def with_timestamp(self, m):
        if not m:
            m = arrow.utcnow().isoformat()
        self.dirty = True
        return self

    def succeed(self):
        self.status = 'Succeeded'
        self.done = True
        return self

    def cancel(self):
        self.status = 'Failed'
        self.done = True
        return self

    def fail(self):
        self.status = 'Failed'
        self.done = True
        return self

    def update(self):
        self.conn.hmset(self.get_full_key(), {
                        'name': self.name,
                        'status': self.status,
                        'message': self.message,
                        'current_progress': self.current_progress,
                        'total_progress': self.total_progress
                        })

    def to_json(self):
        return {'name': self.name}


class ProgressMagician(TrackerBase):
    def __init__(self, **kwargs):
        self.progress_manager = kwargs.get('ProgressManager')
        self.name = kwargs.get('Name')
        self.trackers = {}
        super(ProgressMagician, self).__init__(**kwargs)
        self.trackers[self.id] = self

    def load(self, key):
        all_items = self.progress_manager.get_all_by_key(key)
        self.progress_trackers = {}
        for i in all_items.keys():
            self.add_progress_tracker(i, all_items[i])

    def with_tracker(self, t):
        if not t.parent_id:
            t.parent_id = self.id
        t.trackers = self.trackers
        self.trackers[t.parent_id].children.append(t.id)
        self.trackers[t.id] = t
        return self

    def update(self):
        for k in self.progress_trackers.keys():
            pt = self.progress_trackers[k]
            if pt.is_dirty:
                self.progress_manager.update_tracker(pt)
                pt.is_dirty = False

    def summary(self):
        for k in self.progress_trackers.keys():
            pt = self.progress_trackers[k]

    def find_friendly_id(self, fk):
        for k in self.trackers.keys():
            if self.trackers[k].friendly_id == fk:
                return self.trackers[k]
        return None
