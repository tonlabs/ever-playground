from typing import Optional, Tuple

class Cell:
    """
    A TVM cell consists of at most 1023 bits of data, and of at
    most four references to other cells. All persistent data (including TVM
    code) in the TON Blockchain is represented as a collection of TVM
    cells.
    """
    def __init__(self, *args) -> None: ...

    @staticmethod
    def empty() -> Cell:
        """
        Constructs empty cell.
        """

    def write(self, flags: int) -> bytes:
        """
        Writes the cell to boc bytes.

        Bits of the ``flags`` parameter have the following effect:
        - +1 enables bag-of-cells index creation (useful for lazy deserialization of large bags of cells).
        - +2 includes the CRC32-C of all data into the serialization (useful for checking data integrity).
        """

    @staticmethod
    def read(bytes: bytes) -> Cell:
        """
        Reads a Cell from the boc ``bytes``.
        """

    def repr_hash(self) -> int:
        """
        Returns the representation hash of the cell.
        """

    def repr_depth(self) -> int:
        """
        Returns the representation depth of the cell.
        """

    def level(self) -> int:
        """
        Returns level of the cell.
        """

    def depth(self, index: int) -> int:
        """
        Returns depth of the cell.
        """

    def cells_count(self) -> int:
        """
        Returns the total cells count.
        """

    def unique_cells_count(self) -> int:
        """
        Returns the unique cells count.
        """

