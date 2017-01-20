from kazoo.exceptions import LockTimeout, NoNodeError, NotEmptyError
from os.path import join
from .utils import mutex


def make_path(*paths):
    return join("/", *paths)


class LockInternals:
    _TIMEOUT_ERR = "Failed to acquire a lock on %s after %s seconds"

    def __init__(self, client, driver, path, name, max_leases):
        self._base_path = path
        self._client = client
        self._driver = driver
        self._lock = client.handler.lock_object()
        self._max_leases = max_leases
        self._name = name
        self._path = make_path(path, name)
        self._watch_handle = client.handler.event_object()

    @property
    def driver(self):
        return self._driver

    @property
    def name(self):
        return self._name

    @property
    def path(self):
        return self._path

    @property
    def max_leases(self):
        return self._max_leases

    def attempt_lock(self, timeout=0.2):
        path = None
        finished = False
        lock_acquired = False

        while not finished:
            finished = True

            try:
                path = self.driver.create_lock(self._client, self.path)
                lock_acquired = self._acquire(path, timeout)
            except NoNodeError:
                # TODO: need a retry here
                finished = False

        return path if lock_acquired else None

    def release_lock(self, lock_path):
        self._delete(lock_path)

    def clean(self):
        try:
            self._client.delete(self._base_path)
        except NoNodeError:
            pass
        except NotEmptyError:
            pass

    def get_sorted_children(self):
        def sortkey(path):
            return self._driver.sort_key(path, self.name)

        children = self._client.get_children(self._base_path)
        children.sort(key=sortkey)
        return children

    def _acquire(self, path, timeout):
        acquired = False
        delete = False

        try:
            while self._client.connected and not acquired:
                self._watch_handle.clear()

                children = self.get_sorted_children()
                name = path[len(self._base_path) + 1:]

                path_to_watch, acquirable = self._driver.is_acquirable(
                    children,
                    name,
                    self.max_leases
                )

                if acquirable:
                    acquired = True
                    break

                path_to_watch = make_path(self._base_path, path_to_watch)
                self._client.add_listener(self._watcher)

                with mutex(self._lock):
                    try:
                        if self._client.exists(path_to_watch, self._watcher):
                            self._watch_handle.wait(timeout)

                            if not self._watch_handle.isSet():
                                raise LockTimeout(
                                    self._TIMEOUT_ERR
                                    % (self._base_path, timeout)
                                )
                    except NoNodeError:
                        pass
                    finally:
                        self._client.remove_listener(self._watcher)
        except:
            delete = True
            raise
        finally:
            if delete:
                self._delete(path)

        return acquired

    def _delete(self, path):
        try:
            self._client.delete(path)
        except NoNodeError:
            pass

    def _watcher(self, state):
        self._watch_handle.set()
        return True


class LockInternalsDriver:
    def is_acquirable(self, children, sequence_node_name, max_leases):
        try:
            index = children.index(sequence_node_name)
            acquirable = index < max_leases
            watch_path = None if acquirable else children[index - max_leases]

            return (watch_path, acquirable)
        except ValueError:
            raise NoNodeError()

    def create_lock(self, client, path):
        return client.create(
            path,
            ephemeral=True,
            makepath=True,
            sequence=True
        )

    def sort_key(self, string, lock_name):
        if lock_name not in string:
            return string

        index = string.rfind(lock_name) + len(lock_name)
        return string[index:] if index < len(string) else ""