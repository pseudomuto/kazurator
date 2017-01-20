from kazurator.utils import lazyproperty, make_path, mutex
from threading import Lock


class TestClass:
    @lazyproperty
    def first_name(self):
        return "Test"

    @lazyproperty
    def last_name(self):
        return "User"


def test_make_path():
    assert make_path("a", "b", "c") == "/a/b/c"
    assert make_path("a") == "/a"
    assert make_path("abc", "000") == "/abc/000"


def test_lazyproperty():
    instance = TestClass()
    assert instance.first_name is instance.first_name
    assert instance.last_name is instance.last_name


def test_mutex():
    lock = Lock()

    with mutex(lock):
        assert not lock.acquire(False)  # already taken

    assert lock.acquire(True)  # should be free now
    lock.release()
