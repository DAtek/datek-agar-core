from asyncio import DatagramTransport, get_running_loop, Queue, CancelledError, sleep
from typing import Callable, Coroutine, Optional, Iterable

from datek_agar_core.network.protocol import Protocol, AddressTuple
from datek_agar_core.network.message import Message, MessageType
from datek_agar_core.utils import AsyncWorker, run_forever, async_log_error


class UDPClient(AsyncWorker):
    def __init__(
        self,
        *,
        host: str,
        port: int,
        handle_message: Callable[[Message], Coroutine],
        player_name: str,
        ping_interval_sec: float,
    ):
        self._host = host
        self._port = port
        self._loop = get_running_loop()
        self._player_name = player_name
        self._address: AddressTuple = (host, port)
        self._handle_message = handle_message
        self._receive_queue = Queue()
        self._ping_interval_sec = ping_interval_sec
        self._player_id = None
        self._protocol: Protocol = ...
        self._transport: TransportProxy = ...

    @property
    def player_id(self) -> Optional[int]:
        return self._player_id

    def start(self):
        super().start()
        self._loop.create_task(self._connect())

    def change_speed(self, speed_polar_coordinates: Iterable[float]):
        if not self.player_id:
            return

        self._send_message(
            Message(
                type=MessageType.CHANGE_SPEED,
                speed_polar_coordinates=speed_polar_coordinates,
                bacteria_id=self.player_id,
            )
        )

    async def _run(self):
        transport, self._protocol = await self._loop.create_datagram_endpoint(
            lambda: Protocol(self._receive_queue, self._loop),
            remote_addr=(self._host, self._port)
        )  # type: DatagramTransport, Protocol

        handle_queue_task = self._loop.create_task(self._run_handle_queue())
        self._transport = TransportProxy(transport)

        try:
            self._started.set_result(1)
            await handle_queue_task
        except CancelledError:
            pass

        self._transport.close()

    async def _connect(self):
        await self.wait_started()
        self._send_message(Message(type=MessageType.CONNECT, name=self._player_name))

    @run_forever
    @async_log_error("UDPClient")
    async def _run_handle_queue(self):
        data, _ = await self._receive_queue.get()
        message = Message.unpack(data)
        if message.type == MessageType.CONNECT:
            self._player_id = message.bacteria_id
            self._loop.create_task(self._run_keep_connection())

        self._loop.create_task(self._handle_message(message))

    @run_forever
    async def _run_keep_connection(self):
        self._send_message(Message(type=MessageType.PING))
        await sleep(self._ping_interval_sec)

    def _send_message(self, message: Message):
        self._transport.sendto(message.pack(), self._address)


class TransportProxy:
    def __init__(self, transport: DatagramTransport):
        self._transport = transport

    def close(self):
        self._transport.close()

    def sendto(self, data: bytes, address: AddressTuple):
        self._transport.sendto(data, address)
