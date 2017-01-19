import uuid
from kazoo.exceptions import LockTimeout, NoNodeError
from kazoo.retry import KazooRetry, RetryFailedError
from .utils import retryable

DEFAULT_LOCK_NAME = "lock-"
DEFAULT_TIMEOUT = 2.0


class InterProcessMutex:
    def __init__(self, client, path, max_leases, **kwargs):
        self._name = kwargs.get("name", DEFAULT_LOCK_NAME)
        self._timeout = kwargs.get("timeout", DEFAULT_TIMEOUT)

        self._attempted = False
        self._client = client
        self._create_path = path + "/" + uuid.uuid4().hex + "-" + self._name
        self._event = client.handler.event_object()
        self._lock = client.handler.lock_object()
        self._max_leases = max_leases
        self._nodes = []
        self._path = path

        self._retry = KazooRetry(
            max_tries=kwargs.get("max_tries", None),
            sleep_func=client.handler.sleep_func
        )

    def __enter__(self):
        self.acquire()

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()

    @property
    def name(self):
        return self._name

    @property
    def path(self):
        return self._path

    @property
    def is_acquired(self):
        return len(self._nodes) > 0

    @property
    def _current_node(self):
        if len(self._nodes) == 0:
            return None

        return self._nodes[-1]

    @property
    def _mutex(self):
        return retryable(self._lock, self._retry, self._timeout)

    def acquire(self):
        with self._mutex as locked:
            if not locked:
                return False

            acquired = False
            retry = self._retry.copy()

            try:
                acquired = retry(self._acquire_znode)
                self._attempted = False
            except RetryFailedError:
                pass

            return acquired

    def release(self):
        with self._mutex as locked:
            if not locked:
                return False

            return self._retry(self._release_znode)

    def _ensure_path(self):
        if hasattr(self, '__ensure_path'):
            return

        self._client.ensure_path(self.path)
        self.__ensure_path = True

    def _acquire_znode(self):
        self._ensure_path()

        node = self._current_node if self._attempted else None

        if not node:
            self._attempted = True

            node = self._client.create(
                self._create_path,
                ephemeral=True,
                sequence=True
            )

            # strip path from the node
            self._nodes.append(node[len(self.path) + 1:])

        while True:
            children = self._get_sorted_children()
            if len(children) <= self._max_leases:
                return True

            self._client.add_listener(self._wait)
            try:
                self._event.wait(self._timeout)

                if not self._event.isSet():
                    raise LockTimeout(
                        "Failed to acquire lock on %s after %s seconds"
                        % (self.path, self._timeout)
                    )
            finally:
                self._client.remove_listener(self._wait)

    def _wait(self, _state):
        self._event.set()
        return True

    def _release_znode(self):
        if not self.is_acquired:
            return False

        try:
            self._client.delete(self.path + "/" + self._nodes.pop())
        except NoNodeError:
            pass

        return True

    def _get_sorted_children(self):
        def sort_key(node):
            return node[node.find(self.name) + len(self.name):]

        children = self._client.get_children(self.path)
        children.sort(key=sort_key)
        return children
