class Chain2(object):

    def __init__(self, path=''):
        self.path = path

    def __getattr__(self, attr):
        return Chain2('%s/%s' %(self.path, attr))

    def __str__(self):
        return self.path


    def __call__(self, param):
        return Chain2('%s/%s' %(self.path, str(param)))

    __repr__ = __str__


print(Chain2().users('michael').age(23).repos)
print(Chain2().users('michael').age(23).sex('female').repos)