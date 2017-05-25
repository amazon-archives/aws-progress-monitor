import uuid
# from itertools import groupby


class Tracker(object):
    def __init__(self, **kwargs):
        self.key = str(uuid.uuid4())
        self.parent = kwargs.get('Parent')
        self.name = kwargs.get('Name')
        self.children = []


def add_tracker(t):
    if t.parent:
        trackers[t.parent].children.append(t.key)
    trackers[t.key] = t


trackers = {}
a = Tracker(Name='Master Workflow')
b = Tracker(Parent=a.key, Name='CopyData')
c = Tracker(Parent=a.key, Name='ConvertVM')
d = Tracker(Parent=b.key, Name='CreateFolder')
e = Tracker(Parent=b.key, Name='Copyfiles')

add_tracker(a)
add_tracker(b)
add_tracker(c)
add_tracker(d)
add_tracker(e)


def count_children(key):
    tot = 0
    t = trackers[key]
    if len(t.children):
        for k in t.children:
            tot = tot + count_children(k)
    tot = tot + len(t.children)
    print t.name, tot
    return tot

for k in trackers.keys():
    total = 0
    if not trackers[k].parent:
        count_children(trackers[k].key)


# groups = groupby(trackers, lambda a: (a.parent))
# for key, group in groups:
#    g = list(group)
#    print "{}: {}".format(key, len(g))
