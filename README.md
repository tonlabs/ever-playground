# ever-playground

A tool alternative to Fift: play with Cells, Slices, Builders, and Dictionaries — native types of TVM; assemble and run TVM code.

### Running

```
pip install ever-playground
python3
Python 3.10.6 (main, Mar 10 2023, 10:55:28) [GCC 11.3.0] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> from ever_playground import Cell as C
>>> print(C("abc_"))
C("abc_")
```

### Running examples in dev mode

```
python3 -m venv .venv
source .venv/bin/activate
pip install maturin
maturin develop
python3 examples.py
```
