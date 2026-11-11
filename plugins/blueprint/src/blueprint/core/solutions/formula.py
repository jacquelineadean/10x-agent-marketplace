"""Formulas: arithmetic Claude writes as text, read into a tree the build and the page walk.

The text uses Python's arithmetic syntax. `parse` reads it with the standard `ast` reader
and runs none of it: it accepts numbers, names, `+ - * / % **`, comparisons, `and`, `or`,
`not`, `a if c else b` and the functions in FUNCTIONS. The tree is nested lists, so the
page's script applies the same rules to the same tree and gets the same number.
"""

from __future__ import annotations

import ast
import math
from collections.abc import Mapping
from typing import Any

# A number, a name, or [operation, argument, ...].
Tree = Any

BINARY: dict[type[ast.operator], str] = {
    ast.Add: "add",
    ast.Sub: "sub",
    ast.Mult: "mul",
    ast.Div: "div",
    ast.Mod: "mod",
    ast.Pow: "pow",
}
COMPARE: dict[type[ast.cmpop], str] = {
    ast.Lt: "lt",
    ast.LtE: "le",
    ast.Gt: "gt",
    ast.GtE: "ge",
    ast.Eq: "eq",
    ast.NotEq: "ne",
}
# Each function's fewest and most arguments; None means any number.
FUNCTIONS: dict[str, tuple[int, int | None]] = {
    "min": (2, None),
    "max": (2, None),
    "abs": (1, 1),
    "sqrt": (1, 1),
    "log": (1, 1),
    "exp": (1, 1),
    "ceil": (1, 1),
    "floor": (1, 1),
    "round": (1, 1),
    "clamp": (3, 3),
    "pow": (2, 2),
}
ALLOWED = (
    "numbers, names, + - * / % **, comparisons, and, or, not, `a if c else b` and "
    + ", ".join(FUNCTIONS)
)


class FormulaError(ValueError):
    """A formula that cannot be read, or a value it cannot compute."""


def parse(text: str) -> Tree:
    """Read a formula into its tree; FormulaError says what to change."""
    try:
        body = ast.parse(text.strip(), mode="eval").body
    except SyntaxError as exc:
        raise FormulaError(f"cannot read {text!r}: {exc.msg}") from exc
    return _tree(body)


def _tree(node: ast.expr) -> Tree:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, int | float):
            raise FormulaError(f"{node.value!r} is not a number")
        return float(node.value)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.BinOp) and type(node.op) in BINARY:
        return [BINARY[type(node.op)], _tree(node.left), _tree(node.right)]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub | ast.UAdd | ast.Not):
        inner = _tree(node.operand)
        if isinstance(node.op, ast.UAdd):
            return inner
        return ["neg" if isinstance(node.op, ast.USub) else "not", inner]
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in COMPARE:
        return [COMPARE[type(node.ops[0])], _tree(node.left), _tree(node.comparators[0])]
    if isinstance(node, ast.BoolOp):
        return ["and" if isinstance(node.op, ast.And) else "or", *map(_tree, node.values)]
    if isinstance(node, ast.IfExp):
        return ["if", _tree(node.test), _tree(node.body), _tree(node.orelse)]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and not node.keywords:
        return _call(node.func.id, node.args)
    raise FormulaError(f"{ast.unparse(node)!r} is not arithmetic; use {ALLOWED}")


def _call(name: str, args: list[ast.expr]) -> Tree:
    if name not in FUNCTIONS:
        raise FormulaError(f"unknown function {name!r}; use {', '.join(FUNCTIONS)}")
    fewest, most = FUNCTIONS[name]
    if len(args) < fewest or (most is not None and len(args) > most):
        wanted = f"{fewest}" if most == fewest else f"{fewest} or more"
        raise FormulaError(f"{name} takes {wanted} argument(s), not {len(args)}")
    return [name, *map(_tree, args)]


def names(tree: Tree) -> set[str]:
    """Every name a tree reads."""
    if isinstance(tree, str):
        return {tree}
    if isinstance(tree, list):
        return set().union(*(names(arg) for arg in tree[1:]))
    return set()


def evaluate(tree: Tree, values: Mapping[str, float]) -> float:
    """The tree's value; FormulaError when a name is unknown or a step is not a finite number."""
    if isinstance(tree, str):
        if tree not in values:
            raise FormulaError(f"unknown name {tree!r}")
        return float(values[tree])
    if not isinstance(tree, list):
        return float(tree)
    op = str(tree[0])
    # Only the branch taken is computed, so a guard such as `a / b if b > 0 else 0` holds.
    if op == "if":
        return evaluate(tree[2] if evaluate(tree[1], values) else tree[3], values)
    if op == "and":
        return float(all(evaluate(arg, values) for arg in tree[1:]))
    if op == "or":
        return float(any(evaluate(arg, values) for arg in tree[1:]))
    return _apply(op, [evaluate(arg, values) for arg in tree[1:]])


def _apply(op: str, args: list[float]) -> float:
    a = args[0]
    b = args[1] if len(args) > 1 else 0.0
    if op in ("div", "mod") and b == 0:
        raise FormulaError("division by zero")
    if (op == "sqrt" and a < 0) or (op == "log" and a <= 0):
        raise FormulaError(f"{op} of {a:g}")
    try:
        result = float(_OPERATIONS[op](a, b, args))
    except (ValueError, OverflowError) as exc:
        raise FormulaError(f"{op} of {a:g} and {b:g} is not a real number") from exc
    # Every step must be finite, so no infinity reaches a comparison on either side.
    if not math.isfinite(result):
        raise FormulaError(f"{op} of {a:g} and {b:g} is too large")
    return result


_OPERATIONS: dict[str, Any] = {
    "add": lambda a, b, _: a + b,
    "sub": lambda a, b, _: a - b,
    "mul": lambda a, b, _: a * b,
    "div": lambda a, b, _: a / b,
    # Floored, so the page's script and this reader agree for negative values.
    "mod": lambda a, b, _: a - b * math.floor(a / b),
    "pow": lambda a, b, _: math.pow(a, b),
    "neg": lambda a, _b, _: -a,
    "not": lambda a, _b, _: float(not a),
    "lt": lambda a, b, _: float(a < b),
    "le": lambda a, b, _: float(a <= b),
    "gt": lambda a, b, _: float(a > b),
    "ge": lambda a, b, _: float(a >= b),
    "eq": lambda a, b, _: float(a == b),
    "ne": lambda a, b, _: float(a != b),
    "min": lambda _a, _b, args: min(args),
    "max": lambda _a, _b, args: max(args),
    "abs": lambda a, _b, _: abs(a),
    "sqrt": lambda a, _b, _: math.sqrt(a),
    "log": lambda a, _b, _: math.log(a),
    "exp": lambda a, _b, _: math.exp(a),
    "ceil": lambda a, _b, _: float(math.ceil(a)),
    "floor": lambda a, _b, _: float(math.floor(a)),
    # Halves round up, as the page's script rounds them.
    "round": lambda a, _b, _: float(math.floor(a + 0.5)),
    "clamp": lambda a, b, args: max(b, min(args[2], a)),
}
