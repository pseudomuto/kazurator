from kazoo.exceptions import LockTimeout
from kazurator import Mutex
from sys import maxsize
from threading import Thread, ThreadError
from unittest import TestCase
from . import kazoo_client


class TestMutex(TestCase):
    def setUp(self):
        self.path = "/haderp/some_path"

    def tearDown(self):
        with kazoo_client() as client:
            client.delete(self.path, recursive=True)

    def _create_mutex(self, client, **kwargs):
        name = kwargs.get("name", "__READ__")
        max_leases = kwargs.get("max_leases", maxsize)
        timeout = kwargs.get("timeout", 0.5)

        return Mutex(
            client,
            self.path,
            max_leases,
            name=name,
            timeout=timeout
        )

    def test_initialization(self):
        with kazoo_client() as client:
            mutex = self._create_mutex(client)
            assert mutex.name.endswith("__READ__")
            assert mutex.path == self.path

    def test_is_owned_by_current_thread_when_owned(self):
        with kazoo_client() as client:
            mutex = self._create_mutex(client)
            with mutex:
                assert mutex.is_owned_by_current_thread

    def test_is_owned_by_current_thread_when_owned_by_another_thread(self):
        with kazoo_client() as client:
            mutex = self._create_mutex(client)

            # the owning thread
            thread = Thread(target=mutex.acquire)
            thread.start()
            thread.join()

            assert not mutex.is_owned_by_current_thread

    def test_acquire_marks_the_mutex_as_acquired(self):
        with kazoo_client() as client:
            mutex = self._create_mutex(client)
            assert not mutex.is_acquired

            with mutex:
                assert mutex.is_acquired

    def test_acquire_is_reentrant(self):
        with kazoo_client() as client:
            mutex = self._create_mutex(client)

            with mutex:
                assert len(client.get_children(self.path)) == 1
                assert mutex.acquire()
                mutex.release()

            assert not mutex.is_acquired

    def test_acquire_blocks_when_max_leases_reached(self):
        with kazoo_client() as client:
            first = self._create_mutex(client, max_leases=1)
            second = self._create_mutex(client, max_leases=1)

            with first:
                with self.assertRaises(LockTimeout):
                    second.acquire()  # should timeout

    def test_release_releases_the_lock(self):
        with kazoo_client() as client:
            mutex = self._create_mutex(client)

            mutex.acquire()
            assert mutex.is_acquired

            mutex.release()
            assert not mutex.is_acquired

    def test_release_raises_thread_error_when_lock_not_acquired(self):
        with kazoo_client() as client:
            mutex = self._create_mutex(client)
            message = "You do not own the lock: " + self.path

            with self.assertRaises(ThreadError) as err:
                mutex.release()

            assert str(err.exception) == message
