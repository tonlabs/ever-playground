mod tests;
mod utils;

use std::sync::Arc;

use utils::*;

use num_bigint::{BigInt, BigUint, Sign};
use pyo3::{
    prelude::*,
    basic::CompareOp,
    exceptions::PyRuntimeError,
    types::{PyBytes, PyDict, PyList, PyLong, PyTuple},
};

use ton_types::{BuilderData, Cell as InternalCell, HashmapE, HashmapType, SliceData, IBitstring};
use ton_vm::{
    error::tvm_exception_full,
    executor::{Engine, EngineTraceInfo, gas::gas_state::Gas},
    stack::{
        StackItem, Stack,
        integer::{IntegerData, utils::process_value},
        savelist::SaveList,
    },
};

#[pyclass]
#[derive(Clone)]
pub struct Cell {
    cell: InternalCell,
}

#[pymethods]
impl Cell {
    #[new]
    #[pyo3(signature = (bitstring, *args))]
    fn new(bitstring: String, args: &PyTuple) -> PyResult<Self> {
        if args.len() > 4 {
            return err!("cell can't contain more than 4 references")
        }
        let slice = SliceData::from_string(&bitstring)
            .map_err(|_| PyRuntimeError::new_err(format!("invalid bitstring \"{}\"", bitstring)))?;
        let mut b = BuilderData::from_slice(&slice);
        for arg in args.iter() {
            let cell = arg.extract::<Cell>()?;
            b.checked_append_reference(cell.cell).map_err(runtime_err)?;
        }
        let cell = b.into_cell().map_err(runtime_err)?;
        Ok(Self { cell })
    }
    fn reference(&self, index: usize) -> PyResult<Cell> {
        self.cell.reference(index)
            .map(|cell| Self { cell })
            .map_err(runtime_err)
    }
    fn write<'a>(&'a self, py: Python<'a>) -> PyResult<&PyBytes> {
        ton_types::write_boc(&self.cell)
            .map(|bytes| PyBytes::new(py, &bytes))
            .map_err(runtime_err)
    }
    #[staticmethod]
    fn read(bytes: Vec<u8>) -> PyResult<Self> {
        ton_types::read_single_root_boc(bytes)
            .map(|cell| Self { cell })
            .map_err(runtime_err)
    }
    fn repr_hash(&self) -> BigUint {
        let hash = self.cell.repr_hash();
        BigUint::from_bytes_be(hash.as_slice())
    }
    fn __len__(&self) -> PyResult<usize> {
        self.cell.count_cells(usize::MAX).map_err(runtime_err)
    }
    fn __str__(&self) -> PyResult<String> {
        PyResult::Ok(dump_cell(self.cell.clone()))
    }
    fn __bytes__<'a>(&'a self, py: Python<'a>) -> PyResult<&PyBytes> {
        self.write(py)
    }
    fn __richcmp__(&self, other: Self, op: CompareOp, py: Python<'_>) -> PyObject {
        match op {
            CompareOp::Eq => self.cell.eq(&other.cell).into_py(py),
            CompareOp::Ne => self.cell.ne(&other.cell).into_py(py),
            _ => py.NotImplemented(),
        }
    }
}

#[pyclass]
#[derive(Clone)]
pub struct Slice {
    slice: SliceData,
}

