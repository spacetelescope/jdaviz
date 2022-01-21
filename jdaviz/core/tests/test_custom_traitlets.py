import pytest
from traitlets import HasTraits, TraitError

from jdaviz.core.custom_traitlets import IntHandleEmpty, FloatHandleEmpty


class Foo(HasTraits):
    int_handle_empty = IntHandleEmpty(0)
    int_handle_empty_replace = IntHandleEmpty(0, replace_with_default=True)
    float_handle_empty = FloatHandleEmpty()


def test_inthandleempty():
    foo = Foo()

    foo.int_handle_empty = 1
    foo.int_handle_empty = ''
    assert foo.int_handle_empty == ''
    with pytest.raises(
            TraitError,
            match=r"The 'int_handle_empty' trait of a Foo instance expected an int, not the str 'blah'\."):  # noqa
        foo.int_handle_empty = 'blah'

    foo.int_handle_empty_replace = 1
    foo.int_handle_empty_replace = ''
    assert foo.int_handle_empty_replace == 0

    foo.float_handle_empty = 1.2
