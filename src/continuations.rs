use crate::{
    err, PySlice,
    utils::{convert_from_vm, convert_to_vm, runtime_err},
};
use pyo3::{
    prelude::*,
    types::PyList,
    exceptions::PyRuntimeError,
};
use ton_vm::stack::{
    continuation::{ContinuationData, ContinuationType},
    savelist::SaveList
};

#[derive(Clone)]
#[pyclass(name = "SaveList")]
pub(crate) struct PySaveList {
    pub(crate) savelist: SaveList
}

impl Default for PySaveList {
    fn default() -> Self {
        Self { savelist: SaveList::new() }
    }
}

impl PySaveList {
    pub(crate) fn new(savelist: SaveList) -> Self {
        Self { savelist }
    }
}

#[pymethods]
impl PySaveList {
    #[new]
    fn create() -> Self {
        Self::default()
    }
    fn get(&self, py: Python<'_>, index: usize) -> Option<PyObject> {
        let item = self.savelist.get(index)?;
        Some(convert_from_vm(py, item))
    }
    fn put(&mut self, py: Python<'_>, index: usize, value: PyObject) -> PyResult<()> {
        let mut item = convert_to_vm(value.as_ref(py))?;
        self.savelist.put(index, &mut item).map(|_| ()).map_err(runtime_err)
    }
}

#[derive(Clone)]
#[pyclass(name = "ContinuationType")]
pub(crate) struct PyContinuationType {
    typ: ContinuationType
}

impl PyContinuationType {
    fn new(typ: ContinuationType) -> Self {
        Self { typ }
    }
}

// Must be in sync with python code
enum ContinuationVariant {
    Again    = 0,
    TryCatch = 1,
    Ordinary = 2,
    PushInt  = 3,
    Quit     = 4,
    Repeat   = 5,
    Until    = 6,
    While    = 7,
    ExcQuit  = 8,
}

#[pymethods]
impl PyContinuationType {
    #[getter]
    fn variant(&self) -> u8 {
        use ContinuationType::*;
        match self.typ {
            AgainLoopBody(_)         => ContinuationVariant::Again    as u8,
            TryCatch                 => ContinuationVariant::TryCatch as u8,
            Ordinary                 => ContinuationVariant::Ordinary as u8,
            PushInt(_)               => ContinuationVariant::PushInt  as u8,
            Quit(_)                  => ContinuationVariant::Quit     as u8,
            RepeatLoopBody(_, _)     => ContinuationVariant::Repeat   as u8,
            UntilLoopCondition(_)    => ContinuationVariant::Until    as u8,
            WhileLoopCondition(_, _) => ContinuationVariant::While    as u8,
            ExcQuit                  => ContinuationVariant::ExcQuit  as u8,
        }
    }
    fn params_again(&self) -> PyResult<PySlice> {
        let ContinuationType::AgainLoopBody(body) = &self.typ
            else { return err!("wrong continuation type") };
        Ok(PySlice::new(body.clone()))
    }
    fn params_pushint(&self) -> PyResult<i32> {
        let ContinuationType::PushInt(value) = &self.typ
            else { return err!("wrong continuation type") };
        Ok(*value)
    }
    fn params_quit(&self) -> PyResult<i32> {
        let ContinuationType::Quit(exit_code) = &self.typ
            else { return err!("wrong continuation type") };
        Ok(*exit_code)
    }
    fn params_repeat(&self) -> PyResult<(PySlice, isize)> {
        let ContinuationType::RepeatLoopBody(body, counter) = &self.typ
            else { return err!("wrong continuation type") };
        Ok((PySlice::new(body.clone()), *counter))
    }
    fn params_until(&self) -> PyResult<PySlice> {
        let ContinuationType::UntilLoopCondition(body) = &self.typ
            else { return err!("wrong continuation type") };
        Ok(PySlice::new(body.clone()))
    }
    fn params_while(&self) -> PyResult<(PySlice, PySlice)> {
        let ContinuationType::WhileLoopCondition(body, cond) = &self.typ
            else { return err!("wrong continuation type") };
        Ok((PySlice::new(body.clone()), PySlice::new(cond.clone())))
    }
    #[staticmethod]
    fn create_again(body: PySlice) -> Self {
        Self::new(ContinuationType::AgainLoopBody(body.slice))
    }
    #[staticmethod]
    fn create_trycatch() -> Self {
        Self::new(ContinuationType::TryCatch)
    }
    #[staticmethod]
    fn create_ordinary() -> Self {
        Self::new(ContinuationType::Ordinary)
    }
    #[staticmethod]
    fn create_pushint(value: i32) -> Self {
        Self::new(ContinuationType::PushInt(value))
    }
    #[staticmethod]
    fn create_quit(exit_code: i32) -> Self {
        Self::new(ContinuationType::Quit(exit_code))
    }
    #[staticmethod]
    fn create_repeat(body: PySlice, counter: isize) -> Self {
        Self::new(ContinuationType::RepeatLoopBody(body.slice, counter))
    }
    #[staticmethod]
    fn create_until(body: PySlice) -> Self {
        Self::new(ContinuationType::UntilLoopCondition(body.slice))
    }
    #[staticmethod]
    fn create_while(body: PySlice, cond: PySlice) -> Self {
        Self::new(ContinuationType::WhileLoopCondition(body.slice, cond.slice))
    }
    #[staticmethod]
    fn create_excquit() -> Self {
        Self::new(ContinuationType::ExcQuit)
    }
}

#[derive(Clone)]
#[pyclass(name = "Continuation")]
pub(crate) struct PyContinuation {
    pub(crate) cont: ContinuationData
}

impl Default for PyContinuation {
    fn default() -> Self {
        Self { cont: ContinuationData::new_empty() }
    }
}

impl PyContinuation {
    pub(crate) fn new(cont: ContinuationData) -> Self {
        Self { cont }
    }
}

#[pymethods]
impl PyContinuation {
    #[new]
    fn create(
        typ: PyContinuationType,
        code: PySlice,
        stack: &PyList,
        savelist: PySaveList,
        nargs: isize,
    ) -> PyResult<Self> {
        let mut cdata = ContinuationData::with_type(typ.typ);
        *cdata.code_mut() = code.slice;
        for item in stack.iter() {
            cdata.stack.push(convert_to_vm(item)?);
        }
        cdata.savelist = savelist.savelist;
        cdata.nargs = nargs;
        Ok(Self::new(cdata))
    }
    #[getter]
    fn typ(&self) -> PyContinuationType {
        PyContinuationType::new(self.cont.type_of.clone())
    }
    #[getter]
    fn code(&self) -> PySlice {
        PySlice::new(self.cont.code().clone())
    }
    #[getter]
    fn stack(&self, py: Python<'_>) -> PyObject {
        let mut stack = Vec::new();
        for item in self.cont.stack.iter() {
            stack.push(convert_from_vm(py, item))
        }
        PyList::new(py, stack).to_object(py)
    }
    #[getter]
    fn savelist(&self) -> PySaveList {
        PySaveList::new(self.cont.savelist.clone())
    }
    #[getter]
    fn nargs(&self) -> isize {
        self.cont.nargs
    }
}
