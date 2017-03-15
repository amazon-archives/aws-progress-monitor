from __future__ import division
import uuid
import arrow
import logging
import json
from fluentmetrics.metric import FluentMetric


class TrackerStats(object):
    def __init__(self, **kwargs):
        self.id = kwargs.get('Id')
        self.trackers = kwargs.get('Trackers')


class TrackerState(object):
    def __init__(self):
        self.totals = {}
        self.is_done = False
        self.is_failed = False
        self.is_errored = False
        self.is_cancelled = False
        self.is_partially_failed = False
        self.percent_done = 0
        self.start_time = None
        self.finish_time = None

    def start(self, **kwargs):
        self.is_in_progress = True
        self.start_time = kwargs.get('StartTime')
        secs = kwargs.get("EstimatedSeconds", None)
        if secs:
            self.estimated_seconds = int(secs)
        else:
            self.estimated_seconds = None

    def elapsed_time_in_seconds(self):
        if not self.start_time:
            return 0
        if self.finish_time:
            delta = self.finish_time - self.start_time
        else:
            delta = arrow.utcnow() - self.start_time

        return delta.total_seconds()

    def remaining_time_in_seconds(self):
        if self.estimated_seconds:
            if self.estimated_seconds > self.elapsed_time_in_seconds:
                return self.estimated_seconds - self.elapsed_time_in_seconds
        return None


class RedisProgressManager(object):
    def __init__(self, **kwargs):
        self.redis = kwargs.get('RedisConnection')
        self.trackers = kwargs.get('Trackers')

    def children_key(self, k):
        return "{}:ch".format(k)

    def update_tracker(self, e):
        pipe = self.redis.pipeline(True)
        data = e.to_json()
        pipe.hmset(e.get_full_key(), data)
        if e.children:
            children = []
            for c in e.children:
                children.append(c.id)
            pipe.sadd(self.children_key(e.id), *set(children))
        if e.friendly_id:
            pipe.set(e.friendly_id, e.id)
        pipe.execute()

    def get_by_friendly_id(self, friendly_id):
        if (self.redis.exists(friendly_id)):
            id = self.redis.get(friendly_id)
            if id:
                return self.get_all_by_id(id)

    def get_by_id(self, id):
        logging.info('Reading {} from Redis DB'.format(id))
        return self.redis.hgetall(id)

    def get_children(self, id):
        k = self.children_key(id)
        if self.redis.exists(k):
            return self.redis.smembers(self.children_key(id))

    def get_all_by_id(self, id):
        j = self.get_by_id(id)
        if j:
            t = TrackerBase.from_json(id, j)
            t.db_conn = self
            children = self.get_children(id)
            if children:
                for c in children:
                    t.with_tracker(self.get_all_by_id(c))
        return t

    def inc_progress(self, e, value=1):
        self.redis.hincrby(e.get_full_key(), "curr_prog", value)


