from asyncio import DatagramProtocol, Queue, AbstractEventLoop

AddressTuple = tuple[str, int]


class Protocol(DatagramProtocol):
    def __init__(self, receive_queue: Queue, loop: AbstractEventLoop):
        self._receive_queue = receive_queue
        self._loop = loop

    def datagram_received(self, data: bytes, addr: AddressTuple):
        self._loop.create_task(self._receive_queue.put((data, addr)))
