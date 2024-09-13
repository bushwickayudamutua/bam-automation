from bam_core.utils.etc import to_list, to_bool


def test_to_list():
    assert [1] == to_list(1)
    assert [1] == to_list([1])


def test_to_bool():
    assert to_bool("y") == True
    assert to_bool("yes") == True
    assert to_bool("t") == True
    assert to_bool("true") == True
    assert to_bool("TRUE") == True
    assert to_bool(True) == True
    assert to_bool(False) == False
    assert to_bool("n") == False
    assert to_bool("no") == False
    assert to_bool("f") == False
    assert to_bool("false") == False
    assert to_bool("FALSE") == False
