# ever-playground

A tool alternative to Fift: play with Cells, Slices, Builders, and Dictionaries — native types of TVM; assemble and run TVM code.

### Using the package

```
pip3 install ever-playground
python3
Python 3.10.12 (main, Jun 11 2023, 05:26:28) [GCC 11.4.0] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> from ever_playground import Cell as C
>>> print(C("abc_", C("def8_")))
C("abc_",
    C("def"))
```

### Running examples in dev mode

```
python3 -m venv .venv
source .venv/bin/activate
pip install maturin
maturin develop
python3 run-examples.py
```
