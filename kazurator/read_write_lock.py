from kazoo.exceptions import NoNodeError
from sys import maxsize
from .mutex import Mutex
from .internals import LockDriver
from .utils import lazyproperty

READ_LOCK_NAME = "__READ__"
WRITE_LOCK_NAME = "__WRIT__"


class _LockDriver(LockDriver):
    def sort_key(self, string, _lock_name):
        string = super(_LockDriver, self).sort_key(string, READ_LOCK_NAME)
        string = super(_LockDriver, self).sort_key(string, WRITE_LOCK_NAME)
        return string


class _ReadLockDriver(_LockDriver):
    def __init__(self, predicate):
        super(_ReadLockDriver, self).__init__()
        self._predicate = predicate

    def is_acquirable(self, children, sequence_node_name, max_leases):
        return self._predicate(children, sequence_node_name)


class _Mutex(Mutex):
    def __init__(self, client, path, name, max_leases, driver, timeout):
        super(_Mutex, self).__init__(
            client,
            path,
            max_leases,
            name=name,
            driver=driver
        )

    def get_participant_nodes(self):
        nodes = super(_Mutex, self).get_participant_nodes()
        return list(filter(lambda node: self.name in node, nodes))


class ReadWriteLock(object):
    def __init__(self, client, path, timeout=None):
        self._client = client
        self._path = path
        self._timeout = timeout

    @property
    def path(self):
        return self._path

    @property
    def timeout(self):
        return self._timeout

    @lazyproperty
    def read_lock(self):
        def predicate(children, sequence_node_name):
            return self._read_is_acquirable_predicate(
                children,
                sequence_node_name
            )

        return _Mutex(
            self._client,
            self.path,
            READ_LOCK_NAME,
            maxsize,
            _ReadLockDriver(predicate),
            self.timeout
        )

    @lazyproperty
    def write_lock(self):
        return _Mutex(
            self._client,
            self.path,
            WRITE_LOCK_NAME,
            1,
            _LockDriver(),
            self.timeout
        )

    def _read_is_acquirable_predicate(self, children, sequence_node_name):
        if self.write_lock.is_owned_by_current_thread:
            return (None, True)

        index = 0
        write_index = maxsize
        our_index = -1

        for node in children:
            if WRITE_LOCK_NAME in node:
                write_index = min(index, write_index)
            elif node.startswith(sequence_node_name):
                our_index = index
                break

            index += 1

        if our_index < 0:
            raise NoNodeError

        acquirable = our_index < write_index
        path = None if acquirable else children[write_index]
        return (path, acquirable)
