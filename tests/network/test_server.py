from asyncio import sleep
from logging import ERROR
from unittest.mock import patch, MagicMock

from datek_agar_core.game import Game, REFRESH_INTERVAL
from datek_agar_core.network.message import Message, MessageType
from datek_agar_core.network.server import AddressRegistry, UDPServer, GameStatusFilter
from datek_agar_core.types import Bacteria, GameStatus, Organism
from datek_agar_core.universe import Universe
from msgpack import packb
from pytest import mark, raises

from ..conftest import HOST, PORT
from ..utils import AsyncFunction


class TestAddressRegistry:
    CLIENT_EXPIRATION_SECONDS = 0.001

    @mark.asyncio
    async def test_update_address(self):
        host = "127.0.0.1"
        port = 8000
        registry = AddressRegistry(1)

        await registry.update_address((host, port))
        addresses = [address async for address in registry.get_addresses()]

        assert len(addresses) == 1
        assert addresses[0] == f"{host}:{port}"

    @mark.asyncio
    async def test_remove_expired_addresses(self):
        host = "127.0.0.1"
        port = 8000
        registry = AddressRegistry(self.CLIENT_EXPIRATION_SECONDS)
        await registry.update_address((host, port))
        registry.start()
        await sleep(self.CLIENT_EXPIRATION_SECONDS * 2)
        registry.stop()
        addresses = [address async for address in registry.get_addresses()]

        assert not len(addresses)


class TestUDPServer:
    @mark.asyncio
    async def test_connect(self, test_client, connect_message, caplog):
        transport, messages = test_client[0], test_client[1]
        transport.sendto(connect_message.pack(), (HOST, PORT))
        await sleep(REFRESH_INTERVAL)

        assert len(messages) == 1
        unpacked = Message.unpack(messages[0])
        assert unpacked.type == connect_message.type

    @mark.asyncio
    async def test_ping(self, test_client, test_server):
        transport, messages = test_client[0], test_client[1]
        message = Message(
            type=MessageType.PING,
        )
        update_address = MagicMock()

        with patch.object(AddressRegistry, AddressRegistry.update_address.__name__, update_address):
            transport.sendto(message.pack(), (HOST, PORT))
            await sleep(REFRESH_INTERVAL)

        assert not len(messages)
        assert update_address.called

    @mark.asyncio
    async def test_move(self, connected_client):
        transport, messages = connected_client[0], connected_client[1]
        message = Message(
            type=MessageType.CHANGE_SPEED,
            speed_polar_coordinates=(0.1, 0.2)
        )

        change_bacteria_speed = AsyncFunction()
        with patch.object(Game, Game.change_bacteria_speed.__name__, change_bacteria_speed):
            transport.sendto(message.pack(), (HOST, PORT))
            await sleep(REFRESH_INTERVAL)

        assert change_bacteria_speed.called_count

    @mark.asyncio
    async def test_player_was_eaten(self, connected_client):
        transport, messages = connected_client[0], connected_client[1]

        get_filtered_game_status = AsyncFunction()

        with patch.object(
            GameStatusFilter,
            GameStatusFilter.get_filtered_game_status.__name__,
            get_filtered_game_status
        ):
            await sleep(REFRESH_INTERVAL)

        # no game status update, just connect response
        assert len(messages) == 1

    @mark.asyncio
    async def test_log_error(self, connected_client, caplog):
        transport, messages = connected_client[0], connected_client[1]
        transport.sendto(packb({"type": MessageType.CHANGE_SPEED.value}), (HOST, PORT))
        await sleep(REFRESH_INTERVAL)
        assert caplog.records[1].levelno == ERROR

    @mark.asyncio
    async def test_raise_error_if_port_is_taken(self, test_server):
        server = UDPServer(
            host=HOST,
            port=PORT,
            world_size=100,
            total_nutrient=90,
        )

        server.start()

        with raises(OSError):
            await server.wait_started()


bacteria = Bacteria()


class TestGameStatusFilter:
    @mark.asyncio
    async def test_register_player(self):
        game_status_filter = GameStatusFilter(universe)
        address = "127.0.0.1:9999"

        await game_status_filter.register_player(bacteria.id, address)
        assert game_status_filter.address_player_id_map[address] == bacteria.id

    @mark.asyncio
    async def test_get_filtered_game_status_returns_filtered_game_status(self):
        game_status_filter = GameStatusFilter(universe)
        address1 = "a"
        bacteria1 = Bacteria(position=[0, 0])
        address2 = "b"
        bacteria2 = Bacteria(position=[1, 1])
        address3 = "c"
        bacteria3 = Bacteria(position=[Universe.VIEW_DISTANCE + 10, Universe.VIEW_DISTANCE + 10])
        organism1 = Organism(position=[5, 5])
        organism2 = Organism(position=[Universe.VIEW_DISTANCE + 5, Universe.VIEW_DISTANCE + 5])

        game_status = GameStatus(
            bacterias=[bacteria1, bacteria2, bacteria3],
            organisms=[organism1, organism2]
        )

        await game_status_filter.set_game_status(game_status)

        await game_status_filter.register_player(bacteria1.id, address1)
        await game_status_filter.register_player(bacteria2.id, address2)
        await game_status_filter.register_player(bacteria3.id, address3)

        filtered_status = await game_status_filter.get_filtered_game_status(address1)
        assert set(filtered_status.bacterias) == {bacteria1, bacteria2}
        assert set(filtered_status.organisms) == {organism1}

        filtered_status = await game_status_filter.get_filtered_game_status(address2)
        assert set(filtered_status.bacterias) == {bacteria1, bacteria2}
        assert set(filtered_status.organisms) == {organism1}

        filtered_status = await game_status_filter.get_filtered_game_status(address3)
        assert set(filtered_status.bacterias) == {bacteria3}
        assert set(filtered_status.organisms) == {organism2}

    @mark.asyncio
    async def test_get_filtered_game_status_returns_none_if_player_not_exists(self):
        game_status_filter = GameStatusFilter(universe)
        assert await game_status_filter.get_filtered_game_status("") is None

    @mark.asyncio
    async def test_get_filtered_game_status_returns_none_if_bacteria_not_exists(self):
        address = "a"
        game_status_filter = GameStatusFilter(universe)
        await game_status_filter.register_player(1, address)
        await game_status_filter.set_game_status(GameStatus())

        assert await game_status_filter.get_filtered_game_status(address) is None
        address_player_id_map = game_status_filter.address_player_id_map
        assert address_player_id_map.get(address) is None


universe = Universe(
    total_nutrient=10,
    world_size=1000,
)
