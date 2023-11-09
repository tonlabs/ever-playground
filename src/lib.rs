mod continuations;
mod crypto;
mod tests;
mod utils;
mod vm;

use std::collections::HashSet;
use continuations::*;
use crypto::*;
use utils::*;
use vm::*;
use num_bigint::{BigInt, BigUint, Sign};
use pyo3::{
    prelude::*,
    basic::CompareOp,
    exceptions::PyRuntimeError,
    types::{PyBytes, PyTuple},
};
use ton_types::{BuilderData, Cell, HashmapE, HashmapType, SliceData, IBitstring};

#[pyclass(name = "Cell")]
#[derive(Clone)]
struct PyCell {
    cell: Cell,
}

impl PyCell {
    fn new(cell: Cell) -> Self {
        Self { cell }
    }
}

#[pymethods]
impl PyCell {
    #[new]
    #[pyo3(signature = (bitstring, *args))]
    fn create(bitstring: String, args: &PyTuple) -> PyResult<Self> {
        if args.len() > 4 {
            return err!("cell can't contain more than 4 references")
        }
        let slice = SliceData::from_string(&bitstring)
            .map_err(|_| PyRuntimeError::new_err(format!("invalid bitstring \"{}\"", bitstring)))?;
        let mut b = slice.as_builder();
        for arg in args.iter() {
            let cell = arg.extract::<PyCell>()?;
            b.checked_append_reference(cell.cell).map_err(runtime_err)?;
        }
        let cell = b.into_cell().map_err(runtime_err)?;
        Ok(Self::new(cell))
    }
    #[staticmethod]
    fn empty() -> Self {
        Self::new(Cell::default())
    }
    fn reference(&self, index: usize) -> PyResult<Self> {
        self.cell.reference(index)
            .map(|cell| Self::new(cell))
            .map_err(runtime_err)
    }
    fn write<'a>(&'a self, py: Python<'a>, flags: usize) -> PyResult<&PyBytes> {
        if flags > 3 {
            return err!("flags {} is not supported", flags)
        }
        let include_index = flags & 1 == 1;
        let include_crc = flags & 2 == 2;
        let writer = ton_types::BocWriter::with_root(&self.cell).map_err(runtime_err)?;
        let mut bytes = Vec::new();
        writer.write_ex(&mut bytes, include_index, include_crc, None, None).map_err(runtime_err)?;
        Ok(PyBytes::new(py, &bytes))
    }
    #[staticmethod]
    fn read(bytes: Vec<u8>) -> PyResult<Self> {
        ton_types::read_single_root_boc(bytes)
            .map(|cell| Self::new(cell))
            .map_err(runtime_err)
    }
    fn repr_hash(&self) -> BigUint {
        let hash = self.cell.repr_hash();
        BigUint::from_bytes_be(hash.as_slice())
    }
    fn repr_depth(&self) -> usize {
        self.cell.repr_depth() as usize
    }
    fn level(&self) -> usize {
        self.cell.level() as usize
    }
    fn depth(&self, index: usize) -> usize {
        self.cell.depth(index) as usize
    }
    fn cells_count(&self) -> PyResult<usize> {
        self.cell.count_cells(usize::MAX).map_err(runtime_err)
    }
    fn unique_cells_count(&self) -> PyResult<usize> {
        let mut set = HashSet::new();
        let mut stack = Vec::new();
        let mut unique_count = 0;
        stack.push(self.cell.clone());
        while let Some(cell) = stack.pop() {
            if set.insert(cell.repr_hash()) {
                unique_count += 1;
                for i in 0..cell.references_count() {
                    stack.push(cell.reference(i).unwrap())
                }
            }
        }
        Ok(unique_count)
    }
    fn __str__(&self) -> PyResult<String> {
        Ok(dump_cell(self.cell.clone()))
    }
    fn __richcmp__(&self, other: Self, op: CompareOp, py: Python<'_>) -> PyObject {
        match op {
            CompareOp::Eq => self.cell.eq(&other.cell).into_py(py),
            CompareOp::Ne => self.cell.ne(&other.cell).into_py(py),
            _ => py.NotImplemented(),
        }
    }
}

#[pyclass(name = "Slice")]
#[derive(Clone, Default)]
struct PySlice {
    slice: SliceData,
}

impl PySlice {
    fn new(slice: SliceData) -> Self {
        Self { slice }
    }
}

