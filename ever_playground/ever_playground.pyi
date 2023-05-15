class Cell:
    """
    A TVM cell consists of at most 1023 bits of data, and of at
    most four references to other cells. All persistent data (including TVM
    code) in the TON Blockchain is represented as a collection of TVM
    cells.
    """

    def write(self) -> bytes:
        """
        Writes the Cell to a boc bytestream.
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
        Reads out a signed integer from the Slice and shifts internal pointer.
        """

    def u(self, bits: int) -> int:
        """
        Reads out an unsigned integer from the Slice and shifts internal pointer.
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

    def i(self, bits: int, integer: int) -> Builder:
        """
        Appends a Builder with an integer of specified length.
        """

    def serialize(self) -> Cell:
        """
        Converts a Builder into an ordinary Cell.
        """

    def slice(self) -> Slice:
        """
        Converts a Builder into a Slice.

        This is a shortcut for doing Builder.serialize().slice()
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

    def add_kv_slice(self, key_len: int, slice: Slice) -> Dictionary:
        """
        Adds a new key-value pair from the slice. The first key_len data bits are used as a key,
        and all the rest as a value.
        """

    def serialize(self) -> Cell:
        """
        Serializes a dictionary into a tree of cells as defined in the TL-B scheme of HashmapE.
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