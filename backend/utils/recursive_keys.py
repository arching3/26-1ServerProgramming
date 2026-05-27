"""Utilities for recursively printing dictionary keys."""

from __future__ import annotations

from typing import Any


def _list_dict_keys(data: list[Any]) -> dict[str, Any]:
    keys: dict[str, Any] = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        for key, value in item.items():
            keys.setdefault(key, value)
    return keys


def print_dict_keys(data: dict[str, Any], prefix: str = "", list_item: bool = False) -> None:
    """Print every key in a dictionary as a tree, including nested dictionaries."""
    if not isinstance(data, dict):
        raise TypeError("data must be a dictionary")

    items = list(data.items())
    for index, (key, value) in enumerate(items):
        is_last = index == len(items) - 1
        branch = "└── " if is_last else "├── "
        marker = "... " if list_item else ""
        print(f"{prefix}{branch}{marker}{key}")
        if isinstance(value, dict):
            child_prefix = f"{prefix}{'    ' if is_last else '│   '}"
            print_dict_keys(value, child_prefix, list_item)
        elif isinstance(value, list):
            child_keys = _list_dict_keys(value)
            if child_keys:
                child_prefix = f"{prefix}{'    ' if is_last else '│   '}"
                print_dict_keys(child_keys, child_prefix, True)
