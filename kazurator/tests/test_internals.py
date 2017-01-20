from contextlib import contextmanager
from kazoo.exceptions import LockTimeout, NoNodeError
from kazurator.internals import Lock, LockDriver
from kazurator.utils import make_path
from unittest import TestCase
from . import kazoo_client


class TestLock(TestCase):
    def setUp(self):
        self.driver = LockDriver()
        self.path = "/haderp/some_lock_path"

    def tearDown(self):
        with kazoo_client() as client:
            client.delete(self.path, recursive=True)

    @contextmanager
    def internals(self, name, path=None, max_leases=100):
        path = path if path else self.path

        with kazoo_client() as client:
            internals = Lock(
                client,
                self.driver,
                path,
                name,
                max_leases
            )

            yield (client, internals)

    def test_initialization(self):
        with self.internals("__READ__") as (client, lock):
            assert lock.client is client
            assert lock.name == "__READ__"
            assert lock.max_leases == 100
            assert lock.path == make_path(self.path, "__READ__")

    def test_attempt_lock_returns_the_path_when_acquired(self):
        with self.internals("__READ__") as (_, lock):
            assert lock.attempt_lock()

    def test_attempt_lock_raises_lock_timeout_when_timeout_lapses(self):
        with self.internals("__READ__", max_leases=1) as (_, lock):
            assert lock.attempt_lock()

            with self.assertRaises(LockTimeout):
                lock.attempt_lock()

    def test_release_lock_deletes_the_znode(self):
        with self.internals("__READ__") as (client, lock):
            assert lock.attempt_lock()

            children = client.get_children(self.path)
            assert len(children) == 1

            lock.release_lock(make_path(self.path, children[0]))
            assert len(client.get_children(self.path)) == 0

    def test_clean_removes_the_lock_path(self):
        with self.internals("__READ__") as (client, lock):
            client.ensure_path(self.path)
            lock.clean()

            assert not client.exists(self.path)

    def test_clean_noops_when_node_doesnt_exist(self):
        with self.internals("__READ__") as (client, lock):
            lock.clean()
            assert True  # just making sure we get here

    def test_clean_noops_when_node_has_other_children(self):
        with self.internals("__READ__") as (client, lock):
            client.create(
                make_path(self.path, "ohai_there"),
                makepath=True
            )

            lock.clean()
            assert True  # just making sure we get here

    def test_get_sorted_children_returns_sorted_child_paths(self):
        with self.internals("__READ__") as (client, lock):
            lock.driver.create_lock(client, make_path(self.path, "__READ__"))
            lock.driver.create_lock(client, make_path(self.path, "__READ__"))

            children = lock.get_sorted_children()
            assert len(children) == 2
            assert children[0].endswith("__READ__0000000000")
            assert children[1].endswith("__READ__0000000001")

    def test_get_participant_nodes(self):
        with self.internals("__READ__") as (client, lock):
            lock.driver.create_lock(client, make_path(self.path, "__READ__"))
            lock.driver.create_lock(client, make_path(self.path, "__READ__"))

            nodes = lock.get_participant_nodes()
            assert len(nodes) == 2
            assert nodes[0].endswith("__READ__0000000000")
            assert nodes[1].endswith("__READ__0000000001")


class TestLockDriver(TestCase):
    def setUp(self):
        self.driver = LockDriver()

    def test_is_acquirable_returns_true_when_acquirable(self):
        children = ["000000", "000001"]
        path, acquirable = self.driver.is_acquirable(children, "000001", 10)

        assert not path
        assert acquirable

    def test_is_acquirable_returns_path_to_watch_for_when_not_acquirable(self):
        children = ["000000", "000001"]
        path, acquirable = self.driver.is_acquirable(children, "000001", 1)

        assert path == "000000"
        assert not acquirable

    def test_is_acquirable_raises_when_node_not_found(self):
        children = ["000000", "000001"]

        with self.assertRaises(NoNodeError):
            _, __ = self.driver.is_acquirable(children, "000002", 1)

    def test_create_lock_creates_an_ephemeral_sequential_znode(self):
        path = "/haderp/some_path"

        with kazoo_client() as client:
            lock_path = self.driver.create_lock(client, path + "/-lock-")
            assert len(client.get_children(path)) == 1
            assert lock_path.endswith("-lock-0000000000")

        # new client to ensure session was killed
        # Note: /haderp/some_path will still exist
        with kazoo_client() as client:
            assert len(client.get_children(path)) == 0

    def test_sort_key_strips_everything_upto_and_including_name(self):
        examples = [
            "/some/path/prefix/98798798-__WRIT__000001",
            "__WRIT__000001"
        ]

        for path in examples:
            assert self.driver.sort_key(path, "__WRIT__") == "000001"

    def test_sort_key_returns_original_string_when_name_not_found(self):
        assert self.driver.sort_key("/some/path", "__READ__") == "/some/path"
