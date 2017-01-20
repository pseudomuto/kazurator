from contextlib import contextmanager
from kazoo.client import KazooClient


@contextmanager
def kazoo_client():
    try:
        client = KazooClient(hosts="127.0.0.1:2181")
        client.start()
        yield client
    finally:
        client.stop()
