#!/usr/bin/env python3

import filecmp
import subprocess
import os

from ever_playground import Cell

ton_src = "/e/ton"
ton_build = ton_src + "/build"
fift = [ton_build + "/crypto/fift", "-I", ton_src + "/crypto/fift/lib", "-s"]

def run(params):
    p = subprocess.run(params)
    assert(0 == p.returncode)

def remove(filename: str):
    try:
        os.remove(filename)
    except OSError:
        pass

def assert_identical_files(filename1: str, filename2: str):
    res = filecmp.cmp(filename1, filename2)
    remove(filename1)
    remove(filename2)
    if not res:
        raise Exception("outputs are not identical")

def run_basics():
    run(["python3", "examples/basics.py"])

def run_runvm():
    run(["python3", "examples/runvm.py"])

def test_recover_stake():
    script = "examples/recover-stake"
    base = "recover-query"
    py_output = "py-" + base + ".boc"
    fift_output = "fift-" + base + "boc"

    run(["python3", script + ".py", py_output])
    run(fift + [script + ".fif", fift_output])

    assert_identical_files(py_output, fift_output)

def test_testgiver():
    script = "examples/testgiver"
    base = "testgiver-query"
    py_output = "py-" + base
    fift_output = "fift-" + base
    common = ["13:7777777777777777777777777777777777777777777777777777777777777777", "1234", "15.7"]

    run(["python3", script + ".py"] + common + [py_output])
    run(fift + [script + ".fif"] + common + [fift_output])

    assert_identical_files(py_output + ".boc", fift_output + ".boc")

def test_validator_elect_req():
    script = "examples/validator-elect-req"
    base = "validator-to-sign.bin"
    py_output = "py-" + base
    fift_output = "fift-" + base
    common = ["-1:7777777777777777777777777777777777777777777777777777777777777777", "1684501715", "33.333",
        "8888888888888888888888888888888888888888888888888888888888888888"]
    
    run(["python3", script + ".py"] + common + [py_output])
    run(fift + [script + ".fif"] + common + [fift_output])

    assert_identical_files(py_output, fift_output)

def test_highload_wallet_v2():
    curdir = os.getcwd()
    os.chdir("examples/highload")

    script = "highload-wallet-v2"
    base = "wallet-query"
    py_output = "py-" + base
    fift_output = "fift-" + base

    run(["python3", script + ".py", "sample", "27172", "order-list-py", "--savefile", py_output])
    run(fift + [script + ".fif", "sample", "27172", "order-list-fift", fift_output])

    # boc serialization seems different, compare deser-ed cells instead
    # assert_identical_files(py_output + ".boc", fift_output + ".boc")
    p = Cell.read(open(py_output + ".boc", "rb").read())
    f = Cell.read(open(fift_output + ".boc", "rb").read())
    remove(py_output + ".boc")
    remove(fift_output + ".boc")
    assert(p == f)

    os.chdir(curdir)

def test_ifjmp_perf_eval():
    run(["python3", "examples/ifjmp-perf-eval.py"])

def run_runcont():
    run(["python3", "examples/runcont.py"])

def run_libraries():
    run(["python3", "examples/libraries.py"])

run_basics()
run_runvm()
run_runcont()
run_libraries()
test_recover_stake()
test_testgiver()
test_validator_elect_req()
test_highload_wallet_v2()
test_ifjmp_perf_eval()
