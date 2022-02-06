from asyncio import sleep
from unittest.mock import patch

from datek_agar_core.game import REFRESH_INTERVAL
from pytest import mark

from datek_agar_core.network.client import UDPClient, TransportProxy
from datek_agar_core.network.message import Message
from datek_agar_core.network.server import AddressRegistry
from ..conftest import HOST, PORT
from ..utils import AsyncFunction, Function


class TestUDPClient:
    @mark.asyncio
    @mark.parametrize(["player_id", "wanted_value"], [(1, 2), (None, 1)])
    async def test_change_speed(self, test_server, player_id, wanted_value):
        client = UDPClient(
            player_name="Jenny",
            host=HOST,
            port=PORT,
            handle_message=handle_message,
            ping_interval_sec=0.5,
        )
        sendto = Function()

        @patch.object(TransportProxy, TransportProxy.sendto.__name__, sendto)
        @patch.object(UDPClient, "player_id", player_id)
        async def _test():
            client.start()
            await client.wait_started()
            await sleep(REFRESH_INTERVAL)
            client.change_speed((1, 1))
            client.stop()

        await _test()

        assert sendto._called_count == wanted_value

    @mark.asyncio
    async def test_connect_on_start_and_keep_alive(self, test_server):
        update_address = AsyncFunction()

        client = UDPClient(
            player_name="Jenny",
            host=HOST,
            port=PORT,
            handle_message=handle_message,
            ping_interval_sec=0.5,
        )

        assert not client.player_id
        with patch.object(
            AddressRegistry, AddressRegistry.update_address.__name__, update_address
        ):
            client.start()
            await client.wait_started()
            await sleep(REFRESH_INTERVAL)

        assert update_address.called_count
        assert client.player_id

        client.stop()
        await client.task


async def handle_message(message: Message):
    pass
