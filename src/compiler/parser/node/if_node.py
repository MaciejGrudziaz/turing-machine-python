from typing import List, Optional
from src.compiler.tokenizer.tokenizer import SectionLine, Token, TokenValue, TokenizerProgram, TokenizerResult
from enum import Enum
from src.compiler.parser.node.node import Node, NodeType, NodeExecuteResult

class IfConditionType(Enum):
    EQUAL = '=='
    NOT_EQUAL = '!='

# tree representing the IF statement
#    conditions objects on the same level (siblings) represents the OR relation
#    children objects of the IfCondition represents the AND relation
class IfCondition:
    def __init__(self, cond_type: IfConditionType, lhs: int, rhs: int | str):
        self.type = cond_type
        self.lhs = lhs
        self.rhs = rhs
        self.next = None
        self.down = None

    def add_child(self, cond):
        self.down = cond

    def add_sibling(self, cond):
        self.next = cond

    def _get_lhs(self, tapes_values: List[str]) -> str:
        return tapes_values[self.lhs]

    def _get_rhs(self, tapes_values: List[str]) -> str:
        if type(self.rhs).__name__ == "int":
            return tapes_values[self.rhs]
        return self.rhs

    def self_check_syntax(self, tape_count: int, alphabet: List[str]) -> bool:
        if self.lhs < 0 or self.lhs >= tape_count:
            raise Exception(f"Tape T.{self.lhs} is not defined")
        if type(self.rhs).__name__ == "int":
            if self.rhs < 0 or self.rhs >= tape_count:
                raise Exception(f"Tape T.{self.rhs} is not defined")
        else:
            if self.rhs not in alphabet:
                raise Exception(f"Value '{self.rhs}' is not defined in the alphabet.")

        if self.down is not None:
            self.down.self_check_syntax(tape_count, alphabet)
        if self.next is not None:
            self.next.self_check_syntax(tape_count, alphabet)

    def check_condition(self, tapes_values: List[str]) -> bool:
        if self.lhs is None:
            raise Exception("Left side condition argument is undefined")
        if self.rhs is None:
            raise Exception("Right side condition argument is undefined")
        if self.type == IfConditionType.EQUAL:
            if self._get_lhs(tapes_values) != self._get_rhs(tapes_values):
                if self.next is not None:
                    return self.next.check_condition(tapes_values)
                return False
        if self.type == IfConditionType.NOT_EQUAL:
            if self._get_lhs(tapes_values) == self._get_rhs(tapes_values):
                if self.next is not None:
                    return self.next.check_condition(tapes_values)
                return False

        if self.down is not None:
            return self.down.check_condition(tapes_values)

        return True

    def __str__(self):
        res = ""
        if self.down is not None:
            res += f"({self.lhs} {self.type} {self.rhs} && ({self.down}))"
        if self.next is not None:
            if self.down is not None:
                res += f" || {self.next}"
            else:
                res += f"{self.lhs} {self.type} {self.rhs} || {self.next}"
        elif self.down is None:
            res += f"{self.lhs} {self.type} {self.rhs}"

        return res

class IfNode(Node):
    def __init__(self, line: SectionLine):
        super().__init__(NodeType.IF, line)
        self.condition: Optional[IfCondition] = None

    def change_to_elif(self):
        self.node_type = NodeType.ELIF

    def set_condition(self, cond: IfCondition):
        self.condition = cond

    def self_check(self, states: List[str], tape_count: int, alphabet: List[str]) -> bool:
        if self.condition is None:
            self.__print_err__(f"No condition defined for the IF statement.")
            return False
        try:
            self.condition.self_check_syntax(tape_count, alphabet)
        except Exception as e:
            self.__print_err__(f"{e}")
            return False
        return True

    def execute(self, tape_state: List[str], is_debug_mode: bool = False) -> NodeExecuteResult | None:
        if is_debug_mode:
            print("    > Running IF statement")
            print(f"{self}")
        if self.condition is None:
            return None
        if self.condition.check_condition(tape_state):
            if is_debug_mode:
                print("    > IF condition check is successful")
            for child in self.children:
                return child.execute(tape_state, is_debug_mode)
        else:
            if is_debug_mode:
                print("    > IF condition check failed")

        return None


