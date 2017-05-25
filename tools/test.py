import redis

pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
r = redis.Redis(connection_pool=pool)


class RollupEvent(object):
    def __init__(self, **kwargs):
        self.conn = kwargs.get('RedisConnection')
        self.key = kwargs.get('Key')
        self.rollup_events = []
        self.type = kwargs.get('Type')
        self.value = kwargs.get('Value')

    def with_event(self, r):
        self.rollup_events.append(r)


def record_event(conn, event):
    pipe = conn.pipeline(True)
    pipe.hmset('abc', {'val': 'testabc'})
    pipe.hmset('abc:def', {'val': 'testdef'})
    pipe.hmset('abc:def:ghi', {'val': 'testghi'})
    pipe.hmset('123', {'val': 'test123'})
    pipe.hmset('123:456', {'val': 'test456'})
    pipe.execute()


event = {}
event['status'] = 'In progress'

# record_event(r, event)
for i in r.scan_iter('abc*'):
    v = r.hgetall(i)
    print v
