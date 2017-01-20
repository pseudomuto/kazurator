from sys import maxsize
from .mutex import InterProcessMutex
from .utils import lazyproperty

READ_LOCK_NAME = "__READ__"
WRITE_LOCK_NAME = "__WRIT__"


class InterProcessReadWriteLock:
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
        return InterProcessMutex(
            self._client,
            self.path,
            maxsize,
            name=READ_LOCK_NAME,
            timeout=self.timeout
        )

    @lazyproperty
    def write_lock(self):
        return InterProcessMutex(
            self._client,
            self.path,
            1,
            name=WRITE_LOCK_NAME,
            timeout=self.timeout
        )
