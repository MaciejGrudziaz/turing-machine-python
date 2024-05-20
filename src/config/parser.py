from dataclasses import dataclass
from typing import Dict, List
from src.config.tokenizer import SectionLine, Token, TokenizerProgram, TokenizerResult
from enum import Enum

class NodeType(Enum):
    STATE = 0
    IF = 1
    ELSE = 2
    THEN = 3
    ELIF = 4
    GOTO = 5

@dataclass
class NodeExecuteResult:
    # MOV_R = 1, MOV_L = -1
    tape_movement: List[int]
    # if None, stay in the current state
    new_state: None | str

class Node:
    def __init__(self, node_type: NodeType, line: SectionLine):
        self.node_type = node_type
        self.lines = [line]
        self.children = []

    def add_line(self, line: SectionLine):
        self.lines.append(line)

    def add_child(self, node):
        self.children.append(node)

    def execute(self, tape_state: List[str]) -> NodeExecuteResult:
        return NodeExecuteResult(tape_movement=[1 for _ in range(len(tape_state))], new_state=None)

    def check(self) -> bool:
        return True

class StateNode(Node):
    def __init__(self, name: str, line: SectionLine):
        super().__init__(NodeType.STATE, line)
        self.name = name

class IfNode(Node):
    def __init__(self, line: SectionLine):
        super().__init__(NodeType.IF, line)

class ElseNode(Node):
    def __init__(self, line: SectionLine):
        super().__init__(NodeType.ELSE, line)

class ThenNode(Node):
    def __init__(self, line: SectionLine):
        super().__init__(NodeType.THEN, line)

class ElifNode(Node):
    def __init__(self, line: SectionLine):
        super().__init__(NodeType.ELIF, line)

class GotoNode(Node):
    def __init__(self, line: SectionLine):
        super().__init__(NodeType.GOTO, line)

class ProgramAST:
    def __init__(self):
        self.start_node = None
        self.nodes = {}
    def set_start_node(self, start_node: str):
        self.start_node = start_node

    def add_node(self, name: str, node: Node):
        self.nodes[name] = node

def parse_program(tokenizer_result: TokenizerProgram) -> ProgramAST | None:
    ast = ProgramAST()
    tokens = tokenizer_result.tokens.__iter__()
    try:
        start_token = tokens.__next__()
        if start_token.token != Token.START:
            print_err("Missed the START declaration at the beginning of the program.", start_token.line)
            return None
        start_state = tokens.__next__()
        if start_state.token != Token.VAR:
            print_err("Missed STATE declaration in the START state definition (expected START <state>).", start_state.line)
            return None

    except StopIteration:
        pass

    return ast

def print_err(message: str, line: SectionLine):
    print(f"Error at line '{line.no}: {line.value}'. Failed to parse program code. {message}")

