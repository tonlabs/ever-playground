from enum import Enum
from typing import Tuple

from .ever_playground import Cell, Builder, Slice, Dictionary, assemble, runvm

__all__ = [
    "Cell",
    "Builder",
    "Slice",
    "Dictionary",
    "ExceptionCode",
    "StateInit",
    "assemble",
    "runvm",
    "parse_smc_addr",
    "load_address",
    "parse_load_address",
    "parse_adnl_address",
]

class ExceptionCode(Enum):
    NormalTermination = 0
    AlternativeTermination = 1
    StackUnderflow = 2
    StackOverflow = 3
    IntegerOverflow = 4
    RangeCheckError = 5
    InvalidOpcode = 6
    TypeCheckError = 7
    CellOverflow = 8
    CellUnderflow = 9
    DictionaryError = 10
    UnknownError = 11
    FatalError = 12
    OutOfGas = 13
    IllegalInstruction = 14

def parse_smc_addr(addr_string: str) -> Tuple[int, int]:
    """Parses smart-contract address"""
    addr_pair = addr_string.split(":")
    assert(len(addr_pair) == 2)
    wc = int(addr_pair[0])
    addr = int(addr_pair[1], 16)
    return wc, addr

def load_address(filename: str) -> Tuple[int, int]:
    """Loads address from file"""
    with open(filename, "rb") as file:
        data = file.read()
        addr = int.from_bytes(data[:32], "big")
        wc = 0
        if len(data) > 32:
            wc = int.from_bytes(data[32:], "big")
        return wc, addr

def parse_load_address(addr: str) -> Tuple[int, int]:
    """Parses string as address or load address from file (if string is prefixed by @)"""
    if addr.startswith("@"):
        return load_address(addr[1:])
    else:
        return parse_smc_addr(addr)

def parse_adnl_address(addr: str) -> int:
    """Parses ADNL address"""
    if len(addr) != 64:
        raise Exception("ADNL address must consist of exactly 64 hexadecimal characters")
    return int(addr, 16)

class StateInit:
    split_depth: int
    tick: bool
    tock: bool
    code: Cell
    data: Cell
    library: Dictionary

    def __init__(
            self,
            split_depth: int = None,
            tick: bool = False,
            tock: bool = False,
            code: Cell = None,
            data: Cell = None,
            library: Dictionary = None):
        self.split_depth = split_depth
        self.tick = tick
        self.tock = tock
        self.code = code
        self.data = data
        self.library = library

    def deserialize(self, s: Slice):
        if s.u(1):
            self.split_depth = s.u(5)
        if s.u(1):
            self.tick = s.u(1)
            self.tock = s.u(1)
        else:
            self.tick = self.tock = False
        if s.u(1):
            self.code = s.r()
        if s.u(1):
            self.data = s.r()
        if s.u(1):
            self.library = Dictionary.deserialize(256, s)
        return self

    def serialize(self) -> Builder:
        b = Builder()
        if self.split_depth is None:
            b.i(1, 0)
        else:
            b.i(1, 1).i(5, self.split_depth)
        if self.tick or self.tock:
            b.i(1, 1).i(1, self.tick).i(1, self.tock)
        else:
            b.i(1, 0)
        if self.code is None:
            b.i(1, 0)
        else:
            b.i(1, 1).r(self.code)
        if self.data is None:
            b.i(1, 0)
        else:
            b.i(1, 1).r(self.data)
        if self.library is None:
            b.i(1, 0)
        else:
            b.i(1, 1).s(Slice(self.library.serialize()))
        return b

class Currency:
    FACTOR = 1000000000 # TODO make this read-only
    value: int

    def __init__(self, value: int = None):
        if value < 0 or value.bit_length() > 128:
            raise Exception("Currency value must be non-negative and fit into 128 bits")
        self.value = value

    def deserialize(self, s: Slice):
        # TODO
        pass

    def serialize(self) -> Builder:
        if self.value == 0:
            return Builder().i(4, 0)
        len = 1
        while self.value.bit_length() > len * 8:
            len += 1
        assert(len <= 16)
        return Builder().i(4, len).i(len * 8, self.value)
