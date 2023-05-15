from ever_playground import Cell as C
from ever_playground import Builder as B
from ever_playground import Slice as S
from ever_playground import Dictionary as D
from ever_playground import StateInit, runvm, assemble, parse_smc_addr

b = B()
b.i(8, 0x12).i(8, 0x34)
s = S(b.finalize())
assert(s.u(16) == 0x1234)

val1 = -123
val2 = 0xdeadbeefcafebabe
s = B().i(32, val1).i(64, val2).slice()
assert(s.i(32) == val1)
assert(not s.is_empty())
assert(s.u(64) == val2)
assert(s.is_empty())

val3 = 0xffffffff
s = S(B().i(32, val3).finalize())
assert(s.i(23) == -1)
assert(len(s) == 9)

d1_wc, d1_addr = parse_smc_addr("0:000169b042c37962027e58de0dbaa0b85f5d032f37d8333e3cdfdcc7918ae00a")
d2_wc, d2_addr = parse_smc_addr("0:bc43df2056abee4c1a443fbfcfede0ba90d214c77322167fc08ce48920c17c1b")
d3_wc, d3_addr = parse_smc_addr("0:d4a50c1a849a4742214e751977af268269e6eeae064ce800634acea241d430d3")

s1 = B().i(32, d1_wc).i(256, d1_addr).slice()
s2 = B().i(32, d2_wc).i(256, d2_addr).slice()
# s3 = B().i(32, d3_wc).i(256, d3_addr).slice()
b3 = B()
b3.i(32, d3_wc)
b3.i(256, d3_addr)
s3 = b3.slice()

dict = D(288)
dict.add_kv_slice(288, s1)
dict = dict.add_kv_slice(288, s2)
dict.add_kv_slice(288, s3)
#dict = D(288).add_kv_slice(288, s1).add_kv_slice(288, s2).add_kv_slice(288, s3)

assert(dict.get(s1) == S(B().finalize()))
assert(dict.get(B().i(288, 0).slice()) == None)

dict_cell1 = dict.serialize().finalize()
#print(dict_cell1)

dict = D.deserialize(288, S(dict_cell1))

empty = C("")
assert(empty == B().finalize())
assert(empty.repr_hash() == 0x96a296d224f285c67bee93c30f8a309157f0daa35dc5b87e410b78630a09cfc7)

c = \
C("c_",
    C("c20",
        C("bfc000b4d82161bcb1013f2c6f06dd505c2fae81979bec199f1e6fee63c8c570054_"),
        C("2_",
            C("bfbc43df2056abee4c1a443fbfcfede0ba90d214c77322167fc08ce48920c17c1b"),
            C("bf94a50c1a849a4742214e751977af268269e6eeae064ce800634acea241d430d3"))))
assert(dict_cell1 == c)

dict_bytes = dict_cell1.write()
dict_bytes = bytes(dict_cell1)
dict_cell2 = C.read(dict_bytes)
#print(dict_cell2)

assert(dict_cell1 == dict_cell2)

#open("test.boc", "wb").write(dict_cell.write())
#cell = C.read(open("test.boc", "rb").read())

add = assemble("""
    ADD
""")
res = runvm(S(add), [10, 20], capabilities = 0x1)
assert(res.stack == [30])

throw = assemble("THROW 100")
res = runvm(S(throw), [10])
assert(res.exit_code == 100)
assert(res.exception_value == 0)
assert(res.stack == [10])

sib = StateInit(code = throw).serialize()
#print(sib)
sic = \
C("24_",
    C("f2c064"))
assert(sib.finalize() == sic)
#open("throw.tvc", "wb").write(bytes(sib.finalize()))

si = StateInit().deserialize(S(sib.finalize()))
assert(si.code == throw)

throwargany = assemble("NEWC ENDC PUSHINT 100 THROWARGANY")
res = runvm(S(throwargany), [])
assert(res.exit_code == 100)
assert(res.exception_value == empty)
assert(res.stack == [])

ctrls_ex = assemble("PUSHCTR c4")
abc = C("abc")
res = runvm(S(ctrls_ex), [], c4 = abc)
assert(res.stack == [abc])

iters = 211111
chksignu_loop = assemble(f"""
    PUSHINT 0x8de120e0abffc55bf3fc723dee9e6d6bc01716064312a4e4be58be4e193fda8d
    PUSHSLICE xedf0554ee6f844bb7b08c91771d44c30dd69cc5b192ca2d8beff2e38b34f3d8f3c6e76b8c37c2a2fa3ea0bf082a128e2ae4c5befd941160ffcf4aed9e0d8f905
    PUSHINT 0xf5ec1345ad9adf191db35cdece12482e19a3a218e12f2d6c3e26e0ec6463d0a5

    PUSHINT {iters}
    PUSHCONT {{
        BLKPUSH 3, 2
        BLKDROP 2 ;; CHKSIGNU
        DROP
    }}
    REPEAT
""")

from ever_playground import ExceptionCode
res = runvm(S(chksignu_loop), [], gas_limit = 100000)
assert(res.exit_code == ExceptionCode.OutOfGas.value) # out of gas

#open("chksignu-loop.boc", "wb").write(bytes(chksignu_loop))

import time

print("running loop")
t = time.time()
res = runvm(S(chksignu_loop), [])
elapsed = time.time() - t

assert(res.exit_code == 0)
assert(res.steps == 844452)
assert(res.gas_used == 15833573)

print("total time {:.2f}s".format(elapsed))
print("one iteration takes {:.2f}us".format(elapsed * 1000000 / iters))
