import tornado.process
import tornado.ioloop
import tornado.gen
from pykern.pkdebug import pkdp
from pykern import pkcollections
import os

class B():
    c = None
    @classmethod
    def foo(cls):
        cls.c.bar()

    def bar(self):
        print(type(self))


class C(B):
    r = 'im in c'

b = B()
b.bar()
B.c = C()
B.foo()