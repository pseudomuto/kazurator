from threading import current_thread, Lock as ThreadLock, ThreadError
from .internals import Lock, LockDriver
from .utils import mutex

DEFAULT_LOCK_NAME = "lock-"
DEFAULT_TIMEOUT = 1.0


class _LockData(object):
    def __init__(self, path):
        self._count = 1
        self._lock = ThreadLock()
        self._path = path

    @property
    def path(self):
        return self._path

    @property
    def count(self):
        with mutex(self._lock):
            return self._count

    def increment(self):
        with mutex(self._lock):
            self._count += 1
            return self._count

    def decrement(self):
        with mutex(self._lock):
            self._count -= 1
            return self._count


class Mutex(object):
    def __init__(self, client, path, max_leases=1, **kwargs):
        self._path = path
        self._sync_lock = client.handler.lock_object()
        self._thread_data = {}
        self._timeout = kwargs.get("timeout", DEFAULT_TIMEOUT)

        self._lock = Lock(
            client,
            kwargs.get("driver", LockDriver()),
            path,
            kwargs.get("name", DEFAULT_LOCK_NAME),
            max_leases
        )

    def __enter__(self):
        self.acquire()

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()

    @property
    def name(self):
        return self._lock.name

    @property
    def path(self):
        return self._path

    @property
    def is_acquired(self):
        return len(self._thread_data) > 0

    @property
    def is_owned_by_current_thread(self):
        with mutex(self._sync_lock):
            data = self._thread_data.get(current_thread())
            return data and data.count > 0

    def get_participant_nodes(self):
        return self._lock.get_participant_nodes()

    def acquire(self):
        thread = current_thread()

        with mutex(self._sync_lock):
            data = self._thread_data.get(thread)

            if data:
                # re-entering
                data.increment()
                return True

            path = self._lock.attempt_lock(self._timeout)
            if not path:
                return False

            self._thread_data[thread] = _LockData(path)
            return True

    def release(self):
        thread = current_thread()

        with mutex(self._sync_lock):
            data = self._thread_data.get(thread)
            path = self._path

            if not data:
                raise ThreadError("You do not own the lock: " + path)

            count = data.decrement()

            # I'm not 100% sure this can happen...so this might be a little
            # over-defensive
            if count < 0:
                raise ThreadError("Lock count has gone negative: " + path)

            if count == 0:
                try:
                    self._lock.release_lock(data.path)
                finally:
                    del self._thread_data[thread]
