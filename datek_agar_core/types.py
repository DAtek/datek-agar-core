from typing import Optional

import numpy as np
from datek_agar_core.universe import HALF_PI, Universe
from pydantic import Field
from pydantic.main import BaseModel

_ORGANISM_MAX_COUNT = 9999
_current_id = 0


def _create_id() -> int:
    global _current_id
    _current_id += 1
    _current_id %= _ORGANISM_MAX_COUNT
    return _current_id


class Position(np.ndarray):
    _converters = {
        list: np.array,
        tuple: np.array,
        bytes: np.frombuffer
    }

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value):
        type_ = type(value)
        try:
            if type_ is np.ndarray:
                return value

            return cls._converters[type_](value, np.float32)
        except KeyError:
            raise TypeError(f"Received: {value}: {type_}\nndarray or tuple or list or bytes required")


class Organism(BaseModel):
    position: Position = Field(default_factory=lambda: np.array([0, 0], np.float32))
    radius: float = Universe.FOOD_ORGANISM_RADIUS
    id: int = Field(default_factory=_create_id)

    @property
    def size(self) -> float:
        return self.radius ** 2 * HALF_PI

    def __hash__(self):
        return self.id

    def copy(self, *args, **kwargs):
        return self


class Bacteria(Organism):
    name: str = ""
    current_speed: Position = Field(default_factory=lambda: np.array([0, 0], np.float32))
    max_speed: float = 1.0
    hue: float = 0.1


class GameStatus(BaseModel):
    bacterias: list[Bacteria] = Field(default_factory=list)
    organisms: list[Organism] = Field(default_factory=list)

    def get_bacteria_by_id(self, id_: int) -> Optional[Bacteria]:
        for bacteria in self.bacterias:
            if bacteria.id == id_:
                return bacteria

    def get_organism_by_id(self, id_: int) -> Optional[Organism]:
        for organism in self.organisms:
            if organism.id == id_:
                return organism
