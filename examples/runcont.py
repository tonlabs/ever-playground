from ever_playground import *

def a(text: str) -> Slice:
    return Slice(assemble(text))

def make_while(cc: Continuation, c0: Continuation, body_text: str, cond_text: str) -> Continuation:
    body = a(body_text)
    cond = Continuation(
        typ = ContinuationType.create_ordinary(),
        code = a(cond_text)
    )
    while_ = Continuation(typ = ContinuationType.create_while(body, cond.code))
    cc.savelist.put(0, c0)
    while_.savelist.put(0, cc)
    cond.savelist.put(0, while_)
    return cond

def runcont(entry: Continuation, gas_limit: int = 1_000_000, gas_credit: int = 10_000, trace = False) -> VmResult:
    regs = SaveList()
    regs.put(0, entry)
    gas = Gas(gas_limit, gas_credit, gas_limit, 10)
    return runvm_generic(VmState(Continuation(), regs, gas), trace = trace)

quit0 = Continuation(typ = ContinuationType.create_quit(500))
rest = Continuation(typ = ContinuationType.create_ordinary(), code = a("RET"))

program = make_while(rest, quit0, "INC", "DUP PUSHINT 5 LESS")
program.stack.append(0)

r = runcont(program)
assert(r.exit_code == 500)
assert(r.state.cc.stack == [5])
