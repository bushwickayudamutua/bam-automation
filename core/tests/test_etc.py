from bam_core.utils.etc import to_list

def test_to_list():
    assert [1] == to_list(1)
    assert [1] == to_list([1])
