"""Restricted Decimal arithmetic with evidence-bound operands."""
from __future__ import annotations

import ast
import re
from decimal import Decimal, DivisionByZero

from finance_rag.models import Evidence


def extract_raw_and_pct_numbers(text: str) -> tuple[set[Decimal], set[Decimal]]:
    pattern = r"(?<![\w.])[-+]?(?:\d[\d,]*(?:\.\d+)?|\.\d+)"
    raw = {Decimal(token.replace(",", "")) for token in re.findall(pattern, text)}
    pct = {Decimal(token.replace(",", "")) / Decimal(100)
           for token in re.findall(pattern + r"(?=\s*%)", text)}
    paren_neg = {-Decimal(token.replace(",", ""))
                 for token in re.findall(r"\(\s*(?:\$)?\s*([0-9][0-9,]*(?:\.[0-9]+)?|\.[0-9]+)\s*\)", text)}
    paren_pct = {-Decimal(token.replace(",", "")) / Decimal(100)
                 for token in re.findall(r"\(\s*(?:\$)?\s*([0-9][0-9,]*(?:\.[0-9]+)?|\.[0-9]+)\s*%\s*\)", text)}
    return (raw | paren_neg), (pct | paren_pct)


def extract_evidence_numbers(text: str) -> set[Decimal]:
    raw, pct = extract_raw_and_pct_numbers(text)
    return raw | pct


def calculate(expression: str, evidence: list[Evidence], evidence_ids: list[str]) -> dict:
    selected = [e for e in evidence if e.evidence_id in evidence_ids]
    if len(selected) != len(set(evidence_ids)) or not selected:
        raise ValueError("Every calculator operand must cite available evidence")
    raw_numbers: set[Decimal] = set()
    pct_numbers: set[Decimal] = set()
    for item in selected:
        r, p = extract_raw_and_pct_numbers(item.text)
        raw_numbers |= r
        pct_numbers |= p
    tree = ast.parse(expression, mode="eval")
    scale_constants: set[str] = set()

    def visit(node: ast.AST) -> Decimal:
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in {int, float}:
            value = Decimal(str(node.value))
            if value in raw_numbers:
                return value
            if value in pct_numbers or (value * 100) in raw_numbers:
                scaled = value * 100
                scale_str = f"{int(scaled) if scaled == int(scaled) else scaled}"
                scale_constants.add(f"{value} ({scale_str}% decimal equivalent)")
                return value
            if value == 100:
                scale_constants.add("100 (percentage conversion)")
            elif value == 1:
                scale_constants.add("1 (unitary baseline)")
            elif value == 1000:
                scale_constants.add("1000 (thousand/million scale conversion)")
            elif value == 1000000:
                scale_constants.add("1000000 (million/billion scale conversion)")
            elif (value / 100) in raw_numbers:
                scaled = value / 100
                scale_str = f"{int(scaled) if scaled == int(scaled) else scaled}"
                scale_constants.add(f"{value} ({scale_str} percentage conversion)")
            elif (value / 1000) in raw_numbers:
                scaled = value / 1000
                scale_str = f"{int(scaled) if scaled == int(scaled) else scaled}"
                scale_constants.add(f"{value} ({scale_str} * 1000 scale conversion)")
            elif (value * 1000) in raw_numbers:
                scaled = value * 1000
                scale_str = f"{int(scaled) if scaled == int(scaled) else scaled}"
                scale_constants.add(f"{value} ({scale_str} / 1000 scale conversion)")
            elif (value / 1000000) in raw_numbers:
                scaled = value / 1000000
                scale_str = f"{int(scaled) if scaled == int(scaled) else scaled}"
                scale_constants.add(f"{value} ({scale_str} * 1000000 scale conversion)")
            elif (value * 1000000) in raw_numbers:
                scaled = value * 1000000
                scale_str = f"{int(scaled) if scaled == int(scaled) else scaled}"
                scale_constants.add(f"{value} ({scale_str} / 1000000 scale conversion)")
            else:
                raise ValueError(f"Operand {value} does not occur in cited evidence")
            return value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -visit(node.operand)
        if isinstance(node, ast.BinOp):
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                if right == 0:
                    raise DivisionByZero
                return left / right
        raise ValueError("Only numeric +, -, *, / and parentheses are permitted")

    value = visit(tree)
    return {"expression": expression, "result": str(value),
            "operand_evidence_ids": evidence_ids,
            "scale_constants": sorted(scale_constants)}
