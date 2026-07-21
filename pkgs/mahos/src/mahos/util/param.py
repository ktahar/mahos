#!/usr/bin/env python3

"""
Parameter validation and access utilities.

.. This file is a part of MAHOS project, which is released under the 3-Clause BSD license.
.. See included LICENSE file or https://github.com/ToyotaCRDL/mahos/blob/main/LICENSE for details.

"""

from __future__ import annotations

from collections.abc import Mapping
import math
from typing import Any, overload


_MISSING = object()


class ParamError(ValueError):
    """Error raised for a missing or invalid parameter."""


class ParamAccessor:
    """Provide validated access to an unwrapped parameter mapping."""

    def __init__(self, params: Mapping[str, Any], prefix: str = ""):
        self._params = params
        self._prefix = prefix

    def _path(self, key: str) -> str:
        return f"{self._prefix}.{key}" if self._prefix else key

    def _get(self, key: str, default: object = _MISSING) -> tuple[str, Any]:
        path = self._path(key)
        if key in self._params:
            return path, self._params[key]
        if default is not _MISSING:
            return path, default
        raise ParamError(f"Required parameter {path} is missing.")

    def _raise_invalid(self, path: str, expected: str, value: Any) -> None:
        raise ParamError(f"{path} must be {expected}. Got {type(value).__name__}: {value!r}")

    def _numbers(
        self, key: str, length: int, default: object = _MISSING
    ) -> tuple[float | int, ...]:
        if length <= 0:
            raise ValueError(f"length must be positive. Got {length}")
        path, value = self._get(key, default)
        if not isinstance(value, (list, tuple)) or len(value) != length:
            self._raise_invalid(path, f"list or tuple of {length} numbers", value)

        numbers = []
        for i, elem in enumerate(value):
            elem_path = f"{path}[{i}]"
            if isinstance(elem, bool) or not isinstance(elem, (float, int)):
                self._raise_invalid(elem_path, "finite number", elem)
            if isinstance(elem, float) and not math.isfinite(elem):
                self._raise_invalid(elem_path, "finite number", elem)
            numbers.append(elem)
        return tuple(numbers)

    def __contains__(self, key: object) -> bool:
        return key in self._params

    def get(self, key: str, default: object = None) -> Any:
        """Return an unvalidated parameter value."""

        return self._params.get(key, default)

    @overload
    def str(self, key: str) -> str: ...

    @overload
    def str(self, key: str, default: str) -> str: ...

    def str(self, key: str, default: object = _MISSING) -> str:
        """Return a string parameter."""

        path, value = self._get(key, default)
        if not isinstance(value, str):
            self._raise_invalid(path, "str", value)
        return value

    @overload
    def bool(self, key: str) -> bool: ...

    @overload
    def bool(self, key: str, default: bool) -> bool: ...

    def bool(self, key: str, default: object = _MISSING) -> bool:
        """Return a boolean parameter."""

        path, value = self._get(key, default)
        if not isinstance(value, bool):
            self._raise_invalid(path, "bool", value)
        return value

    @overload
    def int(self, key: str) -> int: ...

    @overload
    def int(self, key: str, default: int) -> int: ...

    def int(self, key: str, default: object = _MISSING) -> int:
        """Return an integer parameter, rejecting booleans."""

        path, value = self._get(key, default)
        if isinstance(value, bool) or not isinstance(value, int):
            self._raise_invalid(path, "int", value)
        return value

    @overload
    def pos_int(self, key: str) -> int: ...

    @overload
    def pos_int(self, key: str, default: int) -> int: ...

    def pos_int(self, key: str, default: object = _MISSING) -> int:
        """Return a positive integer parameter, rejecting booleans."""

        path, value = self._get(key, default)
        if isinstance(value, bool) or not isinstance(value, int):
            self._raise_invalid(path, "positive int", value)
        if value <= 0:
            self._raise_invalid(path, "positive int", value)
        return value

    @overload
    def nonneg_int(self, key: str) -> int: ...

    @overload
    def nonneg_int(self, key: str, default: int) -> int: ...

    def nonneg_int(self, key: str, default: object = _MISSING) -> int:
        """Return a non-negative integer parameter, rejecting booleans."""

        path, value = self._get(key, default)
        if isinstance(value, bool) or not isinstance(value, int):
            self._raise_invalid(path, "non-negative int", value)
        if value < 0:
            self._raise_invalid(path, "non-negative int", value)
        return value

    @overload
    def num(self, key: str) -> float | int: ...

    @overload
    def num(self, key: str, default: float | int) -> float | int: ...

    def num(self, key: str, default: object = _MISSING) -> float | int:
        """Return a finite numeric parameter, rejecting booleans."""

        path, value = self._get(key, default)
        if isinstance(value, bool) or not isinstance(value, (float, int)):
            self._raise_invalid(path, "finite number", value)
        if isinstance(value, float) and not math.isfinite(value):
            self._raise_invalid(path, "finite number", value)
        return value

    @overload
    def pos_num(self, key: str) -> float | int: ...

    @overload
    def pos_num(self, key: str, default: float | int) -> float | int: ...

    def pos_num(self, key: str, default: object = _MISSING) -> float | int:
        """Return a positive finite numeric parameter, rejecting booleans."""

        path, value = self._get(key, default)
        if (
            isinstance(value, bool)
            or not isinstance(value, (float, int))
            or isinstance(value, float)
            and not math.isfinite(value)
        ):
            self._raise_invalid(path, "positive finite number", value)
        if value <= 0:
            self._raise_invalid(path, "positive finite number", value)
        return value

    @overload
    def nonneg_num(self, key: str) -> float | int: ...

    @overload
    def nonneg_num(self, key: str, default: float | int) -> float | int: ...

    def nonneg_num(self, key: str, default: object = _MISSING) -> float | int:
        """Return a non-negative finite numeric parameter, rejecting booleans."""

        path, value = self._get(key, default)
        if (
            isinstance(value, bool)
            or not isinstance(value, (float, int))
            or isinstance(value, float)
            and not math.isfinite(value)
        ):
            self._raise_invalid(path, "non-negative finite number", value)
        if value < 0:
            self._raise_invalid(path, "non-negative finite number", value)
        return value

    @overload
    def ascending_numbers(self, key: str, length: int) -> tuple[float | int, ...]: ...

    @overload
    def ascending_numbers(
        self,
        key: str,
        length: int,
        default: list[float | int] | tuple[float | int, ...],
    ) -> tuple[float | int, ...]: ...

    def ascending_numbers(
        self, key: str, length: int, default: object = _MISSING
    ) -> tuple[float | int, ...]:
        """Return a fixed-length sequence of strictly ascending finite numbers."""

        numbers = self._numbers(key, length, default)
        if any(a >= b for a, b in zip(numbers, numbers[1:])):
            self._raise_invalid(self._path(key), "strictly ascending numbers", numbers)
        return numbers

    @overload
    def descending_numbers(self, key: str, length: int) -> tuple[float | int, ...]: ...

    @overload
    def descending_numbers(
        self,
        key: str,
        length: int,
        default: list[float | int] | tuple[float | int, ...],
    ) -> tuple[float | int, ...]: ...

    def descending_numbers(
        self, key: str, length: int, default: object = _MISSING
    ) -> tuple[float | int, ...]:
        """Return a fixed-length sequence of strictly descending finite numbers."""

        numbers = self._numbers(key, length, default)
        if any(a <= b for a, b in zip(numbers, numbers[1:])):
            self._raise_invalid(self._path(key), "strictly descending numbers", numbers)
        return numbers

    @overload
    def child(self, key: str) -> "ParamAccessor": ...

    @overload
    def child(self, key: str, default: Mapping[str, Any]) -> "ParamAccessor": ...

    def child(self, key: str, default: object = _MISSING) -> "ParamAccessor":
        """Return an accessor for a nested mapping, preserving its full path."""

        path, value = self._get(key, default)
        if not isinstance(value, Mapping):
            self._raise_invalid(path, "mapping", value)
        return ParamAccessor(value, path)
