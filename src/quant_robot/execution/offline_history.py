"""Share immutable historical payloads inside journal projections only.

Public reads are expanded to ordinary mutable containers. A late event copies
its affected terminal order before changing it; nothing is removed from history.
"""
from copy import deepcopy
from decimal import Decimal


def _readonly(*_args, **_kwargs):
    raise TypeError('immutable historical record')


class _FrozenDict(dict):
    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = __ior__ = _readonly

    def __deepcopy__(self, memo):
        return self


class _FrozenList(list):
    __setitem__ = __delitem__ = __iadd__ = __imul__ = append = extend = insert = pop = remove = clear = reverse = sort = _readonly

    def __deepcopy__(self, memo):
        return self


class _FrozenSet(frozenset):
    def __deepcopy__(self, memo):
        return self


_ATOMIC = (str, int, float, bool, type(None), Decimal)
_FROZEN = (_FrozenDict, _FrozenList, _FrozenSet)


def freeze_record(value):
    if type(value) in _ATOMIC or isinstance(value, _FROZEN):
        return value
    if isinstance(value, dict):
        return _FrozenDict({key: freeze_record(item) for key, item in value.items()})
    if isinstance(value, list):
        return _FrozenList(freeze_record(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return _FrozenSet(freeze_record(item) for item in value)
    if isinstance(value, tuple):
        return tuple(freeze_record(item) for item in value)
    raise TypeError('unsupported historical record value')


def mutable_copy(value):
    """Return an editable isolated snapshot, including formerly shared records."""
    if type(value) in _ATOMIC:
        return value
    if isinstance(value, dict):
        return {key: mutable_copy(item) for key, item in value.items()}
    if isinstance(value, list):
        return [mutable_copy(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return {mutable_copy(item) for item in value}
    if isinstance(value, tuple):
        return tuple(mutable_copy(item) for item in value)
    return deepcopy(value)


def seal_history(state):
    for key, row in state['orders'].items():
        if row['status'] in {'FILLED', 'CANCELLED', 'REJECTED'}:
            state['orders'][key] = freeze_record(row)
    for key, row in state['receipts'].items():
        state['receipts'][key] = freeze_record(row)
    return state


def mutable_order(state, key):
    row = state['orders'][key]
    if isinstance(row, _FrozenDict):
        row = mutable_copy(row)
        state['orders'][key] = row
    return row
