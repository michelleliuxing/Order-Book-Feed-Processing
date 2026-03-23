"""
Binary message parsing for order book feed data.

Decodes a binary input stream into structured Python objects. Each message
in the stream has a fixed-size header followed by a variable-size body
whose layout depends on the message type.

"""

import struct
from typing import BinaryIO


def decode_symbol(encoded: bytes) -> str:
    return encoded.decode().rstrip("\x00")


class Header(object):
    """Contains header information about a message."""

    ENCODING = "<LLc"

    def __init__(self, seq_num: int, msg_size: int, msg_type: str):
        self.seq_num = seq_num # Unique sequence number for this message
        self.msg_size = msg_size # Body size in bytes
        self.msg_type = msg_type # One of 'A', 'U', 'D', 'E'

    @classmethod
    def unpack(cls, buf: bytes):
        seq_num, msg_size, msg_type = struct.unpack(cls.ENCODING, buf)
        return Header(seq_num, msg_size, msg_type.decode())


class OrderAdd(object):
    """A new order has been added to the book (message type 'A')."""

    TYPE = "A"
    ENCODING = "<3sQc3sQi4s"  # Symbol, Order ID, Side, Reserved, Size, Price, Reserved

    def __init__(self, symbol: str, order_id: int, side: str, volume: int, price: int):
        self.symbol = symbol
        self.order_id = order_id
        self.side = side # 'B' for bid, 'S' for ask
        self.volume = volume # Number of units in this order
        self.price = price # Signed integer price (fixed-point, /10000 for dollars)

    @classmethod
    def unpack(cls, buf: bytes):
        symbol, order_id, side, _, volume, price, _ = struct.unpack(cls.ENCODING, buf)
        return OrderAdd(decode_symbol(symbol), order_id, side.decode(), volume, price)


class OrderUpdate(object):
    """An existing order's price and/or volume has changed (message type 'U')."""

    TYPE = "U"
    ENCODING = "<3sQc3sQi4s"  # Symbol, Order ID, Side, Reserved, Size, Price, Reserved

    def __init__(self, symbol: str, order_id: int, side: str, volume: int, price: int):
        self.symbol = symbol
        self.order_id = order_id
        self.side = side
        self.volume = volume # New volume (replaces previous)
        self.price = price # New price  (replaces previous)

    @classmethod
    def unpack(cls, buf: bytes):
        """Unpack 31 raw bytes into an OrderUpdate instance."""
        symbol, order_id, side, _, volume, price, _ = struct.unpack(cls.ENCODING, buf)
        return OrderUpdate(decode_symbol(symbol), order_id, side.decode(), volume, price)


class OrderDelete(object):
    """Contains details of an order book delete event."""

    TYPE = "D"
    ENCODING = "<3sQc3s" # Symbol, Order ID, Side, Reserved

    def __init__(self, symbol: str, order_id: int, side: str):
        self.symbol = symbol
        self.order_id = order_id
        self.side = side

    @classmethod
    def unpack(cls, buf: bytes):
        symbol, order_id, side, _ = struct.unpack(cls.ENCODING, buf)
        return OrderDelete(decode_symbol(symbol), order_id, side.decode())


class OrderTraded(object):
    """Contains details of an order being traded."""

    TYPE = "E"
    ENCODING = "<3sQc3sQ" # Symbol, Order ID, Side, Reserved, Traded Quantity

    def __init__(self, symbol: str, order_id: int, side: str, volume: int):
        self.symbol = symbol
        self.order_id = order_id
        self.side = side
        self.volume = volume    # Traded quantity (to subtract), if remaining volumn is 0, order is fulfilled and should be removed from book

    @classmethod
    def unpack(cls, buf: bytes):
        symbol, order_id, side, _, volume = struct.unpack(cls.ENCODING, buf)
        return OrderTraded(decode_symbol(symbol), order_id, side.decode(), volume)


def gen_from(bin: BinaryIO):
    """
    gen_from is a generator that reads from given buffer untill fully consumed.
    returns a Header and [OrderAdd | OrderUpdate | OrderDelete | OrderTraded]
    """

    # Pre-compute header size to avoid recalculating each iteration
    header_size = struct.calcsize(Header.ENCODING)

    while True:
        # Read the next header; empty result means end of stream
        buf = bin.read(header_size)
        if not buf:
            return

        header = Header.unpack(buf)
        buf = bin.read(header.msg_size - 1)
        if len(buf) < (header.msg_size - 1):
            raise Exception(f"Incomplete message size({header.msg_size}) read({len(buf)})")

        # Route to the correct message class based on the type character
        if header.msg_type == "A":
            unpack = OrderAdd.unpack
        elif header.msg_type == "U":
            unpack = OrderUpdate.unpack
        elif header.msg_type == "D":
            unpack = OrderDelete.unpack
        elif header.msg_type == "E":
            unpack = OrderTraded.unpack
        else:
            raise Exception(f"Unknown header code: {header.msg_type}")

        yield header, unpack(buf)
