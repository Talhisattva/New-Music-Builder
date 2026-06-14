from __future__ import annotations


def apply_index_selection(
    current_selected: set[int],
    current_anchor: int | None,
    target_index: int,
    item_count: int,
    *,
    shift: bool,
    additive: bool,
) -> tuple[set[int], int | None]:
    if target_index < 0 or target_index >= item_count:
        return set(current_selected), current_anchor

    if shift:
        if current_anchor is None:
            return {target_index}, target_index
        start = min(current_anchor, target_index)
        end = max(current_anchor, target_index)
        return set(range(start, end + 1)), current_anchor

    if additive:
        updated = set(current_selected)
        if target_index in updated:
            updated.remove(target_index)
        else:
            updated.add(target_index)
        return updated, target_index

    if current_selected == {target_index}:
        return set(current_selected), target_index
    return {target_index}, target_index
