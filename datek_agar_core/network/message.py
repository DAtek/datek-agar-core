from enum import Enum, auto
from lzma import decompress, compress
from typing import Optional

import numpy as np
from datek_agar_core.game import GameStatus
from datek_agar_core.types import Position
from msgpack import unpackb, packb
from pydantic import BaseModel, root_validator, validator


class MessageType(Enum):
    CONNECT = auto()
    PING = auto()
    CHANGE_SPEED = auto()
    GAME_STATUS_UPDATE = auto()


class Message(BaseModel):
    type: MessageType
    name: str = None
    bacteria_id: int = None
    speed_polar_coordinates: Optional[Position]
    game_status: GameStatus = None
    world_size: float = None
    total_nutrient: float = None

    @classmethod
    def unpack(cls, packed: bytes):
        data = unpackb(decompress(packed), use_list=False, raw=False)
        return cls(**data)

    def pack(self) -> bytes:
        packed = packb(
            self.dict(exclude_none=True),
            default=cast
        )
        return compress(packed)

    @root_validator
    def validate_values(cls, values: dict) -> dict:
        if validate := _VALIDATOR_MAP.get(values["type"]):
            return validate(values)

        return values

    @validator("speed_polar_coordinates")
    def validate_speed_vector(cls, value) -> np.ndarray:
        if np.min(value) < 0:
            raise ValueError(f"0 >= value")

        if value[0] > 1:
            raise ValueError(f"1 <= value[0]")

        return value


def validate_change_speed(values: dict) -> dict:
    if values.get("speed_polar_coordinates") is None:
        raise ValueError("`speed_polar_coordinates` required")

    return values


def validate_connect(values: dict) -> dict:
    if values.get("name") is None:
        raise ValueError("`name` required")

    return values


def cast(item):
    cast_ = _CAST_MAP.get(type(item))
    return cast_(item) if cast_ else item


_CAST_MAP = {
    MessageType: lambda obj: obj.value,
    np.ndarray: bytes,
}


_VALIDATOR_MAP = {
    MessageType.CHANGE_SPEED: validate_change_speed,
    MessageType.CONNECT: validate_connect,
}