#[pymethods]
impl Slice {
    #[new]
    fn new(cell: Cell) -> PyResult<Self> {
        SliceData::load_cell(cell.cell)
            .map(|slice| Self { slice })
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
    fn r(&mut self) -> PyResult<Cell> {
        self.slice.checked_drain_reference()
            .map(|cell| Cell { cell })
            .map_err(runtime_err)
    }
    fn r_peek(&self, i: usize) -> PyResult<Cell> {
        self.slice.reference(i)
            .map(|cell| Cell { cell })
            .map_err(runtime_err)
    }
    fn __len__(&self) -> usize {
        self.slice.remaining_bits()
    }
    fn is_empty(&self) -> PyResult<bool> {
        Ok(self.slice.is_empty())
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

#[pyclass]
#[derive(Clone, Default)]
pub struct Builder {
    builder: BuilderData,
}

#[pymethods]
impl Builder {
    #[new]
    fn new() -> Self {
        Self::default()
    }
    fn s(mut slf: PyRefMut<Self>, slice: Slice) -> PyResult<PyRefMut<Self>> {
        slf.builder.checked_append_references_and_data(&slice.slice)
            .map_err(runtime_err)?;
        Ok(slf)
    }
    fn b(mut slf: PyRefMut<Self>, builder: Builder) -> PyResult<PyRefMut<Self>> {
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
    fn r(mut slf: PyRefMut<Self>, cell: Cell) -> PyResult<PyRefMut<Self>> {
        slf.builder.checked_append_reference(cell.cell)
            .map_err(runtime_err)?;
        Ok(slf)
    }
    fn slice(&self) -> PyResult<Slice> {
        SliceData::load_builder(self.builder.clone())
            .map(|slice| Slice { slice })
            .map_err(runtime_err)
    }
    fn finalize(&self) -> PyResult<Cell> {
        self.builder.clone().into_cell()
            .map(|cell| Cell { cell })
            .map_err(runtime_err)
    }
    fn __str__(&self) -> PyResult<String> {
        let cell = self.builder.clone().into_cell()
            .map_err(runtime_err)?;
        Ok(dump_cell(cell))
    }
}

#[pyclass]
#[derive(Clone)]
pub struct Dictionary {
    map: HashmapE,
}

#[pymethods]
impl Dictionary {
    #[new]
    fn new(bits: usize) -> Self {
        Self { map: HashmapE::with_bit_len(bits) }
    }
    fn bit_len(&self) -> usize {
        self.map.bit_len()
    }
    fn get(&self, key: Slice, py: Python<'_>) -> PyResult<PyObject> {
        match self.map.get(key.slice).map_err(runtime_err)? {
            Some(slice) => Ok(Slice { slice }.into_py(py)),
            None => Ok(py.None())
        }
    }
    fn add(&mut self, key: Slice, value: Slice) -> PyResult<Self> {
        self.map.set(key.slice, &value.slice).map_err(runtime_err)?;
        Ok(self.clone())
    }
    fn add_kv_slice(&mut self, key_bits: usize, mut slice: Slice) -> PyResult<Self> {
        let key = slice.slice.get_next_slice(key_bits).map_err(runtime_err)?;
        self.map.set(key, &slice.slice).map_err(runtime_err)?;
        Ok(self.clone())
    }
    fn serialize(&self) -> PyResult<Builder> {
        let mut builder = BuilderData::new();
        self.map.write_hashmap_data(&mut builder).map_err(runtime_err)?;
        Ok(Builder { builder })
    }
    #[staticmethod]
    fn deserialize(bits: usize, slice: &mut Slice) -> PyResult<Self> {
        let map = if slice.slice.get_next_bit().map_err(runtime_err)? {
            let cell = slice.slice.checked_drain_reference().map_err(runtime_err)?;
            HashmapE::with_hashmap(bits, Some(cell))
        } else {
            HashmapE::with_hashmap(bits, None)
        };
        Ok(Dictionary { map })
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
fn assemble(code: String) -> PyResult<Cell> {
    let cell = ton_labs_assembler::compile_code(&code)
        .map_err(|err| PyRuntimeError::new_err(err.to_string()))?
        .cell()
        .clone();
    Ok(Cell { cell })
}

struct VmParams {
    capabilites: u64,
    c4: Option<StackItem>,
    c7: Option<StackItem>,
    gas_limit: i64,
    gas_credit: i64,
    trace: bool,
}

impl Default for VmParams {
    fn default() -> Self {
        Self {
            capabilites: 0x537ae,
            c4: None,
            c7: None,
            gas_limit: 1000000000,
            gas_credit: 0,
            trace: false,
        }
    }
}

impl VmParams {
    fn new(dict: &PyDict) -> PyResult<Self> {
        let mut params = Self::default();
        for (key, val) in dict {
            match key.extract::<String>()?.as_str() {
                "capabilities" => params.capabilites = val.extract::<u64>()?,
                "c4" => params.c4 = Some(convert_to_vm(val)?),
                "c7" => params.c7 = Some(convert_to_vm(val)?),
                "gas_limit" => params.gas_limit = val.extract::<i64>()?,
                "gas_credit" => params.gas_credit = val.extract::<i64>()?,
                "trace" => params.trace = val.extract::<bool>()?,
                p => return err!("unknown vm parameter {}", p)
            }
        }
        Ok(params)
    }
}

#[pyclass(get_all)]
#[derive(Default)]
struct VmResult {
    stack: Option<PyObject>,
    exit_code: i32,
    exception_value: Option<PyObject>,
    steps: u32,
    gas_used: i64,
}

#[pyfunction]
#[pyo3(signature = (code, in_stack, **kwargs))]
fn runvm(code: Slice, in_stack: &PyList, kwargs: Option<&PyDict>) -> PyResult<PyObject> {
    let py = in_stack.py();
    let mut vm_stack = Stack::new();
    for item in in_stack.iter() {
        vm_stack.push(convert_to_vm(item)?);
    }

    let params = match kwargs {
        None => VmParams::default(),
        Some(dict) => VmParams::new(dict)?
    };

    let mut result = VmResult::default();
    let mut ctrls = SaveList::new();
    if let Some(mut c4) = params.c4 {
        ctrls.put(4, &mut c4).map_err(runtime_err)?;
    }
    if let Some(mut c7) = params.c7 {
        ctrls.put(7, &mut c7).map_err(runtime_err)?;
    }
    let gas = Gas::new(params.gas_limit, params.gas_credit, 1000000000, 10);
    let mut engine = Engine::with_capabilities(params.capabilites)
        .setup(code.slice, Some(ctrls), Some(vm_stack), Some(gas));
    if params.trace {
        engine.set_trace_callback(trace_callback);
    }
    match engine.execute() {
        Ok(exit_code) => result.exit_code = exit_code,
        Err(err) => if let Some(exception) = tvm_exception_full(&err) {
            result.exit_code = exception.exception_or_custom_code();
            result.exception_value = Some(convert_from_vm(py, &exception.value)?);
        } else {
            return Err(PyRuntimeError::new_err(format!("execution failed: {}", err)))
        }
    }

    let mut out_stack = Vec::new();
    for item in engine.stack().iter() {
        out_stack.push(convert_from_vm(py, item)?)
    }

    result.stack = Some(PyList::new(py, out_stack).to_object(py));
    result.steps = engine.steps();
    result.gas_used = engine.gas_used();
    Ok(result.into_py(py))
}

fn trace_callback(_engine: &Engine, info: &EngineTraceInfo) {
    use ton_vm::executor::EngineTraceInfoType::*;
    match info.info_type {
        Start => { }
        Dump =>  println!("DUMP {}", info.cmd_str),
        Exception => println!("EXCEPTION"),
        _ => {
            println!("STEP {} {}", info.step, info.cmd_str);
            println!("GAS {} in total, {} by insn", info.gas_used, info.gas_cmd);
            if info.stack.is_empty() {
                println!("STACK <empty>")
            } else {
                for item in info.stack.iter() {
                    println!("STACK {}", item)
                }
            }
            println!()
        }
    }
}

fn convert_to_vm(value: &PyAny) -> PyResult<StackItem> {
    if value.is_none() {
        Ok(StackItem::None)
    } else if let Ok(v) = value.downcast::<PyLong>() {
        let integer = IntegerData::from(v.extract::<BigInt>()?)
            .map_err(runtime_err)?;
        Ok(StackItem::Integer(Arc::new(integer)))
    } else if let Ok(v) = value.downcast::<PyList>() {
        let mut tuple = Vec::new();
        for item in v {
            tuple.push(convert_to_vm(item)?)
        }
        Ok(StackItem::Tuple(Arc::new(tuple)))
    } else if let Ok(v) = value.extract::<Cell>() {
        Ok(StackItem::Cell(v.cell))
    } else if let Ok(v) = value.extract::<Slice>() {
        Ok(StackItem::Slice(v.slice))
    } else if let Ok(v) = value.extract::<Builder>() {
        Ok(StackItem::Builder(Arc::new(v.builder)))
    } else {
        return err!("unsupported value {}", value)
    }
}

#[pyclass]
struct NaN {
}

impl NaN {
    fn new() -> Self {
        Self { }
    }
}

#[pyclass]
struct Continuation {
}

impl Continuation {
    fn new() -> Self {
        Self { }
    }
}

fn convert_from_vm(py: Python<'_>, item: &StackItem) -> PyResult<PyObject> {
    match item {
        StackItem::None =>
            Ok(py.None()),
        StackItem::Builder(v) =>
            Ok(Builder { builder: v.as_ref().clone() }.into_py(py)),
        StackItem::Cell(v) =>
            Ok(Cell { cell: v.clone() }.into_py(py)),
        StackItem::Continuation(_) =>
            Ok(Continuation::new().into_py(py)),
        StackItem::Integer(v) => {
            let integer = match process_value(v.as_ref(), |v| Ok(v.clone())) {
                Err(_) => NaN::new().into_py(py),
                Ok(v) => v.into_py(py),
            };
            Ok(integer)
        }
        StackItem::Slice(v) =>
            Ok(Slice { slice: v.clone() }.into_py(py)),
        StackItem::Tuple(v) => {
            let mut list = Vec::new();
            for item in v.iter() {
                list.push(convert_from_vm(py, item)?)
            }
            Ok(PyList::new(py, list).into_py(py))
        }
    }
}

#[pymodule]
fn ever_playground(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<NaN>()?;
    m.add_class::<Cell>()?;
    m.add_class::<Builder>()?;
    m.add_class::<Slice>()?;
    m.add_class::<Dictionary>()?;
    m.add_class::<Continuation>()?;
    m.add_class::<VmResult>()?;
    m.add_wrapped(wrap_pyfunction!(assemble))?;
    m.add_wrapped(wrap_pyfunction!(runvm))?;
    Ok(())
}
