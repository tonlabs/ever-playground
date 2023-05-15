use num_bigint::{BigInt, BigUint, Sign};
use pyo3::{
    prelude::PyResult,
    PyErr,
    exceptions::PyRuntimeError,
};

use ton_types::Cell as InternalCell;

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

pub(crate) fn dump_cell_generic(cell: InternalCell, ctor_name: &str, tab: &str) -> String {
    enum Phase {
        // dump indentation, ctor heading and data string
        Pre(InternalCell, usize),
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

pub(crate) fn dump_cell(cell: InternalCell) -> String {
    // standard python indentation is 4 spaces
    dump_cell_generic(cell, "C", "    ")
}
