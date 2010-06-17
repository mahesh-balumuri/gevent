# Copyright (c) 2009-2010 Denis Bilenko. See LICENSE for details.

from gevent import core
from gevent.timeout import Timeout
from gevent.event import Event

__all__ = ['error', 'select']

__select__ = __import__('select')
error = __select__.error


def get_fileno(obj):
    try:
        fileno_f = obj.fileno
    except AttributeError:
        if not isinstance(obj, int):
            raise TypeError("Must be int or have fileno() method: %r" % (obj, ))
        return obj
    else:
        return fileno_f()


class SelectResult(object):

    def __init__(self):
        self.read = []
        self.write = []
        self.event = Event()

    def update(self, event, evtype):
        if evtype & core.EV_READ:
            self.read.append(event.arg)
            core.timer(0, self.event.set)
        elif evtype & core.EV_WRITE:
            self.write.append(event.arg)
            core.timer(0, self.event.set)
        # using core.timer(0, ...) to let other active events call update() before Event.wait() returns


def select(rlist, wlist, xlist, timeout=None):
    """An implementation of :meth:`select.select` that blocks only the current greenlet.

    Note: *xlist* is ignored.
    """
    allevents = []
    timeout = Timeout.start_new(timeout)
    result = SelectResult()
    try:
        try:
            for readfd in rlist:
                allevents.append(core.read_event(get_fileno(readfd), result.update, arg=readfd))
            for writefd in wlist:
                allevents.append(core.write_event(get_fileno(writefd), result.update, arg=writefd))
        except IOError, ex:
            raise error(*ex.args)
        result.event.wait(timeout=timeout)
        return result.read, result.write, []
    finally:
        for evt in allevents:
            evt.cancel()
        timeout.cancel()

