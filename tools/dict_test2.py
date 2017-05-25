
class Test(object):
    def __init__(self, name):
        self.list = []
        self.name = name

    def with_item(self, i):
        i.parent = self
        self.list.append(i)
        return self


a = Test('a')
b = Test('b')
c = Test('c')
b.with_item(c)
a.with_item(b)
for i in b.list:
    print i.parent.parent.name
