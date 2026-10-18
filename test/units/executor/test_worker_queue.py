from __future__ import annotations

import multiprocessing.queues
import threading
import time

import pytest

from ansible.errors import AnsibleError
from ansible.executor.process.worker import WorkerQueue
from ansible.utils.multiprocessing import context as multiprocessing_context


def _exit_with_item(worker_queue: WorkerQueue) -> None:
    raise SystemExit(worker_queue.get())


def test_get_from_forked_worker() -> None:
    worker_queue = WorkerQueue(ctx=multiprocessing_context)

    child = multiprocessing_context.Process(target=_exit_with_item, args=(worker_queue,))
    child.start()
    worker_queue.put(42)
    child.join(30)

    assert child.exitcode == 42


def test_get_raises_ansible_error() -> None:
    worker_queue = WorkerQueue()
    worker_queue.put(AnsibleError("prompt failed"))

    with pytest.raises(AnsibleError, match="prompt failed"):
        worker_queue.get()


def test_large_item_to_waiting_worker() -> None:
    worker_queue = WorkerQueue()
    item = b"x" * (4 << 20)
    received: list[bytes] = []

    receiver = threading.Thread(target=lambda: received.append(worker_queue.get()))
    receiver.start()
    worker_queue.put(item)
    receiver.join(30)

    assert received == [item]


def test_items_are_received_in_order() -> None:
    worker_queue = WorkerQueue()

    for value in range(100):
        worker_queue.put(value)
        assert worker_queue.get() == value


def test_put_before_previous_item_received_raises() -> None:
    worker_queue = WorkerQueue()
    worker_queue.put("first")

    with pytest.raises(RuntimeError, match="has not received the previous item"):
        worker_queue.put("second")

    assert worker_queue.get() == "first"


def test_concurrent_put_from_threads() -> None:
    """Concurrent producers never corrupt items; each retries until the worker has received the previous item."""
    worker_queue = WorkerQueue()

    def put(value: int) -> None:
        while True:
            try:
                worker_queue.put(bytes([value]) * 200_000)
                return
            except RuntimeError:
                time.sleep(0.001)

    received: list[bytes] = []
    receiver = threading.Thread(target=lambda: received.extend(worker_queue.get() for _value in range(8)))
    receiver.start()
    threads = [threading.Thread(target=put, args=(value,)) for value in range(8)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join(30)

    receiver.join(30)

    assert sorted(item[0] for item in received) == list(range(8))
    assert all(len(item) == 200_000 and len(set(item)) == 1 for item in received)


def test_put_unserializable_raises() -> None:
    worker_queue = WorkerQueue()

    with pytest.raises(Exception):
        worker_queue.put(lambda: None)

    worker_queue.put("still usable")

    assert worker_queue.get() == "still usable"


def test_bounded_queue_raises() -> None:
    with pytest.raises(ValueError):
        WorkerQueue(1)


def test_queue_options_are_not_supported() -> None:
    worker_queue = WorkerQueue()

    with pytest.raises(TypeError):
        worker_queue.put("item", block=False)  # type: ignore[call-arg]

    with pytest.raises(TypeError):
        worker_queue.get(timeout=1)  # type: ignore[call-arg]


@pytest.mark.parametrize("name", ["qsize", "empty", "full", "put_nowait", "get_nowait", "close", "join_thread", "cancel_join_thread"])
def test_unsupported_queue_methods_raise(name: str) -> None:
    with pytest.raises(AttributeError):
        getattr(WorkerQueue(), name)


def test_not_a_multiprocessing_queue() -> None:
    assert not isinstance(WorkerQueue(), multiprocessing.queues.Queue)
