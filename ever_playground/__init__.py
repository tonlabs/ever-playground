from enum import Enum
from typing import Optional, Tuple
from fractions import Fraction

from .ever_playground import Cell, Builder, Slice, Dictionary, NaN, Gas, Continuation, ContinuationType, SaveList, VmState, VmResult, assemble, runvm_generic
from .ever_playground import ed25519_new_keypair, ed25519_secret_to_public, ed25519_sign, ed25519_check_signature

__all__ = [
    "Cell",
    "Builder",
    "Slice",
    "Dictionary",
    "NaN",
    "ExceptionCode",
    "StateInit",
    "assemble",
    "Gas",
    "ContinuationType",
    "Continuation",
    "SaveList",
    "VmState",
    "VmResult",
    "runvm_generic",
    "runvm",
    "parse_smc_addr",
    "load_address",
    "parse_load_address",
    "parse_adnl_address",
    "ed25519_new_keypair",
    "ed25519_secret_to_public",
    "ed25519_sign",
    "ed25519_check_signature",
]

def runvm(code, stack, **kwargs) -> VmResult:
    """
    Invokes TVM with the current continuation cc initialized from the ``code`` slice and
    the ``stack`` of values.

    Optional parameters:
     - capabilities: int
     - c4: Cell
     - c7: list
     - gas_limit: int
     - gas_credit: int
     - gas_limit_max: int
     - gas_price: int
     - trace: bool
     - libs: list

    Returns VmResult.    
    """
    cc = Continuation(
        ContinuationType.create_ordinary(),
        code,
        stack,
        SaveList(),
        -1
    )

    regs = SaveList()
    capabilities = 0
    trace = False
    gas_limit = 1_000_000_000
    gas_credit = 10_000
    gas_limit_max = 1_000_000_000
    gas_price = 10
    libs = []
    for key, value in kwargs.items():
        if key == "capabilities":
            capabilities = int(value)
        elif key == "trace":
            trace = bool(value)
        elif key == "c4":
            regs.put(4, value)
        elif key == "c7":
            regs.put(7, value)
        elif key == "gas_limit":
            gas_limit = int(value)
        elif key == "gas_credit":
            gas_credit = int(value)
        elif key == "gas_limit_max":
            gas_limit_max = int(value)
        elif key == "gas_price":
            gas_price = int(value)
        elif key == "libs":
            libs = value
        else:
            raise Exception("Unknown parameter {}".format(key))

    state = VmState(cc, regs, Gas(gas_limit, gas_credit, gas_limit_max, gas_price))
    return runvm_generic(state, capabilities, trace, libs)

class ExceptionCode(Enum):
    """TVM exception code."""
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

def load_keypair(filename: str) -> Tuple[bytes, bytes]:
    """Loads private key from a file"""
    print(f"Loading private key from file {filename}")
    with open(filename, "rb") as file:
        secret = file.read()
        public = ed25519_secret_to_public(secret)
        return public, secret

class StateInit:
    split_depth: Optional[int]
    tick: bool
    tock: bool
    code: Optional[Cell]
    data: Optional[Cell]
    library: Optional[Dictionary]

    def __init__(
            self,
            split_depth: Optional[int] = None,
            tick: bool = False,
            tock: bool = False,
            code: Optional[Cell] = None,
            data: Optional[Cell] = None,
            library: Optional[Dictionary] = None):
        self.split_depth = split_depth
        self.tick = tick
        self.tock = tock
        self.code = code
        self.data = data
        self.library = library

    def deserialize(self, s: Slice):
        """Deserializes StateInit from the ``s`` slice."""
        if s.u(1):
            self.split_depth = s.u(5)
        if s.u(1):
            self.tick = bool(s.u(1))
            self.tock = bool(s.u(1))
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
        """Serializes StateInit into Builder."""
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
            b.i(1, 1).b(self.library.serialize())
        return b

class Currency:
    FACTOR = 1000000000
    value: int

    def __init__(self, value: int = 0):
        if value < 0 or value.bit_length() > 128:
            raise Exception("Currency value must be non-negative and fit into 128 bits")
        self.value = value

    @classmethod
    def from_str(cls, value: str):
        """Constructs a Currency object from a rational number represented by the ``value`` string."""
        return Currency(int(Fraction(value) * Currency.FACTOR))

    def deserialize(self, s: Slice):
        """Deserializes Currency from the ``s`` slice."""
        len = s.u(4)
        if len == 0:
            self.value = 0
        else:
            self.value = s.u(len * 8)
        return self

    def serialize(self) -> Builder:
        """Serializes Currency into Builder."""
        if self.value == 0:
            return Builder().i(4, 0)
        len = (self.value.bit_length() + 7) >> 3
        assert(len < 16)
        return Builder().i(4, len).i(len * 8, self.value)

    def __str__(self) -> str:
        return str(float(Fraction(self.value) / self.FACTOR))
