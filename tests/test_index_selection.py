from new_music_builder.services.index_selection import apply_index_selection


def test_apply_index_selection_single_selects_one() -> None:
    selected, anchor = apply_index_selection(set(), None, 2, 6, shift=False, additive=False)
    assert selected == {2}
    assert anchor == 2


def test_apply_index_selection_ctrl_toggles_membership() -> None:
    selected, anchor = apply_index_selection({1, 3}, 3, 1, 6, shift=False, additive=True)
    assert selected == {3}
    assert anchor == 1


def test_apply_index_selection_shift_selects_range_from_anchor() -> None:
    selected, anchor = apply_index_selection({2}, 2, 5, 8, shift=True, additive=False)
    assert selected == {2, 3, 4, 5}
    assert anchor == 2
