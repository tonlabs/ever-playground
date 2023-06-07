from ever_playground import Slice, assemble, runvm

target_call_id = 4444
setup = f"""
    PUSHCONT {{
        PUSHINT {target_call_id}
        EQUAL
        THROWIF 0
        THROW 1 }}
    POPCTR c3
"""

fragment = """
    DUP
    PUSHINT {} ; function id
    EQUAL
    IFJMPREF {{
        {} ; a sequence of nops 
        CALL {} ; call id
    }}
"""

fence = """
    THROW 1
"""

target_func_id = 0xec4c18f9
ids = [
    0xeebdce93,
    0xf782f611,
    0xcdfa0518,
    0xaa4a43c6,
    0x6dfb812f,
    0x4ffeea48,
    0x6b2d00fb,
    0x15bb7a7b,
    0xd8d06025,
    0xe4d5bbb8
]

def bench_by_cmps_count(filler):
    print("cmps ifjmpref       pushcont+ifjmp    gas ratio")
    template = setup
    for i in range(0, len(ids)):
        template += fragment.format(ids[i], filler, i * 1000)
        text1 = template + fragment.format(target_func_id, filler, target_call_id) + fence
        code1 = assemble(text1)
        text2 = text1.replace("IFJMPREF", "PUSHCONT").replace("    }", "    } IFJMP")
        code2 = assemble(text2)

        res1 = runvm(Slice(code1), [target_func_id])
        assert(res1.exit_code == 0)
        res2 = runvm(Slice(code2), [target_func_id])
        assert(res2.exit_code == 0)

        gas1 = res1.state.gas.used
        gas2 = res2.state.gas.used

        ratio = float(gas2) / gas1
        print(f"{i+1:<4} {code1.cells_count():<2} {gas1:8}    {code2.cells_count():<2} {gas2:<14} {ratio:.2f}")

for i in [0, 16, 64]:
    print(f"ifjmp body has {i} nops before call")
    bench_by_cmps_count("NOP " * i)
