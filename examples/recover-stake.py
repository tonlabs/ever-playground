# #!/usr/bin/fift -s
# "TonUtil.fif" include

import sys
import time

from ever_playground import Builder as B

# { ."usage: " @' $0 type ." [<savefile>]" cr
#   ."Creates the message body to be sent from a validator controlling smart contract (wallet) to recover its share of unfrozen stakes and bonuses." cr
#   ."The result is saved into <savefile> (`recover-query.boc` by default) and output in hexadecimal form, to be sent later as the body of a message from the wallet to elections smart contract, along with a small value (say, one Gram) to cover forwarding and processing fees" cr 1 halt
# } : usage

def usage():
    print("Usage: {} [<savefile>]".format(sys.argv[0]))
    print("Creates the message body to be sent from a validator controlling smart contract (wallet) to recover its share of unfrozen stakes and bonuses.")
    print("The result is saved into <savefile> (`recover-query.boc` by default) and output in hexadecimal form, to be sent later as the body of a message from the wallet to elections smart contract, along with a small value (say, one Gram) to cover forwarding and processing fees")
    exit(1)

# $# dup 0 < swap 1 > or ' usage if
argc = len(sys.argv) - 1
if argc > 1:
    usage()

# def? $1 { @' $1 } { "recover-query.boc" } cond constant output_fname
output_filename = "recover-query.boc"
if argc > 0:
    output_filename = sys.argv[1]

# now constant query_id
query_id = 1684770872 # int(time.time())

# ."query_id for stake recovery message is set to " query_id . cr
print(f"query_id for stake recovery message is set to {query_id}")

# <b x{47657424} s, query_id 64 u, b>
# cr ."Message body is " dup <s csr. cr
body = B().x("47657424").i(64, query_id).finalize()
print(f"Message body is {body}")

# 2 boc+>B output_fname tuck B>file ."Saved to file " type cr
open(output_filename, "wb").write(body.write(2))
print(f"Saved to file {output_filename}")