class TrackerBase(object):
    def __init__(self, **kwargs):
        self.friendly_id = kwargs.get('FriendlyId', None)
        self.id = kwargs.get('Id', str(uuid.uuid4()))
        self.name = kwargs.get('Name')
        self.children = []
        self.state = TrackerState()
        self.estimated_seconds = kwargs.get('EstimatedSeconds', 0)
        self.parent_id = kwargs.get('ParentId', None)
        self.status_msg = None
        self.last_update = arrow.utcnow()
        self.source = kwargs.get('Source', None)
        self.is_in_progress = False
        self.is_done = False
        self.status = 'Not started'
        self.metric = None
        self.metric_name = None
        self.metric_namespace = None
        self.finish_time = None
        self.db_conn = kwargs.get('DbConnection')
        self.parent = None
        self.is_dirty = True
        self.has_parallel_children = kwargs.get('HasParallelChildren', False)

    def __str__(self):
        return self.name

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
        if not self.parent_id:
            return self.id
        else:
            return "{}".format(self.id)

    def inc_progress(self, val=1):
        self.db_conn.inc_progress(val)

    @property
    def stats(self):
        s = TrackerStats(Id=self.id, Trackers=self.trackers)
        return s

    def get_stats(self, **kwargs):
        id = kwargs.get('Id', None)
        tot = 0
        if id:
            t = self.trackers[id]
        else:
            t = self.trackers[self.id]
        if len(t.children):
            for k in t.children:
                tot = tot + self.get_stats(k)
        tot = tot + len(t.children)
        return tot

    @property
    def total_estimate(self):
        if self.has_parallel_children:
            longest = 0

        if len(self.children):
            secs = 0
            for k in self.children:
                tot = k.total_estimate
                if self.has_parallel_children and tot > longest:
                    longest = tot
                else:
                    secs = secs + tot
        else:
            return self.estimated_seconds

        if self.has_parallel_children:
            return longest
        else:
            return secs

    def get_children_by_status(self, status):
        items = []
        if len(self.children):
            for k in self.children:
                if len(status) == 0 or k.status in status:
                    items.append(k)
                match = k.get_children_by_status(status)
                if len(match) > 0:
                    items.extend(match)
        return items

    def start(self, **kwargs):
        if self.is_in_progress:
            logging.warning('{} is already started. Ignoring start()'
                            .format(self.id))
            return self
        if self.is_done:
            logging.warning('{} is done. Ignoring start()')
            return self
        m = kwargs.get('Message', None)
        if m:
            self.with_status_msg(m)
        self.start_time = kwargs.get('StartTime', arrow.utcnow())
        if bool(kwargs.get('Parents', False)):
            if self.parent:
                self.parent.start(Parents=True)
        if self.parent and not self.parent.is_in_progress:
            raise Exception("You can't start a tracker if the parent isn't " +
                            'started')
        self.state.start(StartTime=self.start_time,
                         EstimatedSeconds=self.estimated_seconds)
        self.status = 'In Progress'
        self.is_in_progress = True
        self.is_dirty = True
        return self

    def with_status_msg(self, s, clean=False):
        if not self.status_msg == s:
            self.status_msg = s
            if not clean:
                self.dirty = True
        return self

    @property
    def remaining_time_in_seconds(self):
        return self.total_estimate - self.elapsed_time_in_seconds

    @property
    def elapsed_time_in_seconds(self):
        return self.state.elapsed_time_in_seconds()

    def update(self, recursive=True):
        p = self.parent
        if p:
            p.update(False)

        if self.is_dirty:
            try:
                self.db_conn.update_tracker(self)
            except Exception as e:
                logging.error('Error persisting to DB: {}'.format(str(e)))
                raise
            self.is_dirty = False

        if recursive:
            for c in self.children:
                c.update()
        return self

    def to_json(self):
        j = {}
        j['name'] = self.name
        if self.estimated_seconds:
            j['est_sec'] = self.estimated_seconds
        if self.state.start_time:
            j['start'] = self.state.start_time.isoformat()
        if self.state.finish_time:
            j['finish'] = self.state.finish_time.isoformat()
        if self.status_msg:
            j['st_msg'] = self.status_msg
        if self.parent_id:
            j['pid'] = self.parent_id
        if self.friendly_id:
            j['fid'] = self.friendly_id
        if self.last_update:
            j['l_u'] = self.last_update.isoformat()
        if self.source:
            j['s'] = self.source
        if self.metric_namespace:
            j['m_ns'] = self.metric_namespace
        if self.metric:
            j['m'] = self.metric_name
        j['in_p'] = self.is_in_progress
        j['has_p'] = self.has_parallel_children
        j['d'] = self.is_done
        if self.status:
            j['st'] = self.status
        return json.loads(json.dumps(j))

    @staticmethod
    def from_json(id, j):
        t = ProgressTracker(Id=id)
        if 'name' in j.keys():
            t.with_name(j['name'], True)
        if 'est_sec' in j.keys():
            t.with_estimated_seconds(j['est_sec'], True)
        if 'start' in j.keys():
            t.with_start_time(arrow.get(j['start']), True)
        if 'finish' in j.keys():
            t.with_finish_time(arrow.get(j['finish']), True)
        if 'st_msg' in j.keys():
            t.with_status_msg(arrow.get(j['st_msg']), True)
        if 'fid' in j.keys():
            t.with_friendly_id(j['fid'], True)
        if 'pid' in j.keys():
            t.parent_id = j['pid']
        if 'in_p' in j.keys():
            t.is_in_progress = str(j['in_p']) == 'True'
        if 'st' in j.keys():
            t.status = j['st']
        if 's' in j.keys():
            t.with_source(j['s'], True)
        if 'd' in j.keys():
            t.is_done = str(j['d']) == 'True'
        if 'has_p' in j.keys():
            t.has_parallel_children = str(j['has_p']) == 'True'
        if 'm_ns' in j.keys() and 'm' in j.keys():
            ns = j['m_ns']
            m = j['m']
            t.with_metric(Namespace=ns, Metric=m, Clean=True)
        t.is_dirty = False
        return t

    def with_tracker(self, t):
        t.db_conn = self.db_conn
        t.parent = self
        self.children.append(t)
        return self

    def with_child(self, c):
        c.parent = self
        if self.children and c in self.children:
            return self
        self.is_dirty = True
        self.children.append(c)
        return self

    def with_estimated_seconds(self, e, clean=False):
        if not self.estimated_seconds == e:
            self.estimated_seconds = e
            if not clean:
                self.dirty = True
        return self

    def with_start_time(self, s, clean=False):
        if not self.start_time == s:
            self.start_time = s
            self.state.start_time = s
            if not clean:
                self.dirty = True
        return self

    def with_finish_time(self, f, clean=False):
        if not self.finish_time == f:
            self.finish_time = f
            self.state.finish_time = f
            if not clean:
                self.dirty = True
        return self

    def with_last_update(self, d):
        self.is_dirty = not self.last_update == d
        self.last_update = d
        return self

    def with_autosave(self):
        if self.autosave:
            return self
        self.is_dirty = True
        self.autosave = True

    def with_source(self, s, clean=False):
        if not self.source == s:
            self.source = s
            if not clean:
                self.dirty = True
        return self

    def with_friendly_id(self, f, clean=False):
        if not self.friendly_id == f:
            self.friendly_id = f
            if not clean:
                self.dirty = True
        return self

    def with_metric(self, **kwargs):
        ns = kwargs.get('Namespace')
        m = kwargs.get('Metric')
        clean = kwargs.get('Clean', False)
        if self.metric_namespace == ns and self.metric_name == m:
            return self
        self.metric_name = m
        self.metric_namespace = ns
        self.metric = FluentMetric().with_namespace(self.metric_namespace)
        if not clean:
            self.dirty = True
        return self

    def get_pct(self, m):
        t = self.all_children_count
        if m == 0 or t == 0:
            return 0
        else:
            return float("{0:.2f}".format(m/t))

    @property
    def not_started_pct(self):
        return self.get_pct(self.not_started_count)

    @property
    def in_progress_pct(self):
        return self.get_pct(self.in_progress_count)

    @property
    def canceled_pct(self):
        return self.get_pct(self.canceled_count)

    @property
    def succeeded_pct(self):
        return self.get_pct(self.succeeded_count)

    @property
    def failed_pct(self):
        return self.get_pct(self.failed_count)

    @property
    def done_pct(self):
        return self.get_pct(self.done_count)

    @property
    def paused_pct(self):
        return self.get_pct(self.paused_count)

    @property
    def not_started_count(self):
        return len(self.not_started)

    @property
    def in_progress_count(self):
        return len(self.in_progress)

    @property
    def canceled_count(self):
        return len(self.canceled)

    @property
    def succeeded_count(self):
        return len(self.succeeded)

    @property
    def failed_count(self):
        return len(self.failed)

    @property
    def done_count(self):
        return len(self.done)

    @property
    def paused_count(self):
        return len(self.paused)

    @property
    def not_started(self):
        return self.get_children_by_status(['Not started'])

    @property
    def in_progress(self):
        return self.get_children_by_status(['In Progress'])

    @property
    def canceled(self):
        return self.get_children_by_status(['Canceled'])

    @property
    def succeeded(self):
        return self.get_children_by_status(['Succeeded'])

    @property
    def failed(self):
        return self.get_children_by_status(['Failed'])

    @property
    def done(self):
        return self.get_children_by_status(['Succeeded', 'Canceled', 'Failed'])

    @property
    def not_done(self):
        return self.get_children_by_status(['In Progress', 'Paused'])

    @property
    def paused(self):
        return self.get_children_by_status(['Paused'])

    @property
    def all_children(self):
        return self.get_children_by_status([])

    @property
    def all_children_count(self):
        return len(self.all_children)

    def find_id(self, f):
        found = None
        for c in self.children:
            if c.id == f:
                found = c
            else:
                found = c.find_id(f)
            if found:
                break

        return found

    def find_friendly_id(self, f):
        found = None
        for c in self.children:
            if c.friendly_id == f:
                found = c
            else:
                found = c.find_friendly_id(f)
            if found:
                break

        return found

    def log_done(self):
        if not self.has_metric:
            logging.debug('No metric defined for {}'.format(self.id))
            return self
        try:
            self.metric.seconds(MetricName=self.metric_name,
                                Value=self.elapsed_time_in_seconds)
            self.metric.count(MetricName="{}/{}"
                              .format(self.metric_name, self.status))
        except Exception as e:
            logging.warn('Error logging done metric: {}\n{}:{}'
                         .format(str(e), self.metric_name,
                                 self.elapsed_time_in_seconds))
        return self

    def mark_done(self, status, m=None):
        if self.is_done:
            logging.warning('Already done: {}'.self.id)
            return self
        if m:
            self.with_status_msg(m)
        self.with_finish_time(arrow.utcnow())
        self.is_done = True
        self.is_in_progress = False
        self.status = status
        self.is_dirty = True
        self.log_done()
        return self

    def succeed(self, **kwargs):
        if self.status == 'Succeeeded' and self.is_done and \
                          not self.is_in_progress:
            logging.warning('Already succeeded {}'.self.id)
            return self
        m = kwargs.get('Message', None)
        self.mark_done('Succeeded', m)
        return self

    def cancel(self, **kwargs):
        if self.status == 'Canceled' and self.is_done and \
                not self.is_in_progress:
            logging.warning('Already canceled: {}'.self.id)
            return self
        m = kwargs.get('Message', None)
        self.mark_done('Canceled', m)
        return self

    def fail(self, **kwargs):
        if self.status == 'Failed' and self.is_done and \
                not self.is_in_progress:
            logging.warning('Already failed: {}'.self.id)
            return self
        m = kwargs.get('Message', None)
        self.mark_done('Failed', m)
        return self


class ProgressTracker(TrackerBase):
    def __init__(self, **kwargs):
        self.start_time = kwargs.get('StartTime', arrow.utcnow().isoformat())
        self.is_done = False
        super(ProgressTracker, self).__init__(**kwargs)

    def with_name(self, n, clean=False):
        if not self.name == n:
            self.name = n
            if not clean:
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

    @property
    def has_metric(self):
        return self.metric and self.metric_name


class ProgressInsight(ProgressTracker):
    def __init__(self, **kwargs):
        self.name = kwargs.get('Name')
        self.trackers = {}
        super(ProgressInsight, self).__init__(**kwargs)
        self.trackers[self.id] = self
        self.main = self.trackers[self.id]
        self.db_conn.trackers = self.trackers

    def load(self, id):
        self.id = id
        return self.db_conn.get_all_by_id(id)

    def update_all(self):
        self.update(True)
        return self
