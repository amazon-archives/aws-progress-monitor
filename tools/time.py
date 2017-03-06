def record_event(conn, event):
    id = conn.incr('event:id')
    event['id'] = id
    event_key = 'event:{id}'.format(id=id)

    pipe = conn.pipeline(True)
    pipe.hmset(event_key, event)
    pipe.zadd('events', **{id: event['timestamp']})
    pipe.execute()


