from typing import List
from dataclasses import dataclass
from enum import Enum
from src.compiler.tokenizer.tokenizer import SectionLine, Token, TokenValue, TokenizerProgram, TokenizerResult
from functools import reduce

class NodeType(Enum):
    STATE = 0
    IF = 1
    ELIF = 2
    ELSE = 3
    THEN = 4
    GOTO = 5

@dataclass
class NodeExecuteResult:
    # MOV_R = 1, MOV_L = -1
    tape_movement: List[int]
    tape_value: List[int | str]
    new_state: str


class Node:
    def __init__(self, node_type: NodeType, line: SectionLine):
        self.node_type = node_type
        self.lines = {}
        self.lines[line.no] = line
        self.children = []

    def add_line(self, line: SectionLine):
        self.lines[line.no] = line

    def add_child(self, node):
        self.children.append(node)
        for line in node.lines.values():
            self.add_line(line)

    def does_end_with_goto(self) -> bool:
        if len(self.children) == 0:
            if self.node_type == NodeType.GOTO:
                return True
            else:
                return False

        for child in self.children:
            if not child.does_end_with_goto():
                return False
        return True

    def check_children(self, states: List[str], tape_count: int, alphabet: List[str]) -> bool:
        for child in self.children:
            if len(self.children) == 1:
                child = self.children[0]
                if child.node_type == NodeType.IF:
                    self.__print_err__("Missing ELSE statement")
                    return False
                elif child.node_type == NodeType.ELSE:
                    self.__print_err__("Missing IF statement")
                    return False
            elif len(self.children) > 1:
                node_types = list(map(lambda child: child.node_type, self.children))
                if_count = reduce(lambda count, node_type: count + 1 if node_type == NodeType.IF else count, node_types, 0)
                if_pos = reduce(lambda pos, node_enum: node_enum[0] if node_enum[1] == NodeType.IF else pos, enumerate(node_types), 0)
                else_count = reduce(lambda count, node_type: count + 1 if node_type == NodeType.ELSE else count, node_types, 0)
                else_pos = reduce(lambda pos, node_enum: node_enum[0] if node_enum[1] == NodeType.ELSE else pos, enumerate(node_types), 0)
                elif_count = reduce(lambda count, node_type: count + 1 if node_type == NodeType.ELIF else count, node_types, 0)
                first_elif_pos = reduce(lambda pos, node_enum: node_enum[0] if node_enum[1] == NodeType.ELIF and pos == -1 else pos, enumerate(node_types), -1)
                last_elif_pos = reduce(lambda pos, node_enum: node_enum[0] if node_enum[1] == NodeType.ELIF else pos, enumerate(node_types), 0)

                if else_count > 1:
                    self.__print_err__("Multiple ELSE definitions")
                    return False
                elif if_count == 1 and else_count == 0:
                    self.__print_err__("Missing ELSE statement")
                    return False
                elif if_count == 0 and (elif_count > 0 or else_count > 0):
                    self.__print_err__("Missing IF statement")
                    return False
                elif if_count > 1:
                    self.__print_err__("Multiple IF statements")
                    return False
                elif elif_count > 0:
                    if first_elif_pos != if_pos + 1:
                        self.__print_err__("ELIF statement must be after IF statement")
                        return False
                    if (last_elif_pos - first_elif_pos + 1) != elif_count:
                        self.__print_err__("ELIF statements must begin with IF statement and end with ELSE statement")
                        return False
                    if else_pos != last_elif_pos + 1:
                        self.__print_err__("ELSE statement must be after last ELIF statement")
                        return False
                elif elif_count == 0:
                    if else_pos != if_pos + 1:
                        self.__print_err__("ELSE statement must be after IF statement")
                        return False

            if not child.self_check(states, tape_count, alphabet):
                return False
            if not child.check_children(states, tape_count, alphabet):
                return False

        return True

    def execute(self, tape_state: List[str], is_debug_mode: bool = False) -> NodeExecuteResult | None:
        for child in self.children:
            result = child.execute(tape_state, is_debug_mode)
            if result is not None:
                return result

        return None

    def self_check(self, states: List[str], tape_count: int, alphabet: List[str]) -> bool:
        return True

    def __print_err__(self, msg: str):
        print(f"In component:\n{self}\n{msg}")

    def __str__(self):
        lines = map(lambda v: v[1].value, sorted(list(self.lines.items()), key=lambda v: v[0]))
        return "\n".join(lines)

