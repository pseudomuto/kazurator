from kazoo.exceptions import LockTimeout
from kazurator import ReadWriteLock
from unittest import TestCase
from . import kazoo_client


class TestReadWriteLock(TestCase):
    def setUp(self):
        self.path = "/haderp/some_path"

    def tearDown(self):
        with kazoo_client() as client:
            client.delete(self.path, recursive=True)

    def _create_lock(self, client, timeout=0.5):
        return ReadWriteLock(client, self.path, timeout)

    def test_initialization(self):
        with kazoo_client() as client:
            lock = self._create_lock(client, timeout=20.0)
            assert lock.timeout == 20.0
            assert lock.read_lock.timeout == 20.0
            assert lock.write_lock.timeout == 20.0

    def test_setting_timeout_sets_value_on_locks(self):
        with kazoo_client() as client:
            lock = self._create_lock(client, timeout=20.0)
            assert lock.timeout == 20.0

            lock.timeout = 50.0
            assert lock.read_lock.timeout == 50.0
            assert lock.write_lock.timeout == 50.0

    def test_read_and_write_locks_are_memoized(self):
        with kazoo_client() as client:
            lock = self._create_lock(client)
            assert lock.read_lock is lock.read_lock
            assert lock.write_lock is lock.write_lock

    def test_read_lock_can_be_acquired(self):
        with kazoo_client() as client:
            lock = self._create_lock(client)

            with lock.read_lock:
                assert len(client.get_children(self.path)) == 1

            assert len(client.get_children(self.path)) == 0

    def test_read_locks_arent_limited_to_a_single_lock(self):
        with kazoo_client() as client:
            first_reader = self._create_lock(client)
            other_reader = self._create_lock(client)

            with first_reader.read_lock:
                with other_reader.read_lock:
                    assert len(client.get_children(self.path)) == 2

            assert len(client.get_children(self.path)) == 0

    def test_write_lock_can_be_acquired(self):
        with kazoo_client() as client:
            lock = self._create_lock(client)

            with lock.write_lock:
                assert len(client.get_children(self.path)) == 1

            assert len(client.get_children(self.path)) == 0

    def test_write_lock_is_exclusive(self):
        with kazoo_client() as client:
            first_writer = self._create_lock(client)
            other_writer = self._create_lock(client)

            with first_writer.write_lock:
                with self.assertRaises(LockTimeout):
                    other_writer.write_lock.acquire()  # should timeout

    def test_read_lock_blocks_when_write_lock_held(self):
        with kazoo_client() as client:
            reader = self._create_lock(client)
            writer = self._create_lock(client)

            with writer.write_lock:
                with self.assertRaises(LockTimeout):
                    reader.read_lock.acquire()  # should timeout

    def test_write_lock_blocks_when_read_lock_held(self):
        with kazoo_client() as client:
            reader = self._create_lock(client)
            writer = self._create_lock(client)

            with reader.read_lock:
                with self.assertRaises(LockTimeout):
                    writer.write_lock.acquire()  # should timeout

    def test_get_participant_nodes_includes_read_locks(self):
        with kazoo_client() as client:
            reader_one = self._create_lock(client)
            reader_two = self._create_lock(client)

            with reader_one.read_lock:
                with reader_two.read_lock:
                    nodes = reader_one.get_participant_nodes()
                    assert len(nodes) == 2

                    assert nodes[0].startswith(self.path)
                    assert nodes[0].endswith("__READ__0000000000")

                    assert nodes[1].startswith(self.path)
                    assert nodes[1].endswith("__READ__0000000001")

    def test_get_participant_nodes_includes_write_lock(self):
        with kazoo_client() as client:
            writer = self._create_lock(client)

            with writer.write_lock:
                    nodes = writer.get_participant_nodes()
                    assert len(nodes) == 1

                    assert nodes[0].startswith(self.path)
                    assert nodes[0].endswith("__WRIT__0000000000")