#[pymethods]
impl PySlice {
    #[new]
    fn create(cell: PyCell) -> PyResult<Self> {
        SliceData::load_cell(cell.cell)
            .map(Self::new)
            .map_err(runtime_err)
    }
    fn i(&mut self, bits: usize) -> PyResult<BigInt> {
        let bytes = self.slice.get_next_bits(bits)
            .map_err(runtime_err)?;
        signed_int_deserialize(&bytes, bits)
    }
    fn u(&mut self, bits: usize) -> PyResult<BigUint> {
        let bytes = self.slice.get_next_bits(bits)
            .map_err(runtime_err)?;
        unsigned_int_deserialize(&bytes, bits)
    }
    fn refs(&self) -> PyResult<usize> {
        Ok(self.slice.remaining_references())
    }
    fn r(&mut self) -> PyResult<PyCell> {
        self.slice.checked_drain_reference()
            .map(PyCell::new)
            .map_err(runtime_err)
    }
    fn r_peek(&self, i: usize) -> PyResult<PyCell> {
        self.slice.reference(i)
            .map(PyCell::new)
            .map_err(runtime_err)
    }
    fn remaining_bits(&self) -> usize {
        self.slice.remaining_bits()
    }
    fn is_empty(&self) -> PyResult<bool> {
        Ok(self.slice.is_empty())
    }
    fn skip(&mut self, bits: usize) -> PyResult<()> {
        self.slice.move_by(bits)
            .map_err(runtime_err)
    }
    fn __richcmp__(&self, other: Self, op: CompareOp, py: Python<'_>) -> PyObject {
        match op {
            CompareOp::Eq => self.slice.eq(&other.slice).into_py(py),
            CompareOp::Ne => self.slice.ne(&other.slice).into_py(py),
            _ => py.NotImplemented(),
        }
    }
    fn __str__(&self) -> PyResult<String> {
        Ok(dump_cell(self.slice.cell().clone()))
    }
}

#[pyclass(name = "Builder")]
#[derive(Clone, Default)]
struct PyBuilder {
    builder: BuilderData,
}

impl PyBuilder {
    fn new(builder: BuilderData) -> Self {
        Self { builder }
    }
}

#[pymethods]
impl PyBuilder {
    #[new]
    fn create() -> Self {
        Self::default()
    }
    fn s(mut slf: PyRefMut<Self>, slice: PySlice) -> PyResult<PyRefMut<Self>> {
        slf.builder.checked_append_references_and_data(&slice.slice)
            .map_err(runtime_err)?;
        Ok(slf)
    }
    fn b(mut slf: PyRefMut<Self>, builder: PyBuilder) -> PyResult<PyRefMut<Self>> {
        slf.builder.append_builder(&builder.builder).map_err(runtime_err)?;
        Ok(slf)
    }
    fn i(mut slf: PyRefMut<Self>, bits: usize, integer: BigInt) -> PyResult<PyRefMut<Self>> {
        if bits == 0 {
            return err!("bits must be greater than 0")
        }
        let bytes = if integer.sign() == Sign::Minus {
            signed_int_serialize(integer, bits)?
        }else {
            unsigned_int_serialize(integer, bits)?
        };
        slf.builder.append_raw(&bytes, bits).map_err(runtime_err)?;
        Ok(slf)
    }
    // TODO consider moving this to Python library (by using superclassing)
    fn ib(mut slf: PyRefMut<Self>, bin: String) -> PyResult<PyRefMut<Self>> {
        for digit in bin.chars() {
            match digit {
                '0' => { slf.builder.append_bit_zero().map_err(runtime_err)?; }
                '1' => { slf.builder.append_bit_one().map_err(runtime_err)?; }
                _ => return err!("Failed to parse binary string {}", bin)
            }
        }
        Ok(slf)
    }
    fn x(mut slf: PyRefMut<Self>, bitstring: String) -> PyResult<PyRefMut<Self>> {
        let slice = SliceData::from_string(&bitstring)
            .map_err(runtime_err)?;
        slf.builder.checked_append_references_and_data(&slice)
            .map_err(runtime_err)?;
        Ok(slf)
    }
    fn y(mut slf: PyRefMut<Self>, bytes: Vec<u8>) -> PyResult<PyRefMut<Self>> {
        let length = bytes.len() * 8;
        let bytes = BuilderData::with_raw(bytes, length)
            .map_err(runtime_err)?;
        slf.builder.append_builder(&bytes)
            .map_err(runtime_err)?;
        Ok(slf)
    }
    fn r(mut slf: PyRefMut<Self>, cell: PyCell) -> PyResult<PyRefMut<Self>> {
        slf.builder.checked_append_reference(cell.cell)
            .map_err(runtime_err)?;
        Ok(slf)
    }
    fn fits(&self, slice: PySlice, extra_bits: usize, extra_refs: usize) -> bool {
        self.builder.check_enough_space(slice.slice.remaining_bits() + extra_bits) &&
            self.builder.check_enough_refs(slice.slice.remaining_references() + extra_refs)
    }
    fn slice(&self) -> PyResult<PySlice> {
        SliceData::load_builder(self.builder.clone())
            .map(PySlice::new)
            .map_err(runtime_err)
    }
    fn finalize(&self) -> PyResult<PyCell> {
        self.builder.clone().into_cell()
            .map(PyCell::new)
            .map_err(runtime_err)
    }
    fn __str__(&self) -> PyResult<String> {
        let cell = self.builder.clone().into_cell()
            .map_err(runtime_err)?;
        Ok(dump_cell(cell))
    }
}

