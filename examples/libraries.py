from ever_playground import *

def expect(expected, v):
    if not expected == v:
        raise Exception("{} != {}".format(expected, v))

callee = assemble("""
    PUSHINT 13
""")
lib_cell_hash = "{:064x}".format(callee.repr_hash())
caller = assemble("""
    CALLREF {{
        .library-cell {}
    }}
""".format(lib_cell_hash))

lib = Dictionary(256)
lib.add_ref(Builder().x(lib_cell_hash).slice(), callee)

caps = 0x800 # CapSetLibCode
res = runvm(Slice(caller), [], capabilities = caps, libs = [lib])
expect([13], res.state.cc.stack)
