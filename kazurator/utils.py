from contextlib import contextmanager
from kazoo.retry import ForceRetryError, RetryFailedError


class lazyproperty:
    def __init__(self, fn):
        self._fn = fn

    def __get__(self, instance, klass):
        if instance is None:
            return self

        result = self._fn(instance)
        setattr(instance, self._fn.__name__, result)
        return result


@contextmanager
def mutex(lock):
    try:
        lock.acquire()
        yield
    finally:
        lock.release()


@contextmanager
def retryable(lock, retry_fn, timeout):
    try:
        retry = retry_fn.copy()
        retry.deadline = timeout

        def lockify():
            acquired = lock.acquire(False)
            if not acquired:
                raise ForceRetryError()

            return True

        locked = lock.acquire(False)

        if not locked:
            try:
                locked = retry(lockify)
            except RetryFailedError:
                yield False

        yield locked
    finally:
        lock.release()
