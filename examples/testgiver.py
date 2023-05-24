# #!/usr/bin/fift -s
# "TonUtil.fif" include

import sys
from ever_playground import Builder as B, Slice as S, Currency, parse_smc_addr, parse_load_address

# { ."usage: " @' $0 type ." <dest-addr> <seqno> <amount> [<savefile>]" cr
#   ."Creates a request to TestGiver and saves it into <savefile>.boc" cr
#   ."('testgiver-query.boc' by default)" cr 1 halt
# } : usage
def usage():
    print(f"usage: {sys.argv[0]} <dest-addr> <seqno> <amount> [<savefile>]")
    print("Creates a request to TestGiver and saves it into <savefile>.boc")
    print("('testgiver-query.boc' by default)")
    exit(1)

# $# 3 - -2 and ' usage if
argc = len(sys.argv) - 1
if not (3 <= argc and argc <= 4):
    usage()

# // "testgiver.addr" load-address 
# Masterchain 0xfcb91a3a3816d0f7b8c2c76108b8a9bc5a6b7a55bd79f8ab101c52db29232260
# 2constant giver_addr
#  ."Test giver address = " giver_addr 2dup .addr cr 6 .Addr cr
giver_address = "-1:fcb91a3a3816d0f7b8c2c76108b8a9bc5a6b7a55bd79f8ab101c52db29232260"
giver_wc, giver_addr = parse_smc_addr(giver_address)
print(f"Test giver address = {giver_address}")

# $1 true parse-load-address =: bounce 2=: dest_addr
# $2 parse-int =: seqno
# $3 $>GR =: amount
# def? $4 { @' $4 } { "testgiver-query" } cond constant savefile
dest_address = sys.argv[1]
dest_wc, dest_addr = parse_load_address(dest_address)
bounce = True # TODO?
seqno = int(sys.argv[2])
amount = Currency.from_str(sys.argv[3])
savefile = "testgiver-query"
if argc > 3:
    savefile = sys.argv[4]

# ."Requesting " amount .GR ."to account "
# dest_addr 2dup bounce 7 + .Addr ." = " .addr
# ."seqno=0x" seqno x. ."bounce=" bounce . cr
print(f"Requesting {amount} to account {dest_address} seqno {hex(seqno)} bounce {bounce}")

# // create a message (NB: 01b00.., b = bounce)
# <b b{01} s, bounce 1 i, b{000100} s, dest_addr addr, 
#    amount Gram, 0 9 64 32 + + 1+ 1+ u, 0 32 u, "GIFT" $, b>
# <b seqno 32 u, 1 8 u, swap ref, b>
# dup ."enveloping message: " <s csr. cr
hint = bytes("GIFT", "utf8")
c1 = B().ib("01").i(1, bounce).ib("000100").i(8, dest_wc).i(256, dest_addr) \
    .b(amount.serialize()).i(9 + 64 + 32 + 1 + 1, 0).i(32, 0).y(hint) \
    .finalize()
message = B().i(32, seqno).i(8, 1).r(c1).finalize()
print(f"enveloping message: {message}")

# <b b{1000100} s, giver_addr addr, 0 Gram, b{00} s,
#    swap <s s, b>
# dup ."resulting external message: " <s csr. cr
# 2 boc+>B dup Bx. cr
# savefile +".boc" tuck B>file
# ."(Saved to file " type .")" cr
ext_message = B().ib("1000100").i(8, giver_wc).i(256, giver_addr) \
    .b(Currency(0).serialize()).ib("00").s(S(message)).finalize()
print(f"resulting external message: {ext_message}")
ext_message_bytes = ext_message.write(2) # include crc32
print(ext_message_bytes.hex())

output_filename = savefile + ".boc"
open(output_filename, "wb").write(ext_message_bytes)
print(f"(Saved to file {output_filename})")
