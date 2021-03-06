from asyncio import Queue, Task, sleep, Lock
from math import floor, pi, sin, cos
from random import random, uniform
from typing import Iterable, Set, Union

import numpy as np
from datek_agar_core.types import GameStatus, Bacteria, Organism, Position
from datek_agar_core.universe import Universe, HALF_PI
from datek_agar_core.utils import run_forever, AsyncWorker, async_log_error

REFRESH_FREQUENCY = 40
REFRESH_INTERVAL = 1 / REFRESH_FREQUENCY


class Game(AsyncWorker):
    def __init__(
        self,
        *,
        game_status_queue: Queue,
        universe: Universe,
    ):
        self._universe = universe
        self._game_status = GameStatus()
        self._game_status_queue = game_status_queue
        self._simulation = Simulation(universe=universe, game_status=self._game_status)
        self._lock = Lock()

        self._task: Task = ...

    async def change_bacteria_speed(
        self,
        id_: int,
        speed_polar_coordinates: Union[Position, tuple[float, float], list[float]]
    ):
        bacteria = self._game_status.get_bacteria_by_id(id_)
        current_speed = bacteria.max_speed * speed_polar_coordinates[0]

        bacteria.current_speed = np.array(
            [
                cos(speed_polar_coordinates[1]) * current_speed,
                sin(speed_polar_coordinates[1]) * current_speed,
            ],
            np.float32,
        )

    @async_log_error("Game")
    async def calculate_turn(self):
        async with self._lock:
            if not self._game_status.bacterias:
                return

            self._simulation.move_bacterias()
            self._simulation.place_food()
            self._simulation.feed_bacterias_to_other_bacterias()
            self._simulation.feed_organisms_to_bacterias()

            await self._game_status_queue.put(self._game_status)

    async def add_bacteria(self, name: str, position: Iterable[float] = None) -> Bacteria:
        max_speed = self._universe.calculate_organism_max_speed(Universe.BACTERIA_STARTING_RADIUS)
        async with self._lock:
            bacteria = Bacteria(
                name=name,
                hue=random(),
                radius=Universe.BACTERIA_STARTING_RADIUS,
                position=position if position else self._simulation.create_random_position(),
                current_speed=[0, 0],
                max_speed=max_speed,
            )
            self._game_status.bacterias.append(bacteria)

        return bacteria

    async def _run(self):
        self._started.set_result(1)
        await self._run_in_loop()

    @run_forever
    async def _run_in_loop(self):
        await self.calculate_turn()
        await sleep(REFRESH_INTERVAL)


class Simulation:
    def __init__(self, *, universe: Universe, game_status: GameStatus):
        self._universe = universe
        self._game_status = game_status

    @property
    def total_in_game_organics_size(self) -> float:
        return sum((organism.size for organism in self._game_status.organisms)) \
               + sum((bacteria.size for bacteria in self._game_status.bacterias))

    def move_bacterias(self) -> None:
        for bacteria in self._game_status.bacterias:
            bacteria.position += (bacteria.current_speed / REFRESH_FREQUENCY)
            bacteria.position %= self._universe.world_size

    def feed_bacterias_to_other_bacterias(self):
        self._game_status.bacterias.sort(key=lambda item: item.size, reverse=True)
        bacteria_ids = [bacteria.id for bacteria in self._game_status.bacterias]

        for id_ in bacteria_ids:
            bacteria = self._game_status.get_bacteria_by_id(id_)
            if not bacteria:
                continue

            bacterias = self.get_bacterias_to_eat(bacteria)

            if not bacterias:
                continue

            self._modify_bacteria_size_and_speed(bacteria, bacterias)
            self.remove_bacterias(set(bacterias))

    def feed_organisms_to_bacterias(self):
        for bacteria in self._game_status.bacterias:
            organisms = self.get_organisms_to_eat(bacteria)

            if not organisms:
                continue

            self._modify_bacteria_size_and_speed(bacteria, organisms)
            self.remove_organisms(set(organisms))

    def _modify_bacteria_size_and_speed(self, bacteria: Bacteria, organisms_to_eat: list[Organism]):
        size_increment = _calculate_size_summary(organisms_to_eat)
        new_size = bacteria.size + size_increment
        bacteria.radius = (new_size * 2 / pi) ** 0.5
        previous_max_speed = bacteria.max_speed
        max_speed = self._universe.calculate_organism_max_speed(bacteria.radius)
        bacteria.max_speed = max_speed
        bacteria.current_speed *= previous_max_speed / bacteria.max_speed

    def create_random_position(self) -> tuple[float, float]:
        return (
            uniform(0, self._universe.world_size),
            uniform(0, self._universe.world_size)
        )

    def place_food(self) -> None:
        organism_count = floor(
            (self._universe.total_nutrient - self.total_in_game_organics_size) / Universe.FOOD_ORGANISM_SIZE
        )

        if organism_count < 1:
            return

        for _ in range(organism_count):
            self._game_status.organisms.append(
                Organism(
                    position=self.create_random_position(),
                    radius=Universe.FOOD_ORGANISM_RADIUS,
                )
            )

        self._game_status.organisms.sort(key=lambda item: item.position[0])

    def remove_organisms(self, organisms: Set[Organism]):
        old_organisms = set(self._game_status.organisms)
        self._game_status.organisms = list(old_organisms - organisms)

    def remove_bacterias(self, bacterias: Set[Bacteria]):
        old_bacterias = set(self._game_status.bacterias)
        self._game_status.bacterias = list(old_bacterias - bacterias)

    def get_organisms_to_eat(self, bacteria: Bacteria) -> list[Organism]:
        if not self._game_status.organisms:
            return []

        organism_positions = np.array([organism.position for organism in self._game_status.organisms], np.float32)
        relative_positions = self._universe.calculate_position_vector_array(bacteria.position, organism_positions)
        distances = (relative_positions[:, 0] ** 2 + relative_positions[:, 1] ** 2) ** 0.5

        distance_id_map = {
            distances[id_]: id_
            for id_ in range(len(distances))
        }

        wanted_distances = distances[bacteria.radius >= distances]

        return [
            self._game_status.organisms[distance_id_map[distance]]
            for distance in wanted_distances
        ]

    def get_bacterias_to_eat(self, bacteria: Bacteria) -> list[Bacteria]:
        bacteria_positions = []
        position_id_map = {}

        for bacteria_ in self._game_status.bacterias:
            if (
                bacteria_.id == bacteria.id
                or (bacteria.radius / bacteria_.radius) < Universe.MINIMAL_RADIUS_MODIFIER_TO_EAT
            ):
                continue

            bacteria_positions.append(bacteria_.position)
            position_id_map[len(bacteria_positions) - 1] = bacteria_.id

        if not bacteria_positions:
            return []

        bacteria_positions = np.array(bacteria_positions, np.float32)
        relative_positions = self._universe.calculate_position_vector_array(bacteria.position, bacteria_positions)
        distances = (relative_positions[:, 0] ** 2 + relative_positions[:, 1] ** 2) ** 0.5

        wanted_ids = [i for i in range(len(distances)) if distances[i] < bacteria.radius]

        return [
            self._game_status.get_bacteria_by_id(position_id_map[id_])
            for id_ in wanted_ids
        ]


def _calculate_size_summary(organisms: list[Organism]):
    radius_array = np.array([organism.radius for organism in organisms], np.float32)
    return sum(radius_array ** 2 * HALF_PI)
