from dataclasses import dataclass
from typing import Literal

OpType = Literal["insert", "delete", "update"]


@dataclass
class Op:
    type: OpType
    pos: int
    text: str = ""
    length: int = 0
    user_id: str = ""
    doc_version: int = 0


def transform(op_a: Op, op_b: Op) -> Op:
    match (op_a.type, op_b.type):
        case ("insert", "insert"):
            if op_a.pos >= op_b.pos:
                op_a.pos += len(op_b.text)
        case ("insert", "delete"):
            if op_a.pos > op_b.pos:
                op_a.pos -= min(op_b.length, op_a.pos - op_b.pos)
        case ("delete", "insert"):
            if op_a.pos >= op_b.pos:
                op_a.pos += len(op_b.text)
        case ("delete", "delete"):
            if op_a.pos >= op_b.pos:
                shift = min(op_b.length, op_a.pos - op_b.pos)
                op_a.pos -= shift
    return op_a


def apply(content: str, op: Op) -> str:
    match op.type:
        case "insert":
            return content[:op.pos] + op.text + content[op.pos:]
        case "delete":
            return content[:op.pos] + content[op.pos + op.length :]
        case "update":
            return content[:op.pos] + op.text + content[op.pos + op.length :]


def compose(op_a: Op, op_b: Op) -> Op:
    match (op_a.type, op_b.type):
        case ("insert", "insert"):
            if op_b.pos >= op_a.pos:
                offset = op_b.pos - op_a.pos
                new_text = op_a.text[:offset] + op_b.text + op_a.text[offset:]
                return Op("insert", op_a.pos, new_text)
            msg = f"cannot compose insert before another insert"
            raise NotImplementedError(msg)

        case ("insert", "delete"):
            ins_end = op_a.pos + len(op_a.text)
            if op_b.pos >= op_a.pos and op_b.pos + op_b.length <= ins_end:
                offset = op_b.pos - op_a.pos
                new_text = op_a.text[:offset] + op_a.text[offset + op_b.length :]
                return Op("insert", op_a.pos, new_text)
            msg = f"cannot compose insert+delete: delete not within inserted text"
            raise NotImplementedError(msg)

        case ("delete", "insert"):
            if op_b.pos == op_a.pos:
                return Op("update", op_a.pos, op_b.text, op_a.length)
            msg = f"cannot compose delete+insert: insert not at delete position"
            raise NotImplementedError(msg)

        case ("delete", "delete"):
            if op_b.pos == op_a.pos:
                return Op("delete", op_a.pos, length=op_a.length + op_b.length)
            msg = f"cannot compose delete+delete: b not at same position as a"
            raise NotImplementedError(msg)

        case _:
            msg = f"compose not implemented for ({op_a.type}, {op_b.type})"
            raise NotImplementedError(msg)


def transform_list(op: Op, against: list[Op]) -> Op:
    for prior in against:
        op = transform(op, prior)
    return op
