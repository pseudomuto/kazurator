import uuid
from kazoo.exceptions import LockTimeout, NoNodeError, NotEmptyError
from .utils import make_path, mutex


# SHAMELESS THEFT FROM CURATOR:
#  It turns out there is an edge case that exists when creating
#  sequential-ephemeral nodes. The creation can succeed on the server, but the
#  server can crash before the created node name is returned to the client.
#  However, the ZK session is still valid so the ephemeral node is not deleted.
#  Thus, there is no way for the client to determine what node was created for
#  them.
#
#  See Curator's CreateBuilder#withProtection for more info
def _protect(path):
    parts = path.split("/")
    parts[-1] = "_c_{}-{}".format(uuid.uuid4(), parts[-1])
    return "/".join(parts)


class Lock(object):
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
    def client(self):
        return self._client

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

    def get_participant_nodes(self):
        children = self.get_sorted_children()
        nodes = map(lambda child: make_path(self._base_path, child), children)
        return list(nodes)

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


class LockDriver(object):
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
            _protect(path),
            ephemeral=True,
            makepath=True,
            sequence=True
        )

    def sort_key(self, string, lock_name):
        if lock_name not in string:
            return string

        index = string.rfind(lock_name) + len(lock_name)
        return string[index:] if index < len(string) else ""
