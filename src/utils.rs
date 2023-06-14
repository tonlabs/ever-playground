use std::sync::Arc;
use crate::{
    PyBuilder, PyCell, PyNaN, PySlice,
    continuations::PyContinuation,
};
use num_bigint::{BigInt, BigUint, Sign};
use pyo3::{
    exceptions::PyRuntimeError,
    prelude::{IntoPy, Python, PyAny, PyObject, PyResult},
    PyErr,
    types::{PyList, PyLong},
};
use ton_types::Cell;
use ton_vm::stack::{
    StackItem,
    integer::{IntegerData, utils::process_value},
};

macro_rules! err {
    ($error:literal) => {
        PyResult::Err(PyRuntimeError::new_err($error))
    };
    ($fmt:expr, $($arg:tt)+) => {
        PyResult::Err(PyRuntimeError::new_err(format!($fmt, $($arg)+)))
    };
}

pub(crate) use err;

pub(crate) fn runtime_err(err: ton_types::Error) -> PyErr {
    PyRuntimeError::new_err(err.to_string())
}

pub(crate) fn signed_int_serialize(mut integer: BigInt, bits: usize) -> PyResult<Vec<u8>> {
    let excess_bits = excess_bits(bits);
    if excess_bits != 0 {
        integer <<= 8 - excess_bits;
    }
    let buffer = integer.to_signed_bytes_be();
    Ok(extend_buffer_be(buffer, bits, integer.sign() == Sign::Minus))
}

pub(crate) fn unsigned_int_serialize(integer: BigInt, bits: usize) -> PyResult<Vec<u8>> {
    let mut integer = integer.to_biguint()
        .ok_or(PyRuntimeError::new_err("integer is negative"))?;
    let excess_bits = excess_bits(bits);
    if excess_bits != 0 {
        integer <<= 8 - excess_bits;
    }
    let buffer = integer.to_bytes_be();
    Ok(extend_buffer_be(buffer, bits, false))
}

pub(crate) fn signed_int_deserialize(bytes: &[u8], bits: usize) -> PyResult<BigInt> {
    let mut integer = BigInt::from_signed_bytes_be(bytes);
    let excess_bits = excess_bits(bits);
    if excess_bits != 0 {
        integer >>= 8 - excess_bits;
    }
    Ok(integer)
}

pub(crate) fn unsigned_int_deserialize(bytes: &[u8], bits: usize) -> PyResult<BigUint> {
    let mut integer = BigUint::from_bytes_be(bytes);
    let excess_bits = excess_bits(bits);
    if excess_bits != 0 {
        integer >>= 8 - excess_bits;
    }
    Ok(integer)
}

fn excess_bits(bits: usize) -> usize {
    bits & 0b111
}

fn bits_to_bytes(bits: usize) -> usize {
    (bits + 7) >> 3
}

fn get_fill(is_negative: bool) -> u8 {
    if is_negative {
        0xFF
    } else {
        0
    }
}

fn extend_buffer_be(mut bytes: Vec<u8>, bits: usize, is_negative: bool) -> Vec<u8> {
    let new_len = bits_to_bytes(bits);
    if new_len > bytes.len() {
        let mut new_bytes = vec![get_fill(is_negative); new_len - bytes.len()];
        new_bytes.append(&mut bytes);
        new_bytes
    } else {
        bytes
    }
}

pub(crate) fn dump_cell_generic(cell: Cell, ctor_name: &str, tab: &str) -> String {
    enum Phase {
        // dump indentation, ctor heading and data string
        Pre(Cell, usize),
        // dump closing brackets
        Post
    }
    let mut output = String::new();
    let mut stack = vec!(Phase::Pre(cell, 0));
    while let Some(phase) = stack.pop() {
        match phase {
            Phase::Pre(cell, indent) => {
                output += &format!("{}{}(\"{}\"",
                    tab.repeat(indent),
                    ctor_name,
                    cell.to_hex_string(true)
                );
                if cell.references_count() > 0 {
                    output += ",\n";
                }
                stack.push(Phase::Post);
                for i in (0..cell.references_count()).rev() {
                    let child = cell.reference(i).unwrap();
                    stack.push(Phase::Pre(child, indent + 1));
                }
            }
            Phase::Post => {
                output += ")";
                if let Some(Phase::Pre(_, _)) = stack.last() {
                    output += ",\n";
                }
            }
        }
    }
    output
}

pub(crate) fn dump_cell(cell: Cell) -> String {
    // standard python indentation is 4 spaces
    dump_cell_generic(cell, "C", "    ")
}

pub(crate) fn convert_to_vm(value: &PyAny) -> PyResult<StackItem> {
    if value.is_none() {
        Ok(StackItem::None)
    } else if let Ok(v) = value.downcast::<PyLong>() {
        let integer = IntegerData::from(v.extract::<BigInt>()?)
            .map_err(runtime_err)?;
        Ok(StackItem::Integer(Arc::new(integer)))
    } else if let Ok(_) = value.extract::<crate::PyNaN>() {
        Ok(StackItem::Integer(Arc::new(IntegerData::nan())))
    } else if let Ok(v) = value.downcast::<PyList>() {
        let mut tuple = Vec::new();
        for item in v {
            tuple.push(convert_to_vm(item)?)
        }
        Ok(StackItem::Tuple(Arc::new(tuple)))
    } else if let Ok(v) = value.extract::<PyCell>() {
        Ok(StackItem::Cell(v.cell))
    } else if let Ok(v) = value.extract::<PySlice>() {
        Ok(StackItem::Slice(v.slice))
    } else if let Ok(v) = value.extract::<PyBuilder>() {
        Ok(StackItem::Builder(Arc::new(v.builder)))
    } else if let Ok(v) = value.extract::<PyContinuation>() {
        Ok(StackItem::Continuation(Arc::new(v.cont(value.py())?)))
    } else {
        return err!("unsupported value {}", value)
    }
}

pub(crate) fn convert_from_vm(py: Python<'_>, item: &StackItem) -> PyResult<PyObject> {
    match item {
        StackItem::None =>
            Ok(py.None()),
        StackItem::Builder(v) =>
            Ok(PyBuilder::new(v.as_ref().clone()).into_py(py)),
        StackItem::Cell(v) =>
            Ok(crate::PyCell::new(v.clone()).into_py(py)),
        StackItem::Continuation(cont) =>
            Ok(PyContinuation::new(py, cont.as_ref())?.into_py(py)),
        StackItem::Integer(v) => {
            match process_value(v.as_ref(), |v| Ok(v.clone())) {
                Err(_) => Ok(PyNaN::new().into_py(py)),
                Ok(v) => Ok(v.into_py(py)),
            }
        }
        StackItem::Slice(v) =>
            Ok(PySlice::new(v.clone()).into_py(py)),
        StackItem::Tuple(v) => {
            let mut list = Vec::new();
            for item in v.iter() {
                list.push(convert_from_vm(py, item)?)
            }
            Ok(PyList::new(py, list).into_py(py))
        }
    }
}
