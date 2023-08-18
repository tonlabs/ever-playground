use crate::{err, PySlice, runtime_err, utils::{convert_from_vm, convert_to_vm}};
use pyo3::{
    prelude::*,
    basic::CompareOp,
    types::PyList,
    exceptions::PyRuntimeError,
};
use ton_vm::stack::{
    continuation::{ContinuationData, ContinuationType},
    savelist::SaveList
};

#[derive(Clone, Default)]
#[pyclass(name = "SaveList")]
pub(crate) struct PySaveList {
    pub(crate) savelist: SaveList
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
        convert_from_vm(py, item).ok()
    }
    fn put(&mut self, py: Python<'_>, index: usize, value: PyObject) -> PyResult<()> {
        let mut item = convert_to_vm(value.as_ref(py))?;
        self.savelist.put(index, &mut item).map(|_| ()).map_err(runtime_err)
    }
    fn __richcmp__(&self, other: Self, op: CompareOp, py: Python<'_>) -> PyObject {
        match op {
            CompareOp::Eq => self.savelist.eq(&other.savelist).into_py(py),
            CompareOp::Ne => self.savelist.ne(&other.savelist).into_py(py),
            _ => py.NotImplemented(),
        }
    }
    fn __str__(&self) -> PyResult<String> {
        let mut res = String::new();
        let mut empty = true;
        for i in SaveList::REGS {
            if self.savelist.get(i).is_some() {
                if !empty {
                    res += " ";
                } else {
                    empty = false;
                }
                res += &format!("c{}", i);
            }
        }
        if empty {
            res += "empty";
        }
        Ok(res)
    }
}

#[derive(Clone, Default)]
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
    Again       = 0,
    TryCatch    = 1,
    CatchRevert = 2,
    Ordinary    = 3,
    PushInt     = 4,
    Quit        = 5,
    Repeat      = 6,
    Until       = 7,
    While       = 8,
    ExcQuit     = 9,
}

#[pymethods]
impl PyContinuationType {
    #[getter]
    fn variant(&self) -> u8 {
        use ContinuationType::*;
        match self.typ {
            AgainLoopBody(_)         => ContinuationVariant::Again       as u8,
            TryCatch                 => ContinuationVariant::TryCatch    as u8,
            CatchRevert(_)           => ContinuationVariant::CatchRevert as u8,
            Ordinary                 => ContinuationVariant::Ordinary    as u8,
            PushInt(_)               => ContinuationVariant::PushInt     as u8,
            Quit(_)                  => ContinuationVariant::Quit        as u8,
            RepeatLoopBody(_, _)     => ContinuationVariant::Repeat      as u8,
            UntilLoopCondition(_)    => ContinuationVariant::Until       as u8,
            WhileLoopCondition(_, _) => ContinuationVariant::While       as u8,
            ExcQuit                  => ContinuationVariant::ExcQuit     as u8,
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
    fn __richcmp__(&self, other: Self, op: CompareOp, py: Python<'_>) -> PyObject {
        match op {
            CompareOp::Eq => self.typ.eq(&other.typ).into_py(py),
            CompareOp::Ne => self.typ.ne(&other.typ).into_py(py),
            _ => py.NotImplemented(),
        }
    }
    fn __str__(&self) -> PyResult<String> {
        use ContinuationType::*;
        let str = match self.typ {
            AgainLoopBody(_)         => "Again",
            TryCatch                 => "TryCatch",
            CatchRevert(_)           => "CatchRevert",
            Ordinary                 => "Ordinary",
            PushInt(_)               => "PushInt",
            Quit(_)                  => "Quit",
            RepeatLoopBody(_, _)     => "Repeat",
            UntilLoopCondition(_)    => "Until",
            WhileLoopCondition(_, _) => "While",
            ExcQuit                  => "ExcQuit",
        };
        Ok(str.to_string())
    }
}

#[derive(Clone)]
#[pyclass(name = "Continuation", get_all, set_all)]
pub(crate) struct PyContinuation {
    typ: Py<PyContinuationType>,
    code: Py<PySlice>,
    stack: PyObject,
    savelist: Py<PySaveList>,
    nargs: PyObject,
}

impl PyContinuation {
    pub(crate) fn new(py: Python<'_>, cont: &ContinuationData) -> PyResult<Self> {
        let typ = PyContinuationType::new(cont.type_of.clone());
        let code = PySlice::new(cont.code().clone());
        let mut stack = Vec::new();
        for item in cont.stack.iter() {
            stack.push(convert_from_vm(py, item)?)
        }
        let savelist = PySaveList::new(cont.savelist.clone());
        Ok(Self {
            typ: Py::new(py, typ)?,
            code: Py::new(py, code)?,
            stack: PyList::new(py, stack).to_object(py),
            savelist: Py::new(py, savelist)?,
            nargs: cont.nargs.to_object(py),
        })
    }
    pub(crate) fn cont(&self, py: Python<'_>) -> PyResult<ContinuationData> {
        let mut cont = ContinuationData::with_type(
            self.typ.extract::<PyContinuationType>(py)?.typ);
        *cont.code_mut() = self.code.extract::<PySlice>(py)?.slice;
        for v in self.stack.extract::<&PyList>(py)? {
            cont.stack.push(convert_to_vm(v)?);
        }
        cont.savelist = self.savelist.extract::<PySaveList>(py)?.savelist;
        cont.nargs = self.nargs.extract::<isize>(py)?;
        Ok(cont)
    }
}

#[pymethods]
impl PyContinuation {
    #[new]
    #[pyo3(signature = (
        typ = PyContinuationType::default(),
        code = PySlice::default(),
        stack = Vec::new(),
        savelist = PySaveList::default(),
        nargs = -1,
    ))]
    fn create(
        py: Python<'_>,
        typ: PyContinuationType,
        code: PySlice,
        stack: Vec<PyObject>,
        savelist: PySaveList,
        nargs: isize,
    ) -> PyResult<Self> {
        Ok(Self {
            typ: Py::new(py, typ)?,
            code: Py::new(py, code)?,
            stack: PyList::new(py, stack).to_object(py),
            savelist: Py::new(py, savelist)?,
            nargs: nargs.to_object(py),
        })
    }
    fn __richcmp__(&self, other: Self, op: CompareOp, py: Python<'_>) -> PyObject {
        let self_cont = if let Ok(c) = self.cont(py) {
            c
        } else {
            return false.to_object(py)
        };
        let other_cont = if let Ok(c) = other.cont(py) {
            c
        } else {
            return false.to_object(py)
        };
        match op {
            CompareOp::Eq => self_cont.eq(&other_cont).into_py(py),
            CompareOp::Ne => self_cont.ne(&other_cont).into_py(py),
            _ => py.NotImplemented(),
        }
    }
    fn __str__(&self, py: Python<'_>) -> PyResult<String> {
        Ok(self.cont(py)?.to_string())
    }
}
