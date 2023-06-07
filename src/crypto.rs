use ed25519_dalek::Signer;
use pyo3::{
    prelude::*,
    exceptions::PyRuntimeError,
    types::{PyBytes, PyTuple},
};

#[pyfunction]
pub(crate) fn ed25519_new_keypair<'a>(py: Python<'a>) -> PyResult<&PyTuple> {
    let mut csprng = rand::thread_rng();
    let keypair = ed25519_dalek::Keypair::generate(&mut csprng);
    Ok(PyTuple::new(py, vec!(
        PyBytes::new(py, keypair.secret.as_bytes()),
        PyBytes::new(py, keypair.public.as_bytes()),
    )))
}

pub(crate) fn load_secret(secret: &PyBytes) -> PyResult<ed25519_dalek::SecretKey> {
    let secret = ed25519_dalek::SecretKey::from_bytes(secret.as_bytes())
        .map_err(|err| PyRuntimeError::new_err(format!("invalid secret bytes: {}", err)))?;
    Ok(secret)
}

#[pyfunction]
pub(crate) fn ed25519_secret_to_public<'a>(secret: &'a PyBytes, py: Python<'a>) -> PyResult<&'a PyBytes> {
    let secret = load_secret(secret)?;
    let public = ed25519_dalek::PublicKey::from(&secret);
    Ok(PyBytes::new(py, public.as_bytes()))
}

#[pyfunction]
pub(crate) fn ed25519_sign<'a>(data: &'a PyBytes, secret: &'a PyBytes, py: Python<'a>) -> PyResult<&'a PyBytes> {
    let secret = load_secret(secret)?;
    let public = ed25519_dalek::PublicKey::from(&secret);
    let keypair = ed25519_dalek::Keypair { secret, public };
    let signature = keypair.sign(data.as_bytes()).to_bytes();
    Ok(PyBytes::new(py, &signature[..]))
}

#[pyfunction]
pub(crate) fn ed25519_check_signature<'a>(data: &'a PyBytes, signature: &'a PyBytes, public: &'a PyBytes) -> bool {
    let Ok(public) = ed25519_dalek::PublicKey::from_bytes(public.as_bytes()) else { return false };
    let Ok(signature) = ed25519_dalek::Signature::from_bytes(signature.as_bytes()) else { return false };
    public.verify_strict(data.as_bytes(), &signature).is_ok()
}
