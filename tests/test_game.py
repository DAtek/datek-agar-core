from asyncio import Queue, sleep, CancelledError
from math import isclose, floor, pi

from datek_agar_core.game import Game, GameStatus, Simulation, Bacteria, Organism
from datek_agar_core.universe import Universe
from pytest import mark


class TestGame:
    @mark.asyncio
    async def test_move_bacteria(self):
        queue = Queue()
        game = Game(
            game_status_queue=queue,
            universe=universe
        )

        bacteria = await game.add_bacteria("John", [50, 50])
        speed_polar_coordinates = (1, pi)

        await game.change_bacteria_speed(bacteria.id, speed_polar_coordinates)
        await game.calculate_turn()

        assert isclose(bacteria.position[0], 49.875, rel_tol=0.001)
        assert isclose(bacteria.position[1], 50, rel_tol=0.001)

    @mark.asyncio
    async def test_loop(self):
        game = Game(
            game_status_queue=Queue(),
            universe=universe
        )

        game.start()
        await sleep(0.01)
        game.stop()

        try:
            await game.task
        except CancelledError:
            pass


class TestSimulation:
    def test_total_in_game_organics_size(self):
        game_status = GameStatus()
        bacteria = Bacteria(
            name="asd",
            current_speed=[0, 0],
            max_speed=0,
            hue=0,
            position=[0, 0],
            radius=1
        )
        game_status.bacterias.append(bacteria)
        organism = Organism(
            position=[0, 0],
            radius=2
        )
        game_status.organisms.append(organism)

        simulation = Simulation(
            universe=universe,
            game_status=game_status
        )

        wanted = organism.size + bacteria.size
        assert isclose(simulation.total_in_game_organics_size, wanted)

    def test_place_food(self):
        game_status = GameStatus()
        simulation = Simulation(
            universe=universe,
            game_status=game_status
        )

        wanted_count = floor(
            (universe.total_nutrient - simulation.total_in_game_organics_size) / Universe.FOOD_ORGANISM_SIZE
        )

        simulation.place_food()

        assert len(game_status.organisms) == wanted_count
        simulation.place_food()
        assert len(game_status.organisms) == wanted_count

    def test_feed_organisms_to_bacterias(self):
        game_status = GameStatus()
        simulation = Simulation(
            universe=universe,
            game_status=game_status
        )

        bacteria1 = Bacteria(
            name="asd",
            current_speed=[0, 0],
            max_speed=0,
            hue=0,
            position=[0, 0],
            radius=2
        )
        initial_size = bacteria1.size

        bacteria2 = Bacteria(
            name="asd2",
            current_speed=[0, 0],
            max_speed=0,
            hue=0,
            position=[50, 50],
            radius=2
        )

        organism1 = Organism(
            position=[1, 1],
            radius=1,
        )
        organism_size = organism1.size

        organism2 = Organism(
            position=[60, 60],
            radius=2,
        )

        game_status.bacterias = [bacteria1, bacteria2]
        game_status.organisms = [organism1, organism2]

        simulation.feed_organisms_to_bacterias()

        assert len(game_status.organisms) == 1
        assert isclose(bacteria1.size, initial_size + organism_size, rel_tol=0.001)

    def test_feed_bacterias_to_bacterias(self):
        game_status = GameStatus()
        simulation = Simulation(
            universe=universe,
            game_status=game_status
        )

        bacteria1 = Bacteria(
            name="asd",
            current_speed=[0, 0],
            max_speed=0,
            hue=0,
            position=[0, 0],
            radius=3
        )
        initial_size = bacteria1.size

        bacteria2 = Bacteria(
            name="asd2",
            current_speed=[0, 0],
            max_speed=0,
            hue=0,
            position=[2, 0],
            radius=2
        )
        bacteria2_size = bacteria2.size

        bacteria3 = Bacteria(
            name="asd3",
            current_speed=[0, 0],
            max_speed=0,
            hue=0,
            position=[50, 50],
            radius=2
        )

        game_status.bacterias = [bacteria1, bacteria2, bacteria3]

        simulation.feed_bacterias_to_other_bacterias()

        assert len(game_status.bacterias) == 2
        assert bacteria2.id not in [bacteria.id for bacteria in game_status.bacterias]
        assert isclose(bacteria1.size, initial_size + bacteria2_size, rel_tol=0.001)

    def test_get_organisms_to_eat_returns_empty_list(self):
        bacteria = Bacteria(
            name="asd",
            current_speed=[0, 0],
            max_speed=0,
            hue=0,
            position=[0, 0],
            radius=1
        )

        game_status = GameStatus(
            bacterias=[bacteria]
        )

        simulation = Simulation(
            universe=universe,
            game_status=game_status
        )

        assert not simulation.get_organisms_to_eat(bacteria)


WORLD_SIZE = 100

universe = Universe(
    total_nutrient=5,
    world_size=WORLD_SIZE
)
