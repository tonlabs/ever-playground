use crate::{PyContinuation, PySaveList, convert_from_vm, runtime_err};
use pyo3::{
    prelude::*,
    exceptions::PyRuntimeError,
};
use ton_vm::{
    error::tvm_exception_full,
    executor::{Engine, EngineTraceInfo, gas::gas_state::Gas},
};

#[derive(Clone)]
#[pyclass(name = "Gas")]
pub(crate) struct PyGas {
    gas: Gas,
}

impl Default for PyGas {
    fn default() -> Self {
        Self { gas: Gas::empty() }
    }
}

impl PyGas {
    fn new(gas: Gas) -> Self {
        Self { gas }
    }
}

#[pymethods]
impl PyGas {
    #[new]
    fn create(limit: i64, credit: i64) -> Self {
        Self::new(Gas::new(limit, credit, 1000000000, 10))
    }
    #[getter]
    fn limit(&self) -> i64 {
        self.gas.get_gas_limit()
    }
    #[getter]
    fn used(&self) -> i64 {
        self.gas.get_gas_used()
    }
    #[getter]
    fn credit(&self) -> i64 {
        self.gas.get_gas_credit()
    }
}

#[derive(Clone, Default)]
#[pyclass(get_all, name = "VmState")]
pub(crate) struct PyVmState {
    cc: PyContinuation,
    regs: PySaveList,
    steps: u32,
    gas: PyGas,
    committed_c4: Option<crate::PyCell>,
    committed_c5: Option<crate::PyCell>,
}

impl PyVmState {
    fn new(
        cc: PyContinuation,
        regs: PySaveList,
        steps: u32,
        gas: PyGas,
        committed_c4: Option<crate::PyCell>,
        committed_c5: Option<crate::PyCell>
    ) -> Self {
        Self { cc, regs, steps, gas, committed_c4, committed_c5 }
    }
}

#[pymethods]
impl PyVmState {
    #[new]
    fn create(
        cc: PyContinuation,
        regs: PySaveList,
        gas: PyGas,
    ) -> Self {
        Self::new(cc, regs, 0, gas, None, None)
    }
}

#[derive(Default)]
#[pyclass(get_all, name = "VmResult")]
pub(crate) struct PyVmResult {
    state: PyVmState,
    exit_code: i32,
    exception_value: Option<PyObject>,
}

#[pyfunction]
pub(crate) fn runvm_generic(py: Python<'_>, state: PyVmState, capabilities: u64, trace: bool) -> PyResult<PyObject> {
    let mut engine = Engine::with_capabilities(capabilities).setup(
        state.cc.cont.code().clone(),
        Some(state.regs.savelist),
        Some(state.cc.cont.stack),
        Some(state.gas.gas)
    );
    if trace {
        engine.set_trace_callback(trace_callback);
    }
    let mut result = PyVmResult::default();
    match engine.execute() {
        Ok(exit_code) => result.exit_code = exit_code,
        Err(err) => if let Some(exception) = tvm_exception_full(&err) {
            result.exit_code = exception.exception_or_custom_code();
            result.exception_value = Some(convert_from_vm(py, &exception.value));
        } else {
            return Err(PyRuntimeError::new_err(format!("execution failed: {}", err)))
        }
    }

    let committed_state = engine.get_committed_state();
    let (committed_c4, committed_c5) = if committed_state.is_committed() {
        let c4 = committed_state.get_root();
        let c5 = committed_state.get_actions();
        let c4 = c4.as_cell().map_err(runtime_err)?.clone();
        let c5 = c5.as_cell().map_err(runtime_err)?.clone();
        (Some(crate::PyCell::new(c4)), Some(crate::PyCell::new(c5)))
    } else {
        (None, None)
    };

    result.state = PyVmState::new(
        PyContinuation::new(engine.cc().clone()),
        PySaveList::new(engine.ctrls().clone()),
        engine.steps(),
        PyGas::new(engine.get_gas().clone()),
        committed_c4,
        committed_c5,
    );
    Ok(result.into_py(py))
}

fn trace_callback(_engine: &Engine, info: &EngineTraceInfo) {
    use ton_vm::executor::EngineTraceInfoType::*;
    match &info.info_type {
        Start => { }
        Dump => println!("DUMP {}", info.cmd_str),
        typ => {
            if *typ == Exception {
                println!("EXCEPTION")
            }
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
