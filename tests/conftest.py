from asyncio import DatagramTransport, get_running_loop, DatagramProtocol

from datek_agar_core.game import REFRESH_INTERVAL
from datek_agar_core.network.protocol import AddressTuple
from datek_agar_core.network.message import Message, MessageType
from datek_agar_core.network.server import UDPServer
from pytest import fixture

HOST = "127.0.0.1"
PORT = 9999


@fixture
async def test_server() -> UDPServer:
    server = UDPServer(
        host=HOST,
        port=PORT,
        client_expiration_seconds=REFRESH_INTERVAL * 2,
        world_size=100,
        total_nutrient=90,
    )

    server.start()
    await server.wait_started()
    yield
    server.stop()
    await server.task


@fixture
async def test_client(test_server) -> tuple[DatagramTransport, list[bytes]]:
    loop = get_running_loop()
    messages = []

    transport, protocol = await loop.create_datagram_endpoint(
        lambda: ClientProtocol(messages),
        remote_addr=(HOST, PORT)
    )

    yield transport, messages

    transport.close()


@fixture
async def connected_client(test_client, connect_message) -> tuple[DatagramTransport, list[bytes]]:
    transport, messages = test_client[0], test_client[1]
    transport.sendto(connect_message.pack(), (HOST, PORT))
    yield test_client


@fixture
def connect_message() -> Message:
    return Message(
        type=MessageType.CONNECT,
        name="John"
    )


class ClientProtocol(DatagramProtocol):
    def __init__(self, messages: list):
        self._messages = messages

    def datagram_received(self, data: bytes, addr: AddressTuple) -> None:
        self._messages.append(data)
