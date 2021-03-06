from abc import ABC, abstractmethod
from asyncio import Task, create_task, Future
from functools import wraps
from logging import Formatter, Logger
from typing import Optional, Callable

from datek_app_utils.log import create_logger as _create_logger, LogFormatter

_formatter = Formatter("%(asctime)s [%(name)s] %(levelname)-8s %(message)s")

LogFormatter.set(_formatter)


class AsyncWorker(ABC):
    _task: Task
    _started: Future

    @property
    def task(self) -> Optional[Task]:
        return self._task if self._task is not ... else None

    def start(self):
        self._task = create_task(self._run())
        self._started = Future()

    async def wait_started(self):
        await self._started

    def stop(self):
        if isinstance(self._task, Task):
            self._task.cancel()

    @abstractmethod
    async def _run(self): ...


def create_logger(name: str) -> Logger:
    return _create_logger(name)


def run_forever(func: Callable):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        while True:
            await func(*args, **kwargs)

    return wrapper


def async_log_error(class_name: str):
    def decorator(func: Callable):
        logger = create_logger(".".join([class_name, func.__name__]))

        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as exception:
                logger.error(f"{exception.__class__}: {exception}", exc_info=True)

        return wrapper

    return decorator
