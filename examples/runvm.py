import time

from ever_playground import Cell as C
from ever_playground import Slice as S
from ever_playground import ExceptionCode
from ever_playground import StateInit, runvm, assemble

def expect(expected, v):
    if not expected == v:
        raise Exception("{} != {}".format(expected, v))

add = assemble("""
    ADD
""")
res = runvm(S(add), [10, 20], capabilities = 0x1)
expect([30], res.state.cc.stack)

throw = assemble("THROW 100")
res = runvm(S(throw), [10])
expect(100, res.exit_code)
expect(0, res.exception_value)
expect([10], res.state.cc.stack)

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
expect(C(""), res.exception_value)
expect([], res.state.cc.stack)

ctrls_ex = assemble("PUSHCTR c4")
abc = C("abc")
res = runvm(S(ctrls_ex), [], c4 = abc)
expect([abc], res.state.cc.stack)

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

chksignu_loop = assemble(loop.format(10000, "CHKSIGNU"))
blkdrop2_loop = assemble(loop.format(1000000, "BLKDROP 2"))

res = runvm(S(chksignu_loop), [], gas_limit = 100000)
expect(ExceptionCode.OutOfGas.value, res.exit_code)

def benchmark(name, code_cell, iters, steps = None, gas_used = None):
    print("running {}".format(name))
    t = time.time()
    res = runvm(S(code_cell), [])
    elapsed = time.time() - t

    expect(0, res.exit_code)
    if steps:
        expect(steps, res.state.steps)
    if gas_used:
        expect(gas_used, res.state.gas.used)

    print("total time {:.2f}s".format(elapsed))
    print("one iteration takes {:.2f}us".format(elapsed * 1000000 / iters))

benchmark("chksignu loop", chksignu_loop, 10000, 40008, 750259)
benchmark("blkdrop2 loop", blkdrop2_loop, 1000000, 4000008, 75000248)
