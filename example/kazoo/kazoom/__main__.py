import os
from contextlib import contextmanager
from termcolor import colored
from kazoo.client import KazooClient
from kazurator import ReadWriteLock


PATH = "/haderp/some_path"
TIMEOUT = 60.0


@contextmanager
def padding():
    try:
        print("")
        yield
    finally:
        print("")


def _acquire_read_lock(lock):
    if lock.read_lock.acquire():
        with padding():
            print(colored("Acquired the READ lock", "green"))


def _acquire_write_lock(lock):
    if lock.write_lock.acquire():
        with padding():
            print(colored("Acquired the WRITE lock", "green"))


def _release_read_lock(lock):
    with padding():
        lock.read_lock.release()
        print(colored("Released the READ lock", "yellow"))


def _release_write_lock(lock):
    with padding():
        lock.write_lock.release()
        print(colored("Released the WRITE lock", "yellow"))


def _show_participant_nodes(lock):
    nodes = lock.get_participant_nodes()
    count = colored(str(len(nodes)), "yellow")

    with padding():
        print("There are " + count + " node(s) participating:")

        for node in nodes:
            print("  * " + node)


def _print_menu():
    print("Select one of the following:")
    print("1. Acquire read lock")
    print("2. Acquire write lock")
    print("3. Release read lock")
    print("4. Release write lock")
    print("5. Show participant nodes")
    print("6. Quit")

    return input("\nChoice: ")


if __name__ == "__main__":
    options = {
        1: _acquire_read_lock,
        2: _acquire_write_lock,
        3: _release_read_lock,
        4: _release_write_lock,
        5: _show_participant_nodes
    }

    client = KazooClient(hosts=os.getenv("ZK_CONNECT_STRING"))
    client.start()

    lock = ReadWriteLock(client, PATH, timeout=TIMEOUT)

    while True:
        option = int(_print_menu())

        if option not in options:
            client.stop()
            break

        try:
            options[option](lock)
        except Exception as e:
            print(colored(repr(e), "red"))
            print("")
