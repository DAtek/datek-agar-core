import numpy as np
from datek_agar_core.types import Position, Bacteria, GameStatus, Organism
from pydantic import ValidationError
from pydantic.main import BaseModel
from pytest import raises


class TestGameStatus:
    def test_get_bacteria_by_id(self):
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

        assert id(game_status.get_bacteria_by_id(bacteria.id)) == id(bacteria)
        assert game_status.get_bacteria_by_id(8) is None

    def test_get_organism_by_id(self):
        organism = Organism(
            position=[0, 0],
            radius=1
        )

        game_status = GameStatus(
            organisms=[organism]
        )

        assert id(game_status.get_organism_by_id(organism.id)) == id(organism)
        assert game_status.get_organism_by_id(8) is None


class TestPosition:
    def test_valid(self):
        box = Box(
            x=np.array([1, 1], np.float32),
            y=(0, 6)
        )

        assert isinstance(box.x, np.ndarray)
        assert isinstance(box.y, np.ndarray)

        box2 = Box(
            x=np.array([1, 1], np.float32),
            y=[0, 6]
        )
        assert isinstance(box2.y, np.ndarray)

    def test_raises_type_error_on_wrong_type(self):
        with raises(ValidationError):
            Box(
                x="a",
                y=(0, 6)
            )


class Box(BaseModel):
    x: Position
    y: Position