#[pyclass(name = "Dictionary")]
#[derive(Clone)]
struct PyDictionary {
    map: HashmapE,
}

impl PyDictionary {
    fn new(map: HashmapE) -> Self {
        Self { map }
    }
}

#[pymethods]
impl PyDictionary {
    #[new]
    fn create(bits: usize) -> Self {
        Self { map: HashmapE::with_bit_len(bits) }
    }
    fn bit_len(&self) -> usize {
        self.map.bit_len()
    }
    fn get(&self, key: PySlice, py: Python<'_>) -> PyResult<PyObject> {
        match self.map.get(key.slice).map_err(runtime_err)? {
            Some(slice) => Ok(PySlice::new(slice).into_py(py)),
            None => Ok(py.None())
        }
    }
    fn add(mut slf: PyRefMut<Self>, key: PySlice, value: PySlice) -> PyResult<PyRefMut<Self>> {
        slf.map.set(key.slice, &value.slice).map_err(runtime_err)?;
        Ok(slf)
    }
    fn add_ref(mut slf: PyRefMut<Self>, key: PySlice, value: PyCell) -> PyResult<PyRefMut<Self>> {
        slf.map.setref(key.slice, &value.cell).map_err(runtime_err)?;
        Ok(slf)
    }
    fn add_kv_slice(mut slf: PyRefMut<Self>, key_bits: usize, mut slice: PySlice) -> PyResult<PyRefMut<Self>> {
        let key = slice.slice.get_next_slice(key_bits).map_err(runtime_err)?;
        slf.map.set(key, &slice.slice).map_err(runtime_err)?;
        Ok(slf)
    }
    fn cell(&self) -> PyResult<PyCell> {
        self.map.data()
            .map(|cell| PyCell { cell: cell.clone() })
            .ok_or(PyRuntimeError::new_err("empty dictionary"))
    }
    fn serialize(&self) -> PyResult<PyBuilder> {
        let mut builder = BuilderData::new();
        self.map.write_hashmap_data(&mut builder).map_err(runtime_err)?;
        Ok(PyBuilder::new(builder))
    }
    #[staticmethod]
    fn deserialize(bits: usize, slice: &mut PySlice) -> PyResult<Self> {
        let map = if slice.slice.get_next_bit().map_err(runtime_err)? {
            let cell = slice.slice.checked_drain_reference().map_err(runtime_err)?;
            HashmapE::with_hashmap(bits, Some(cell))
        } else {
            HashmapE::with_hashmap(bits, None)
        };
        Ok(Self::new(map))
    }
    fn __len__(&self) -> PyResult<usize> {
        self.map.count(usize::MAX).map_err(runtime_err)
    }
    fn __str__(&self) -> PyResult<String> {
        match self.map.data() {
            None => Ok(String::from("empty dictionary")),
            Some(cell) => Ok(dump_cell(cell.clone()))
        }
    }
}

#[pyfunction]
fn assemble(code: String) -> PyResult<PyCell> {
    let slice = ton_labs_assembler::compile_code(&code)
        .map_err(|err| PyRuntimeError::new_err(err.to_string()))?;
    Ok(PyCell::new(slice.cell().clone()))
}

#[derive(Clone)]
#[pyclass(name = "NaN")]
struct PyNaN {
}

impl PyNaN {
    fn new() -> Self {
        Self { }
    }
}

#[pymethods]
impl PyNaN {
    #[new]
    fn create() -> Self {
        PyNaN::new()
    }
    // TODO consider making PyNaN a singleton instead
    fn __richcmp__(&self, _other: Self, op: CompareOp, py: Python<'_>) -> PyObject {
        match op {
            CompareOp::Eq => true.into_py(py),
            CompareOp::Ne => false.into_py(py),
            _ => py.NotImplemented(),
        }
    }
}

#[pymodule]
fn ever_playground(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<PyNaN>()?;
    m.add_class::<PyCell>()?;
    m.add_class::<PyBuilder>()?;
    m.add_class::<PySlice>()?;
    m.add_class::<PyDictionary>()?;
    m.add_class::<PySaveList>()?;
    m.add_class::<PyContinuationType>()?;
    m.add_class::<PyContinuation>()?;
    m.add_class::<PyGas>()?;
    m.add_class::<PyVmState>()?;
    m.add_class::<PyVmResult>()?;
    m.add_wrapped(wrap_pyfunction!(assemble))?;
    m.add_wrapped(wrap_pyfunction!(runvm_generic))?;
    m.add_wrapped(wrap_pyfunction!(ed25519_new_keypair))?;
    m.add_wrapped(wrap_pyfunction!(ed25519_secret_to_public))?;
    m.add_wrapped(wrap_pyfunction!(ed25519_sign))?;
    m.add_wrapped(wrap_pyfunction!(ed25519_check_signature))?;
    Ok(())
}
