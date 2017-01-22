kazurator
=========

|PyPI| |Build Status|

A python port of the `Shared Reentrant Read Write Lock`_ recipe from `curator`_. This package dependends on `kazoo`_ for
handling the zookeeper bits.

At this point, you're probably wondering why I didn't just use the existing locks recipe from `kazoo`_. The original
goal was to make `curator`_ and `kazoo`_ respect each other's locks such that:

1. Either could acquire a read lock, so long as neither held a write
   lock
2. Either could acquire a write lock, and block either from acquiring
   either read/write locks

I first attempted to patch the locks recipe in `kazoo`_, but the internals are a bit different. (**READ**: *I wasn't
able to make it work right*).

The reason this is necessary (at least for me), is that some code was running Scala and using `curator`_, and other code
was running Python using `kazoo`_.

Installation
------------

::

    pip install kazurator==0.1.1

Usage
-----

There are two main use cases for this package. Both of them relate to
creating an inter-process critical region.

Inter Process Mutex
~~~~~~~~~~~~~~~~~~~

To start, let's take a look at how we could implement a simple shared
(across process) mutex:

.. code:: python

    from kazoo.client import KazooClient
    from kazurator import Mutex

    def main():
        client = KazooClient(hosts="YOUR_ZK_CONNECT_STRING_HERE")
        client.start()

        mutex = Mutex(client, "/some/path")

        with mutex:
            # do your thread-safe thing here

        client.stop()

This example assumes you want a single thread to be in the critical
region. In order to support simultaneous multi-threaded access, you can
set the ``max_leases`` *kwarg* to a higher number. For example:

.. code:: python

    mutex = Mutex(client, "/some/path", max_leases=2)  # 2 thread at a time

Also, if you'd rather not use the content management protocol, you can
call ``acquire`` and ``release`` directly.

Inter Process Read Write Lock
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In some cases, you'll need to support an unlimited number of read locks,
but only a single write lock. For example, suppose you were processing
some HDFS paths by altering the format and replacing the data (totally
hypothetical of course :smile:).

You'd want any consumers of the data to acquire a read lock. This would
prevent the altering process from acquiring a write lock until the
consumer(s) are finished. Similarly, the consumers wouldn't be able to
acquire read locks until the altering process removes the write lock.

Consumers will block until the lock is available, or timeout after the
specified ``timeout`` (default is ``1s``), at which point a
``kazoo.LockTimeout`` is raised.

.. code:: python

    from kazoo.client import KazooClient
    from kazurator import ReadWriteLock

    def main():
        client = KazooClient(hosts="YOUR_ZK_CONNECT_STRING_HERE")
        client.start()

        # can optionally supply `timeout` kwarg as well
        lock = ReadWriteLock(client, "/some/path")

        with lock.write_lock:  # block until write_lock is available
            # do your thread-safe thing here

        with lock.read_lock:  # block until write_lock is gone
            # do your thread-safe thing here

        client.stop()

Development
-----------

-  Clone this repo and ``pip install -r requirements.txt``
-  Run tests ``script/test nosetests``

Running the tests will spawn a docker container to run zookeeper in. It
will be shutdown automatically at the end of the run

.. _Shared Reentrant Read Write Lock: http://curator.apache.org/curator-recipes/shared-reentrant-read-write-lock.html
.. _curator: http://curator.apache.org/index.html
.. _kazoo: https://kazoo.readthedocs.io/en/latest

.. |PyPI| image:: https://img.shields.io/pypi/v/kazurator.svg
   :target: https://pypi.python.org/pypi/kazurator
.. |Build Status| image:: https://travis-ci.org/pseudomuto/kazurator.svg?branch=master
   :target: https://travis-ci.org/pseudomuto/kazurator
