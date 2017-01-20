from kazoo.client import KazooClient
from kazoo.exceptions import LockTimeout
from kazurator import InterProcessReadWriteLock
from unittest import TestCase


class TestReadWriteLock(TestCase):
    def setUp(self):
        self.client = KazooClient(hosts="127.0.0.1:2181")
        self.client.start()

        self.path = "/haderp/some_path"

    def tearDown(self):
        self.client.delete(self.path, recursive=True)
        self.client.stop()

    def create_lock(self, timeout=0.5):
        return InterProcessReadWriteLock(self.client, self.path, timeout)

    def test_read_and_write_locks_are_memoized(self):
        lock = self.create_lock()
        assert lock.read_lock is lock.read_lock
        assert lock.write_lock is lock.write_lock
