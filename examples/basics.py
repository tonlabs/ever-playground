from ever_playground import Cell as C
from ever_playground import Builder as B
from ever_playground import Slice as S
from ever_playground import Dictionary as D
from ever_playground import parse_smc_addr

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
expect(9, s.remaining_bits())

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
expect(0, empty.repr_depth())
expect(0, empty.level())
expect(0, empty.depth(0))

c = \
C("c_",
    C("c20",
        C("bfc000b4d82161bcb1013f2c6f06dd505c2fae81979bec199f1e6fee63c8c570054_"),
        C("2_",
            C("bfbc43df2056abee4c1a443fbfcfede0ba90d214c77322167fc08ce48920c17c1b"),
            C("bf94a50c1a849a4742214e751977af268269e6eeae064ce800634acea241d430d3"))))
expect(c, dict_cell1)

dict_bytes = dict_cell1.write(0)
dict_cell2 = C.read(dict_bytes)
#print(dict_cell2)

expect(dict_cell1, dict_cell2)

#open("test.boc", "wb").write(dict_cell.write())
#cell = C.read(open("test.boc", "rb").read())
