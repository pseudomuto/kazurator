from contextlib import contextmanager
from kazoo.retry import ForceRetryError, RetryFailedError


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
