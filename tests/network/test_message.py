from lzma import decompress, compress

from datek_agar_core.network.message import Message, MessageType, cast
from msgpack import packb, unpackb
from pydantic import ValidationError
from pytest import raises, mark


class TestMessage:
    @mark.parametrize("params", [
        {"type": MessageType.CONNECT},
        {"type": MessageType.CHANGE_SPEED},
        {"type": MessageType.CHANGE_SPEED, "speed_polar_coordinates": (-1.1, 0)},
        {"type": MessageType.CHANGE_SPEED, "speed_polar_coordinates": (1.1, 0)},
    ])
    def test_invalid(self, params: dict):
        with raises(ValidationError):
            Message(**params)

    def test_unpack(self):
        message = Message(
            type=MessageType.CONNECT,
            name="John"
        )

        packed = compress(packb(message.dict(exclude_none=True),  default=cast))
        unpacked = Message.unpack(packed)

        assert unpacked.type == message.type
        assert unpacked.name == message.name

    def test_pack(self):
        message = Message(
            type=MessageType.CHANGE_SPEED,
            speed_polar_coordinates=(0, 1)
        )

        packed = message.pack()
        unpacked = unpackb(decompress(packed), use_list=False, raw=False)
        unpacked_message = Message(**unpacked)

        assert unpacked_message.type == message.type
        assert unpacked_message.name == message.name
