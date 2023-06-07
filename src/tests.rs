#![cfg(test)]

use crate::dump_cell;
use ton_types::{Cell, SliceData};

fn __(data: &str, refs: Vec<Cell>) -> ton_types::Result<Cell> {
    let mut b = SliceData::from_string(data)?.as_builder();
    for r in refs {
        b.checked_append_reference(r)?;
    }
    b.into_cell()
}

macro_rules! __ {
    ($data:literal) => {
        __($data, vec!())?
    };
    ($data:literal, $($arg:tt)+) => {
        __($data, vec!($($arg)+))?
    };
}

#[test]
fn test_dump_cell() -> ton_types::Status {
    let c1 = __!("c_");
    assert_eq!(dump_cell(c1), r#"C("c_")"#);

    let c2 =
      __!("8abc5_",
        __!("c_",
          __!("bc"),
          __!("45333ac9_",
            __!("c0feebabe")),
          __!("b_")),
        __!("deadbeef"),
        __!("1",
          __!("2",
            __!("3"))));
    assert_eq!(dump_cell(c2), r#"C("8abc5_",
  C("c_",
    C("bc"),
    C("45333ac9_",
      C("c0feebabe")),
    C("b_")),
  C("deadbeef"),
  C("1",
    C("2",
      C("3"))))"#);

    Ok(())
}
