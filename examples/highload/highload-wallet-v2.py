import sys
import time
import argparse
from ever_playground import Builder, Cell, Currency, Dictionary, Slice, \
    parse_smc_addr, load_address, load_keypair, ed25519_sign

def abort(message: str):
    raise Exception(message)

mode_default = 3
timeout_default = 60

argparser = argparse.ArgumentParser(prog = sys.argv[0], description =
    "Creates a request with up to 254 orders loaded from <order-file> to high-load (sub)wallet created by new-highload-v2-wallet.fif, with private key loaded from file <filename-base>.pk "
    "and address from <filename-base><subwallet-id>.addr, and saves it into <savefile>.boc ('wallet-query.boc' by default) "
    "<order-file> is a text file with lines `SEND <dest-addr> <amount>`")
argparser.add_argument("filename_base", help = "prefix for input file names")
argparser.add_argument("subwallet_id", type = int, help = "subwallet id")
argparser.add_argument("order_file", help = "name of file with a list of orders")
argparser.add_argument("--savefile", default = "wallet-query", help = "output file name w/o extension")
argparser.add_argument("-n", "--no-bounce", action = "store_false", help = "clears bounce flag")
argparser.add_argument("-b", "--force-bounce", action = "store_true", help = "forces bounce flag")
argparser.add_argument("-t", "--timeout", type = int, action = "store", default = timeout_default,
    help = f"sets expiration timeout in seconds ({timeout_default} by default)")
argparser.add_argument("-m", "--mode", type = int, action = "store", default = mode_default,
    help = f"sets transfer mode (0..255) for SENDRAWMSG ({mode_default} by default)")
args = argparser.parse_args()

file_base: str = args.filename_base
subwallet_id: int = args.subwallet_id
if subwallet_id.bit_length() > 32:
    argparser.print_help()
    exit(1)
order_file: str = args.order_file
savefile: str = args.savefile
allow_bounce: bool = args.no_bounce
force_bounce: bool = args.force_bounce
timeout: int = args.timeout
send_mode: int = args.mode

wallet_wc, wallet_addr = load_address(file_base + str(subwallet_id) + ".addr")
print(f"Source wallet address = {wallet_wc}:{wallet_addr:064x}")

_, wallet_pk = load_keypair(file_base + ".pk")

orders = Dictionary(16)
order_number = 0

def add_order(order: Slice):
    global orders, order_number
    if order_number > 254:
        abort("more that 254 orders")
    key = Slice(Builder().i(16, order_number).finalize())
    if orders.get(key) != None:
        abort("cannot add order to dictionary")
    orders.add(key, order)
    order_number += 1

def append_msg_body(b: Builder, body: Cell):
    body_slice = Slice(body)
    if b.fits(body_slice, 1, 0):
        b.i(1, 0).s(body_slice)
    else:
        b.i(1, 1).r(body)

def create_int_msg(body: Cell, bounce: bool, wc: int, addr: int, ng: Currency) -> Cell:
    b = Builder().ib("01").i(1, bounce).ib("000100").i(8, wc).i(256, addr) \
        .b(ng.serialize()).i(9 + 64 + 32 + 1, 0)
    append_msg_body(b, body)
    return b.finalize()

def create_simple_transfer(address: str, ng: Currency, bounce: bool) -> Cell:
    wc, addr = parse_smc_addr(address)
    bounce = bounce or force_bounce and allow_bounce
    print(f"Transferring {ng} to account {wc}:{addr:064x} bounce={bounce}")
    return create_int_msg(Builder().i(32, 0).finalize(), bounce, wc, addr, ng)

def create_order(c: Cell, send_mode: int) -> Cell:
    return Builder().i(8, send_mode).r(c).finalize()

def send(address: str, ng: Currency, bounce: bool):
    t = create_simple_transfer(address, ng, bounce)
    order = create_order(t, send_mode)
    add_order(Slice(order))

with open(order_file, "r") as file:
    for line in file:
        chunks = line.split(" ")
        assert(len(chunks) == 4)
        assert(chunks[0] == "SEND")
        address = chunks[1]
        bounce = bool(chunks[2])
        ng = Currency.from_str(chunks[3])
        send(address, ng, bounce)

now = 1684770872 # int(time.time())
orders_cell = orders.serialize().finalize()
query_id = ((now + timeout) << 32) + (orders_cell.repr_hash() & 0xffffffff)

signing_message = Builder().i(32, subwallet_id).i(64, query_id).s(Slice(orders_cell)).finalize()
print(f"signing message: {signing_message}")

signature = ed25519_sign(signing_message.repr_hash().to_bytes(32, "big"), wallet_pk)
ext = Builder().ib("1000100").i(8, wallet_wc).i(256, wallet_addr).b(Currency(0).serialize()) \
    .ib("00").y(signature).s(Slice(signing_message)).finalize()
print(f"resulting external message: {ext}")
ext_bytes = ext.write(2)
print(f"{ext_bytes.hex()}")
print(f"query_id is {query_id} = 0x{query_id:x}")
open(savefile + ".boc", "wb").write(ext_bytes)
print(f"(Saved to file {savefile}.boc)")
