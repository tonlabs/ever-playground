from enum import Enum

from .ever_playground import Cell, Builder, Slice, Dictionary, assemble, runvm

__all__ = [
    "Cell",
    "Builder",
    "Slice",
    "Dictionary",
    "ExceptionCode",
    "assemble",
    "runvm",
    "parse_smc_addr",
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

def parse_smc_addr(addr_string: str) -> tuple[int, int]:
    addr_pair = addr_string.split(":")
    assert(len(addr_pair) == 2)
    wc = int(addr_pair[0])
    addr = int(addr_pair[1], 16)
    return wc, addr
