from __future__ import annotations

import errno
import os

from ansible.executor.process.worker import WorkerProcess
from ansible.plugins.strategy.linear import StrategyModule as LinearStrategyModule

_original_init = WorkerProcess.__init__
_original_start = WorkerProcess.start
_fail_method, _fail_count = os.environ['FAIL_WORKER'].split(':')
_calls = 0


def _simulate_failure(method: str) -> None:
    """Simulate a resource limit being hit when creating or starting the Nth worker."""
    global _calls

    if method != _fail_method:
        return

    _calls += 1

    if _calls == int(_fail_count):
        raise OSError(errno.EAGAIN, f'simulated worker {method} failure')


def _init(self, *args, **kwargs) -> None:
    _simulate_failure('init')
    _original_init(self, *args, **kwargs)


def _start(self) -> None:
    _simulate_failure('start')
    _original_start(self)


WorkerProcess.__init__ = _init  # type: ignore[method-assign]
WorkerProcess.start = _start  # type: ignore[method-assign]


class StrategyModule(LinearStrategyModule):
    pass