class Slice:
    """
    A TVM cell slice, or slice for short, is a contiguous “sub-cell”
    of an existing cell, containing some of its bits of data and some of its
    references. Essentially, a slice is a read-only view for a subcell of a cell.
    Slices are used for unpacking data previously stored (or serialized) in a
    cell or a tree of cells.
    """

    def __init__(self, cell: Cell) -> None: ...

    def i(self, bits: int) -> int:
        """
        Reads a signed integer of bit length ``bits`` and advances the internal data pointer.
        """

    def u(self, bits: int) -> int:
        """
        Reads an unsigned integer of bit length ``bits`` and advances the internal data pointer.
        """

    def refs(self) -> int:
        """
        Returns the remaining children cells (aka references) count.
        """

    def r(self) -> Cell:
        """
        Reads the next children cell (aka reference) and advances the internal refs pointer.
        """

    def is_empty(self) -> bool:
        """
        Returns whether the data of the slice is empty.
        """

    def remaining_bits(self) -> int:
        """
        Returns the number of remaining bits of the slice.
        """

    def skip(self, bits: int):
        """
        Skips a number of bits.
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
        Appends Builder with ``slice``.
        """

    def b(self, builder: Builder) -> Builder:
        """
        Appends Builder with another ``builder``.
        """

    def i(self, bits: int, integer: int) -> Builder:
        """
        Appends Builder with ``integer`` of the ``bits`` length.
        """

    def ib(self, binstring: str) -> Builder:
        """
        Appends Builder with an integer from the binary string ``bin``.
        """

    def x(self, bitstring: str) -> Builder:
        """
        Appends Builder with ``bitstring``.

        Bitstrings provide a way to represent a sequence of bits as a hexadecimal string.
        If the sequence has the bit length multiple of 4, then the hexadecimal string
        contains just length/4 count of hexadecimal digits. Otherwise, the representation
        uses a completion tag ``_`` in the end of the hexstring, which means that
        the rightmost ``0`` bits and the first ``1`` bit are trimmed. For more details,
        see chapter 1.0 of the TVM whitepaper.
        """

    def y(self, data: bytes) -> Builder:
        """
        Appends Builder with the ``data`` bytes.
        """

    def r(self, cell: Cell) -> Builder:
        """
        Appends Builder with ``cell``.
        """

    def fits(self, slice: Slice, extra_bits: int, extra_refs: int) -> bool:
        """
        Checks whether Builder can be appended with ``slice``, some extra data of the
        ``extra_bits`` length, and some extra children cells ``extra_refs``. 
        """

    def finalize(self) -> Cell:
        """
        Converts (finalizes) Builder into an ordinary Cell.
        """

    def slice(self) -> Slice:
        """
        Converts Builder into Slice.

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

    def get(self, key: Slice) -> Optional[Slice]:
        """
        Gets a value for the given ``key``.
        """

    def add(self, key: Slice, value: Slice) -> Dictionary:
        """
        Sets ``value`` for the given ``key``.
        """

    def add_ref(self, key: Slice, value: Cell) -> Dictionary:
        """
        Sets ``value`` for the given ``key`` as a cell reference.
        """

    def add_kv_slice(self, key_len: int, slice: Slice) -> Dictionary:
        """
        Adds a new key-value pair from ``slice``. The first ``key_len`` data bits are used as a key,
        and all the rest as a value.
        """

    def cell(self) -> Cell:
        """
        Returns underlying cell.
        """

    def serialize(self) -> Builder:
        """
        Serializes Dictionary into Builder as defined in the TL-B scheme of HashmapE.
        """

    @staticmethod
    def deserialize(bits: int, slice: Slice) -> Dictionary:
        """
        Deserializes Dictionary from ``slice`` with the ``bits`` key length.
        """

class NaN:
    """
    NaN is a special case of the TVM Integer type.
    """
    def __init__(self) -> None: ...

class Gas:
    limit: int
    used: int
    credit: int

    def __init__(self, limit: int, credit: int, gas_limit_max: int, gas_price: int) -> None: ...

class ContinuationType:
    """
    Represents the type of TVM Continuation.
    """
    variant: int

    def params_again(self) -> Slice:
        """Returns parameters of Again continuation type."""
    def params_pushint(self) -> int:
        """Returns parameters of PushInt continuation type."""
    def params_quit(self) -> int:
        """Returns parameters of Quit continuation type."""
    def params_repeat(self) -> Tuple[Slice, int]:
        """Returns parameters of Repeat continuation type."""
    def params_until(self) -> Slice:
        """Returns parameters of Until continuation type."""
    def params_while(self) -> Tuple[Slice, Slice]:
        """Returns parameters of While continuation type."""

    @staticmethod
    def create_again(body: Slice) -> ContinuationType:
        """Creates Again continuation type."""
    @staticmethod
    def create_trycatch() -> ContinuationType:
        """Creates TryCatch continuation type."""
    @staticmethod
    def create_ordinary() -> ContinuationType:
        """Creates Ordinary continuation type."""
    @staticmethod
    def create_pushint(value: int) -> ContinuationType:
        """Creates PushInt continuation type."""
    @staticmethod
    def create_quit(exit_code: int) -> ContinuationType:
        """Creates Quit continuation type."""
    @staticmethod
    def create_repeat(body: Slice, counter: int) -> ContinuationType:
        """Creates Repeat continuation type."""
    @staticmethod
    def create_until(body: Slice) -> ContinuationType:
        """Creates Until continuation type."""
    @staticmethod
    def create_while(body: Slice, cond: Slice) -> ContinuationType:
        """Creates While continuation type."""
    @staticmethod
    def create_excquit() -> ContinuationType:
        """Creates ExcQuit continuation type."""

class SaveList:
    """
    SaveList contains the values of control registers to be restored before the execution of the code.
    """
    def __init__(self) -> None: ...
    def get(self, index: int) -> object:
        """Gets the register value at the specified ``index``."""
    def put(self, index: int, value: object) -> None:
        """Puts ``value`` into the register at ``index``."""

class Continuation:
    """
    Represents an "execution token" for TVM, which may be invoked (executed) later. As such,
    it generalizes function addresses (i.e., function pointers and references), subroutine
    return addresses, instruction pointer addresses, exception handler addresses, closures,
    partial applications, anonymous functions, and so on.
    """
    typ: ContinuationType
    code: Slice
    stack: list[object]
    savelist: SaveList
    nargs: int

    def __init__(
        self,
        typ: ContinuationType = ContinuationType.create_ordinary(),
        code: Slice = Slice(Cell.empty()),
        stack: list[object] = [],
        savelist: SaveList = SaveList(),
        nargs: int = -1
    ) -> None: ...

class VmState:
    """
    State of the VM consists of:
     - cc: current continuation,
     - regs: register file of c0-c5 and c7,
     - steps: a number of steps done by VM so far,
     - gas: parameters of the gas including gas used,
     - committed_c4/c5: 
    """
    cc: Continuation
    regs: SaveList
    steps: int
    gas: Gas
    committed_c4: Optional[Cell]
    committed_c5: Optional[Cell]

    def __init__(self, cc: Continuation, regs: SaveList, gas: Gas) -> None: ...

class VmResult:
    """Result of TVM execution."""
    state: VmState
    exit_code: int
    exception_value: object

def runvm_generic(state: VmState, capabilities: int = 0, trace: bool = False, libs: list = []) -> VmResult:
    """Generic version of the runvm() function."""

def assemble(code: str) -> Cell:
    """
    Translates the ``code`` string in assembler language to a Cell of TVM bytecode.
    """

def ed25519_new_keypair() -> Tuple[bytes, bytes]:
    """
    Generates a new Ed25519 private/public key pair, and returns both the private key
    and the public key as 32-byte values.

    Example:
    ```
        secret, public = ed25519_new_keypair()
    ```
    """

def ed25519_secret_to_public(secret: bytes) -> bytes:
    """
    Computes the public key corresponding to the private Ed25519 key ``secret``.
    """

def ed25519_sign(data: bytes, secret: bytes) -> bytes:
    """
    Signs ``data`` with the Ed25519 private key ``secret`` (a 32-byte value) and returns the signature as a 64-byte value.
    """

def ed25519_check_signature(data: bytes, signature: bytes, public: bytes) -> bool:
    """
    Checks whether ``signature`` is a valid Ed25519 signature of ``data`` with the public key ``public``.
    """
