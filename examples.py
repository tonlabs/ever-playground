import time

from ever_playground import Cell as C
from ever_playground import Builder as B
from ever_playground import Slice as S
from ever_playground import Dictionary as D
from ever_playground import ExceptionCode
from ever_playground import StateInit, runvm, assemble, parse_smc_addr

def expect(expected, v):
    if not expected == v:
        raise Exception("{} != {}".format(expected, v))

b = B()
b.i(8, 0x12).i(8, 0x34)
s = S(b.finalize())
expect(0x1234, s.u(16))

val1 = -123
val2 = 0xdeadbeefcafebabe
s = B().i(32, val1).i(64, val2).slice()
expect(val1, s.i(32))
expect(False, s.is_empty())
expect(val2, s.u(64))
expect(True, s.is_empty())

val3 = 0xffffffff
s = S(B().i(32, val3).finalize())
expect(-1, s.i(23))
expect(9, len(s))

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

expect(S(B().finalize()), dict.get(s1))
expect(None, dict.get(B().i(288, 0).slice()))

dict_cell1 = dict.serialize().finalize()
#print(dict_cell1)

dict = D.deserialize(288, S(dict_cell1))

empty = C("")
expect(empty, B().finalize())
expect(0x96a296d224f285c67bee93c30f8a309157f0daa35dc5b87e410b78630a09cfc7, empty.repr_hash())

c = \
C("c_",
    C("c20",
        C("bfc000b4d82161bcb1013f2c6f06dd505c2fae81979bec199f1e6fee63c8c570054_"),
        C("2_",
            C("bfbc43df2056abee4c1a443fbfcfede0ba90d214c77322167fc08ce48920c17c1b"),
            C("bf94a50c1a849a4742214e751977af268269e6eeae064ce800634acea241d430d3"))))
expect(c, dict_cell1)

dict_bytes = dict_cell1.write()
dict_bytes = bytes(dict_cell1)
dict_cell2 = C.read(dict_bytes)
#print(dict_cell2)

expect(dict_cell1, dict_cell2)

#open("test.boc", "wb").write(dict_cell.write())
#cell = C.read(open("test.boc", "rb").read())

add = assemble("""
    ADD
""")
res = runvm(S(add), [10, 20], capabilities = 0x1)
expect([30], res.stack)

throw = assemble("THROW 100")
res = runvm(S(throw), [10])
expect(100, res.exit_code)
expect(0, res.exception_value)
expect([10], res.stack)

sib = StateInit(code = throw).serialize()
#print(sib)
sic = \
C("24_",
    C("f2c064"))
expect(sic, sib.finalize())
#open("throw.tvc", "wb").write(bytes(sib.finalize()))

si = StateInit().deserialize(S(sib.finalize()))
expect(throw, si.code)

throwargany = assemble("NEWC ENDC PUSHINT 100 THROWARGANY")
res = runvm(S(throwargany), [], trace = True)
expect(100, res.exit_code)
expect(empty, res.exception_value)
expect([], res.stack)

ctrls_ex = assemble("PUSHCTR c4")
abc = C("abc")
res = runvm(S(ctrls_ex), [], c4 = abc)
expect([abc], res.stack)

loop = """
    PUSHINT 0x8de120e0abffc55bf3fc723dee9e6d6bc01716064312a4e4be58be4e193fda8d
    PUSHSLICE xedf0554ee6f844bb7b08c91771d44c30dd69cc5b192ca2d8beff2e38b34f3d8f3c6e76b8c37c2a2fa3ea0bf082a128e2ae4c5befd941160ffcf4aed9e0d8f905
    PUSHINT 0xf5ec1345ad9adf191db35cdece12482e19a3a218e12f2d6c3e26e0ec6463d0a5

    PUSHINT {}
    PUSHCONT {{
        BLKPUSH 3, 2
        {}
        DROP
    }}
    REPEAT
"""

chksignu_loop = assemble(loop.format(50000, "CHKSIGNU"))
blkdrop2_loop = assemble(loop.format(5000000, "BLKDROP 2"))

res = runvm(S(chksignu_loop), [], gas_limit = 100000)
expect(ExceptionCode.OutOfGas.value, res.exit_code) # out of gas

def benchmark(name, code_cell, iters, steps = None, gas_used = None):
    print("running {}".format(name))
    t = time.time()
    res = runvm(S(code_cell), [])
    elapsed = time.time() - t

    expect(0, res.exit_code)
    if steps:
        expect(steps, res.steps)
    if gas_used:
        expect(gas_used, res.gas_used)

    print("total time {:.2f}s".format(elapsed))
    print("one iteration takes {:.2f}us".format(elapsed * 1000000 / iters))

benchmark("chksignu loop", chksignu_loop, 50000, 200008, 3750248)
benchmark("blkdrop2 loop", blkdrop2_loop, 5000000, 20000008, 375000248)
