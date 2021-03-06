from asyncio import (
    DatagramTransport,
    get_running_loop,
    Queue,
    Lock,
    sleep,
    CancelledError,
    gather,
)
from datetime import datetime, timedelta
from typing import Callable, Coroutine, Generator, Optional

import numpy as np
from datek_agar_core.game import Game
from datek_agar_core.network.protocol import Protocol, AddressTuple
from datek_agar_core.network.message import Message, MessageType
from datek_agar_core.types import GameStatus, Organism, Bacteria
from datek_agar_core.universe import Universe
from datek_agar_core.utils import run_forever, AsyncWorker, async_log_error, create_logger


class UDPServer(AsyncWorker):
    def __init__(
        self,
        *,
        host: str,
        port: int,
        world_size: int,
        total_nutrient: int,
        client_expiration_seconds: float = 2
    ):
        self._host = host
        self._port = port
        self._is_running = False

        self._receive_queue = Queue()
        self._game_status_queue = Queue()

        self._loop = get_running_loop()

        self._address_registry = AddressRegistry(client_expiration_seconds)

        self._actions: dict[MessageType, Callable[[Message, AddressTuple], Coroutine]] = {
            MessageType.CONNECT: self._handle_connect,
            MessageType.PING: self._handle_ping,
            MessageType.CHANGE_SPEED: self._handle_move,
        }

        self._universe = Universe(
            total_nutrient=total_nutrient,
            world_size=world_size,
        )

        self._game_status_filter = GameStatusFilter(self._universe)

        self._game = Game(
            game_status_queue=self._game_status_queue,
            universe=self._universe,
        )

        self._transport: DatagramTransport = ...
        self._protocol: Protocol = ...

    async def _run(self):
        try:
            self._transport, self._protocol = await self._loop.create_datagram_endpoint(
                lambda: Protocol(self._receive_queue, self._loop),
                local_addr=(self._host, self._port)
            )  # type: DatagramTransport, Protocol
        except Exception as error:
            self._started.set_exception(error)
            raise error

        self._game.start()
        self._address_registry.start()
        self._started.set_result(1)
        try:
            await gather(
                self._run_handle_receive(),
                self._run_handle_game_status_queue(),
                loop=self._loop
            )
        except (CancelledError, KeyboardInterrupt):
            pass

        self._address_registry.stop()
        self._game.stop()
        self._transport.close()

    @run_forever
    @async_log_error("UDPServer")
    async def _run_handle_receive(self):
        data, addr = await self._receive_queue.get()  # type: bytes, AddressTuple
        message = Message.unpack(data)
        action = self._actions[message.type]
        self._loop.create_task(action(message, addr))

    @run_forever
    @async_log_error("UDPServer")
    async def _run_handle_game_status_queue(self):
        game_status = await self._game_status_queue.get()
        await self._game_status_filter.set_game_status(game_status)

        message = Message(type=MessageType.GAME_STATUS_UPDATE)

        async for address in self._address_registry.get_addresses():
            message.game_status = await self._game_status_filter.get_filtered_game_status(address)

            if message.game_status is None:
                continue

            self._transport.sendto(message.pack(), _create_address_tuple(address))

    @async_log_error("UDPServer")
    async def _handle_connect(self, message: Message, address: AddressTuple):
        await self._address_registry.update_address(address)
        _logger.info(f"Connect: {message.name} - {address[0]}:{address[1]}")
        bacteria = await self._game.add_bacteria(name=message.name, position=[0, 0])

        await self._game_status_filter.register_player(
            player_id=bacteria.id,
            address=_create_address_string(address)
        )

        self._transport.sendto(
            Message(
                type=MessageType.CONNECT,
                bacteria_id=bacteria.id,
                name=message.name,
                world_size=self._universe.world_size,
                total_nutrient=self._universe.total_nutrient,
            ).pack(),
            address
        )

    @async_log_error("UDPServer")
    async def _handle_ping(self, message: Message, address: AddressTuple):
        await self._address_registry.update_address(address)

    @async_log_error("UDPServer")
    async def _handle_move(self, message: Message, address: AddressTuple):
        await self._address_registry.update_address(address)
        await self._game.change_bacteria_speed(
            id_=message.bacteria_id,
            speed_polar_coordinates=message.speed_polar_coordinates
        )


class AddressRegistry(AsyncWorker):
    def __init__(self, expiration_seconds: float):
        self._addresses: dict[str, datetime] = {}
        self._lock = Lock()
        self._expiration_seconds_timedelta = timedelta(seconds=expiration_seconds)
        self._expiration_seconds = expiration_seconds

    async def update_address(self, address: AddressTuple):
        async with self._lock:
            self._addresses[_create_address_string(address)] = datetime.now()

    async def get_addresses(self) -> Generator[str, None, None]:
        async with self._lock:
            for address_string in self._addresses.keys():
                yield address_string

    async def _run(self):
        self._started.set_result(1)
        await self._run_in_loop()

    @run_forever
    async def _run_in_loop(self):
        await self._remove_expired_addresses()
        await sleep(self._expiration_seconds)

    @async_log_error("AddressRegistry")
    async def _remove_expired_addresses(self):
        now = datetime.now()
        async with self._lock:
            keys_to_delete = [
                key
                for key, value in self._addresses.items()
                if now - value > self._expiration_seconds_timedelta
            ]

            for key in keys_to_delete:
                del self._addresses[key]


class GameStatusFilter:
    def __init__(self, universe: Universe):
        self._universe = universe
        self._address_player_id_map: dict[str, int] = {}
        self._player_id_view_distance_map: dict[str, float] = {}
        self._lock = Lock()
        self._game_status: GameStatus = ...
        self._positions: np.ndarray = ...
        self._position_index_organism_map: dict[int, Organism] = {}

    @property
    def address_player_id_map(self) -> dict:
        return self._address_player_id_map.copy()

    async def register_player(self, player_id: int, address: str):
        async with self._lock:
            self._address_player_id_map[address] = player_id

    async def set_game_status(self, game_status: GameStatus):
        async with self._lock:
            self._game_status = game_status

        positions = []
        for item in self._game_status.organisms + self._game_status.bacterias:
            positions.append(item.position)
            self._position_index_organism_map[len(positions) - 1] = item

        self._positions = np.array(positions, np.float32)

    async def get_filtered_game_status(self, address: str) -> Optional[GameStatus]:
        async with self._lock:
            player_id = self._address_player_id_map.get(address)

            if not player_id:
                return

            bacteria = self._game_status.get_bacteria_by_id(player_id)

            if not bacteria:
                del self._address_player_id_map[address]
                return

            relative_positions = self._universe.calculate_position_vector_array(bacteria.position, self._positions)
            distances = (relative_positions[:, 0] ** 2 + relative_positions[:, 1] ** 2) ** 0.5

            index_distance_map = {
                distances[i]: i
                for i in range(len(distances))
            }

            game_status = GameStatus()

            type_list_map = {
                Organism: game_status.organisms,
                Bacteria: game_status.bacterias,
            }

            indexes = (index_distance_map[distance] for distance in distances[distances < Universe.VIEW_DISTANCE])
            for index in indexes:
                organism = self._position_index_organism_map[index]
                type_list_map[organism.__class__].append(organism)

            return game_status


def _create_address_string(address: AddressTuple) -> str:
    return f"{address[0]}:{address[1]}"


def _create_address_tuple(address: str) -> AddressTuple:
    host, port = address.split(":")
    return host, int(port)


_logger = create_logger(__name__)
