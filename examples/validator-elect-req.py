# #!/usr/bin/fift -s
# "TonUtil.fif" include

import sys
from base64 import b64encode
from fractions import Fraction

from ever_playground import parse_load_address, parse_adnl_address

def abort(message: str):
    raise Exception(message)

# { ."usage: " @' $0 type ." <wallet-addr> <elect-utime> <max-factor> <adnl-addr> [<savefile>]" cr
#   ."Creates a request to participate in validator elections starting at <elect-utime> on behalf of smart-contract with address <wallet-addr> (prefix with '@' to load address from file) and hexadecimal adnl address <adnl-addr> (empty string or '0' for none)." cr
#   ."The result is saved into <savefile> and output in hexadecimal form, to be signed later by the validator public key" cr 1 halt
# } : usage
def usage():
    print("Usage: {} <wallet-addr> <elect-utime> <max-factor> <adnl-addr> [<savefile>]".format(sys.argv[0]))
    print("Creates a request to participate in validator elections starting at <elect-utime> on behalf of smart-contract with address <wallet-addr> (prefix with '@' to load address from file) and hexadecimal adnl address <adnl-addr> (empty string or '0' for none).")
    print("The result is saved into <savefile> and output in hexadecimal form, to be signed later by the validator public key")
    exit(1)

# $# dup 3 < swap 5 > or ' usage if
argc = len(sys.argv) - 1
if not (4 <= argc and argc <= 5):
    usage()

# $1 true parse-load-address drop swap 1+ abort"only masterchain smartcontracts may participate in validator elections"
# constant src_addr
src_wc, src_addr = parse_load_address(sys.argv[1])
if src_wc != -1:
    abort("only masterchain smartcontracts may participate in validator elections")

# $2 (number) 1 <> { 0 } if dup 0<= abort"<elect-utime> must be a positive integer"
# constant elect_time
elect_time = int(sys.argv[2])
if elect_time < 0:
    abort("<elect-utime> must be a positive integer")

# $3 (number) dup 0= abort"<max-factor> must be a real number 1..100"
# 1 = { 16 << } { 16 <</r } cond
# dup 65536 < over 6553600 > or abort"<max-factor> must be a real number 1..100"
# constant max_factor
max_factor = int(Fraction(sys.argv[3]) * 2 ** 16)
if not (65536 <= max_factor and max_factor <= 6553600):
    abort("<max-factor> must be a real number 1..100")

# def? $4 { @' $4 dup $len 1 > { parse-adnl-address } { drop 0 } cond } ' 0 cond
# constant adnl_addr
adnl_addr = parse_adnl_address(sys.argv[4])

# def? $5 { @' $5 } { "validator-to-sign.bin" } cond constant output_fname
output_filename = "validator-to-sign.bin"
if argc > 4:
    output_filename = sys.argv[5]

# ."Creating a request to participate in validator elections at time " elect_time .
# ."from smart contract " -1 src_addr 2dup 1 .Addr ." = " .addr
# ." with maximal stake factor with respect to the minimal stake " max_factor ._
# ."/65536 and validator ADNL address " adnl_addr 64x. cr
print(f"Creating a request to participate in validator elections at time {elect_time} "
    f"from smart contract -1:{src_addr:064x} "
    f"with maximal stake factor with respect to the minimal stake {max_factor}"
    f"/65536 and validator ADNL address {adnl_addr:064x}")

# B{654c5074} elect_time 32 u>B B+ max_factor 32 u>B B+ src_addr 256 u>B B+ adnl_addr 256 u>B B+
def bb(len: int, v: int):
    return v.to_bytes(len, "big")

b = bb(4, 0x654c5074) + bb(4, elect_time) + bb(4, max_factor) + bb(32, src_addr) + bb(32, adnl_addr)

# dup Bx. cr
print(b.hex())
# dup B>base64url type cr
print(b64encode(b).decode())

# output_fname tuck B>file ."Saved to file " type cr
open(output_filename, "wb").write(b)
print(f"Saved to file {output_filename}")
