d = {}
d['test1'] = '1'
d['test2'] = '2'


class test(object):
    def __init__(self, d):
        self.d = d


a = test(d)
b = test(d)

print a.d
print b.d

a.d['test3'] = 3
print b.d
