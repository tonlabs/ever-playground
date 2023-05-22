class Cell:
    """
    A TVM cell consists of at most 1023 bits of data, and of at
    most four references to other cells. All persistent data (including TVM
    code) in the TON Blockchain is represented as a collection of TVM
    cells.
    """

    def write(self, flags: int) -> bytes:
        """
        Writes the Cell to a boc bytestream.

        Bits of the flags parameter have the following effect:
        - +1 enables bag-of-cells index creation (useful for lazy deserialization of large bags of cells).
        - +2 includes the CRC32-C of all data into the serialization (useful for checking data integrity).
        """

    @staticmethod
    def read(bytes: bytes) -> Cell:
        """
        Reads a Cell from a boc bytestream.
        """

    def repr_hash(self) -> int:
        """
        Returns representation hash of the Cell.
        """

class Slice:
    """
    A TVM cell slice, or slice for short, is a contiguous “sub-cell”
    of an existing cell, containing some of its bits of data and some of its
    references. Essentially, a slice is a read-only view for a subcell of a cell.
    Slices are used for unpacking data previously stored (or serialized) in a
    cell or a tree of cells.
    """

    def __init__(self, cell: Cell) -> Slice: ...

    def i(self, bits: int) -> int:
        """
        Reads a signed integer out from the Slice and shifts internal data pointer.
        """

    def u(self, bits: int) -> int:
        """
        Reads an unsigned integer out from the Slice and shifts internal data pointer.
        """

    def refs(self) -> int:
        """
        Returns remaining references count.
        """

    def r(self) -> Cell:
        """
        Reads a Cell out from the Slice and shifts internal refs pointer.
        """

    def is_empty(self) -> bool:
        """
        Returns whether the Slice data is empty.
        """

class Builder:
    """
    A TVM cell builder, or builder for short, is an “incomplete”
    cell that supports fast operations of appending bitstrings and cell references
    at its end. Builders are used for packing (or serializing) data
    from the top of the stack into new cells (e.g., before transferring them
    to persistent storage).
    """

    def s(self, slice: Slice) -> Builder:
        """
        Appends a Builder with a Slice.
        """

    def b(self, builder: Builder) -> Builder:
        """
        Appends a Builder with another Builder.
        """

    def i(self, bits: int, integer: int) -> Builder:
        """
        Appends a Builder with an integer of specified length.
        """

    def ib(self, bin: str) -> Builder:
        """
        Appends a Builder with an integer from binary string.
        """

    def x(self, bitstring: str) -> Builder:
        """
        Appends a Builder with a bitstring.

        TODO describe what TVM bitstring is
        """

    def y(self, data: bytes) -> Builder:
        """
        Appends a Builder with bytes.
        """

    def r(self, cell: Cell) -> Builder:
        """
        Appends a Builder with a Cell.
        """

    def fits(self, slice: Slice, extra_bits: int, extra_refs: int) -> bool:
        """
        TODO
        """

    def finalize(self) -> Cell:
        """
        Converts a Builder into an ordinary Cell.
        """

    def slice(self) -> Slice:
        """
        Converts a Builder into a Slice.

        This is a shortcut for doing Builder.finalize().slice()
        """

class Dictionary:
    """
    Hashmaps, or dictionaries, are a specific data structure represented by a tree
    of cells. Essentially, a hashmap represents a map from keys, which are bitstrings
    of either fixed or variable length, into values of an arbitrary type X,
    in such a way that fast lookups and modifications be possible.
    """

    def __init__(self, bit_len: int) -> None: ...

    def get(self, key: Slice) -> Slice:
        """
        Searches for a given key and returns corresponding value. None is returned when key is not found.
        """

    def add(self, key: Slice, value: Slice) -> Dictionary:
        """
        TODO
        """

    def add_kv_slice(self, key_len: int, slice: Slice) -> Dictionary:
        """
        Adds a new key-value pair from the slice. The first key_len data bits are used as a key,
        and all the rest as a value.
        """

    def cell(self) -> Cell:
        """
        Returns underlying cell.
        """

    def serialize(self) -> Builder:
        """
        Serializes a Dictionary into a Builder as defined in the TL-B scheme of HashmapE.
        """

    def deserialize(self, slice: Slice) -> Dictionary:
        """
        Deserializes a Dictionary from a Slice.
        """

class NaN:
    """
    Opaque type representing a special case of the TVM Integer type.
    """

class Continuation:
    """
    Opaque type representing Contination value on the output stack of TVM invocation.
    """

def runvm(code: Slice, stack: list, **kwargs) -> VmResult:
    """
    Invokes a new instance of TVM with the current continuation cc initialized from Slice code.
    A stack of values is passed to the instance before execution.

    Optional parameters:
     - capabilities: int
     - c4: Cell
     - c7: list
     - gas_limit: int
     - gas_credit: int
     - trace: bool
    """

class VmResult:
    stack: list
    exit_code: int
    exception_value: object
    steps: int
    gas_used: int

def assemble(code: str) -> Cell:
    """
    Translates a code string in assembler language to a Cell of TVM bytecode.
    """

from typing import Tuple

def ed25519_new_keypair() -> Tuple[bytes, bytes]:
    """
    """

def ed25519_secret_to_public(secret: bytes) -> bytes:
    """
    """

def ed25519_sign(data: bytes, secret: bytes) -> bytes:
    """
    """

def ed25519_check_signature(data: bytes, signature: bytes, public: bytes) -> bool:
    """
    """
