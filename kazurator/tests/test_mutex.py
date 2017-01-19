from kazoo.client import KazooClient
from kazoo.exceptions import LockTimeout
from kazurator import InterProcessMutex
from sys import maxsize
from unittest import TestCase


class TestInterProcessMutex(TestCase):
    def setUp(self):
        self.client = KazooClient(hosts="127.0.0.1:2181")
        self.client.start()

        self.path = "/haderp/some_path"

    def tearDown(self):
        self.client.delete(self.path, recursive=True)
        self.client.stop()

    def create_mutex(self, name="__READ__", max_leases=maxsize, timeout=0.5):
        return InterProcessMutex(
            self.client,
            self.path,
            max_leases,
            name=name,
            timeout=timeout
        )

    def test_initialization(self):
        mutex = self.create_mutex()
        assert mutex.name == "__READ__"
        assert mutex.path == self.path

    def test_acquire_marks_the_mutex_as_acquired(self):
        mutex = self.create_mutex()
        assert not mutex.is_acquired

        with mutex:
            assert mutex.is_acquired

    def test_acquire_ensures_the_container_node_exists(self):
        assert not self.client.exists(self.path)

        mutex = self.create_mutex()

        with mutex:
            assert self.client.exists(self.path)

    def test_acquire_is_reentrant(self):
        mutex = self.create_mutex()

        with mutex:
            assert len(self.client.get_children(self.path)) == 1

            with mutex:  # re-enter
                assert len(self.client.get_children(self.path)) == 2

        assert not mutex.is_acquired

    def test_acquire_blocks_when_max_leases_reached(self):
        mutex = self.create_mutex(max_leases=1)
        with mutex:
            with self.assertRaises(LockTimeout):
                mutex.acquire()  # should timeout

    def test_release_releases_the_lock(self):
        mutex = self.create_mutex()

        mutex.acquire()
        assert mutex.is_acquired

        mutex.release()
        assert not mutex.is_acquired
