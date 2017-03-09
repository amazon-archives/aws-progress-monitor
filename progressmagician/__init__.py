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
            pipe.sadd(self.children_key(e.id), *set(e.children))
        print '---\nsetting {}: {}\n---'.format(e.get_full_key(), data)
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
            t.trackers = self.trackers
            c = self.get_children(id)
            if c:
                t.children = c
            t.db_conn = self
            self.trackers[id] = t

            if len(t.children) > 0:
                for c in t.children:
                    self.get_all_by_id(c)

    def inc_progress(self, e, value=1):
        self.redis.hincrby(e.get_full_key(), "curr_prog", value)


class TrackerBase(object):
    def __init__(self, **kwargs):
        self.friendly_id = kwargs.get('FriendlyId', None)
        self.id = kwargs.get('Id', str(uuid.uuid4()))
        self.name = kwargs.get('Name')
        self.children = []
        self.state = TrackerState()
        self.estimated_seconds = kwargs.get('EstimatedSeconds', None)
        self.parent_id = kwargs.get('ParentId', None)
        self.is_dirty = True
        self.status_msg = None
        self.last_update = arrow.utcnow()
        self.source = kwargs.get('Source', None)
        self.is_in_progress = False
        self.done = False
        self.status = 'Not started'
        self.metric = None
        self.metric_name = None
        self.metric_namespace = None
        self.finish_time = None
        self.autosave = True
        self.db_conn = kwargs.get('DbConnection')

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
        print t.name, tot
        return tot

    def get_children_by_status(self, status, id=None):
        c = []
        t = self.main.trackers[id]
        if t.status == status:
            print 'here', t.friendly_id
            c.append(t)
        if len(t.children):
            for k in t.children:
                c.append(self.get_children_by_status(status, k))
        return c

    def parent(self):
        if self.parent_id in self.trackers.keys():
            return self.trackers[self.parent_id]

    def start(self, **kwargs):
        print '{} is starting: now is {}'.format(self.id, self.is_in_progress)
        if self.is_in_progress:
            logging.warning('{} is already started. Ignoring start()'
                            .format(self.id))
            return self
        if self.done:
            logging.warning('{} is done. Ignoring start()')
            return self
        m = kwargs.get('Message', None)
        if m:
            self.with_status_msg(m)
        self.start_time = kwargs.get('StartTime', arrow.utcnow())
        if bool(kwargs.get('Parents', False)):
            if self.parent():
                self.parent().start(Parents=True)
        if self.parent() and not self.parent().is_in_progress:
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

    def remaining_time_in_seconds(self):
        return self.state.remaining_time_in_seconds()

    def elapsed_time_in_seconds(self):
        return self.state.elapsed_time_in_seconds()

    def update(self):
        if self.parent_id:
            p = self.trackers[self.parent_id]
            p.update()

        if self.is_dirty:
            try:
                self.db_conn.update_tracker(self)
            except Exception as e:
                logging.error('Error persisting to DB: {}'.format(str(e)))
                raise
            self.is_dirty = False
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
        j['d'] = self.done
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
            t.done = str(j['d']) == 'True'
        if 'm_ns' in j.keys() and 'm' in j.keys():
            ns = j['m_ns']
            m = j['m']
            t.with_metric(Namespace=ns, Metric=m, Clean=True)
        t.is_dirty = False
        return t

    def with_child(self, c):
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

    @property
    def not_started(self):
        return self.get_children_by_status('Not started', self.id)

    @property
    def in_progress(self):
        return self.get_children_by_status('In Progress', self.id)

class ProgressTracker(TrackerBase):
    def __init__(self, **kwargs):
        self.start_time = kwargs.get('StartTime', arrow.utcnow().isoformat())
        self.done = False
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

    def has_metric(self):
        return self.metric and self.metric_name

    def log_done(self):
        if not self.has_metric:
            logging.debug('No metric defined for {}'.format(self.id))
            return self
        try:
            self.metric.seconds(MetricName=self.metric_name,
                                Value=self.elapsed_time_in_seconds())
            self.metric.count(MetricName="{}/{}"
                              .format(self.metric_name, self.status))
        except Exception as e:
            logging.warn('Error logging done metric: {}\n{}:{}'
                         .format(str(e), self.metric_name,
                                 self.elapsed_time_in_seconds()))
        return self

    def mark_done(self, status, m=None):
        if self.done:
            logging.warning('Already done: {}'.self.id)
            return self
        if m:
            self.with_status_msg(m)
        self.with_finish_time(arrow.utcnow())
        self.done = True
        self.is_in_progress = False
        self.status = status
        self.is_dirty = True
        self.log_done()
        return self

    def succeed(self, **kwargs):
        if self.status == 'Succeeeded' and self.done and \
                          not self.is_in_progress:
            logging.warning('Already succeeded {}'.self.id)
            return self
        m = kwargs.get('Message', None)
        self.mark_done('Succeeded', m)
        return self

    def cancel(self, **kwargs):
        if self.status == 'Canceled' and self.done and not self.is_in_progress:
            logging.warning('Already canceled: {}'.self.id)
            return self
        m = kwargs.get('Message', None)
        self.mark_done('Canceled', m)
        return self

    def fail(self, **kwargs):
        if self.status == 'Failed' and self.done and not self.is_in_progress:
            logging.warning('Already failed: {}'.self.id)
            return self
        m = kwargs.get('Message', None)
        self.mark_done('Failed', m)
        return self


class ProgressMagician(TrackerBase):
    def __init__(self, **kwargs):
        self.name = kwargs.get('Name')
        self.trackers = {}
        super(ProgressMagician, self).__init__(**kwargs)
        self.trackers[self.id] = self
        self.main = self.trackers[self.id]
        self.db_conn.trackers = self.trackers

    def load(self, id):
        self.id = id
        self.db_conn.get_all_by_id(id)
        self.main = self.trackers[id]

    def with_tracker(self, t):
        t.db_conn = self.db_conn
        if not t.parent_id:
            t.parent_id = self.id
        t.trackers = self.trackers
        t.main = self
        p = self.trackers[t.parent_id]
        if t.id not in p.children:
            p.with_child(t.id)
        self.trackers[t.id] = t
        return self

    def find_friendly_id(self, fk):
        for k in self.trackers.keys():
            if self.trackers[k].friendly_id == fk:
                return self.trackers[k]
        return None

    def find_id(self, id):
        if id in self.trackers.keys():
            return self.trackers[id]
        return None

    def update_all(self):
        for i in self.trackers.keys():
            t = self.trackers[i]
            if self.trackers[i].is_dirty:
                t.update()
        if self.is_dirty:
            self.update()
        return self
