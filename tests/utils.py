from abc import ABC


class _BaseFunction(ABC):
    def __init__(self, return_value=None):
        self._return_value = return_value
        self._called_count = 0
        self._called_args: list[tuple] = []
        self._called_kwargs: list[dict] = []

    @property
    def called_count(self) -> int:
        return self._called_count

    @property
    def called_args(self) -> list[tuple]:
        return self._called_args

    @property
    def called_kwargs(self) -> list[dict]:
        return self._called_kwargs


class AsyncFunction(_BaseFunction):
    async def __call__(self, *args, **kwargs):
        self._called_args.append(args)
        self._called_kwargs.append(kwargs)
        self._called_count += 1
        return self._return_value


class Function(_BaseFunction):
    def __call__(self, *args, **kwargs):
        self._called_args.append(args)
        self._called_kwargs.append(kwargs)
        self._called_count += 1
        return self._return_value
