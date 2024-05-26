from dataclasses import dataclass
from typing import Dict, Iterator, List, Tuple
from src.config.tokenizer import SectionLine, Token, TokenValue, TokenizerProgram, TokenizerResult
from enum import Enum
from functools import reduce
import re
......
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

def get_tape_id(token: TokenValue) -> int | None:
    if token.token != Token.VAR or token.value is None:
        return None
    tape_id_pattern = r'^t\.(\d+)$'
    match = re.search(tape_id_pattern, token.value)

    if match is None:
        return None

    try:
        return int(match.group(1))
    except Exception:
        return None

def print_err(message: str, line: SectionLine):
    print(f"Error at line '{line.no}: {line.value}'. Failed to parse program code. {message}")

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

    def execute(self, tape_state: List[str]) -> NodeExecuteResult:
        return NodeExecuteResult(tape_movement=[1 for _ in range(len(tape_state))], new_state="", tape_value=[v for v in tape_state])

    def self_check(self, states: List[str], tape_count: int, alphabet: List[str]) -> bool:
        return True

    def __print_err__(self, msg: str):
        print(f"In component:\n{self}\n{msg}")

    def __str__(self):
        lines = map(lambda v: v[1].value, sorted(list(self.lines.items()), key=lambda v: v[0]))
        return "\n".join(lines)

class StateNode(Node):
    def __init__(self, name: str, line: SectionLine):
        super().__init__(NodeType.STATE, line)
        self.name = name

class IfNode(Node):
    def __init__(self, line: SectionLine):
        super().__init__(NodeType.IF, line)
        self.conditions = []

    def change_to_elif(self):
        self.node_type = NodeType.ELIF

    def add_condition_const(self, tape_id: TokenValue, val: TokenValue) -> bool:
        if tape_id.value is None or val.value is None:
            return False

        tape_id_val = get_tape_id(tape_id)
        if tape_id_val is None:
            return False
        self.conditions.append((tape_id_val, val.value))

        self.add_line(tape_id.line)
        self.add_line(val.line)
        return True

    def add_condition_ref(self, tape_id: TokenValue, ref_tape_id: TokenValue) -> bool:
        if tape_id.value is None or ref_tape_id.value is None:
            return False

        tape_id_val = get_tape_id(tape_id)
        ref_tape_id_val = get_tape_id(ref_tape_id)
        if tape_id_val is None or ref_tape_id_val is None:
            return False

        self.conditions.append((tape_id_val, ref_tape_id_val))

        self.add_line(tape_id.line)
        self.add_line(ref_tape_id.line)
        return True

    def self_check(self, states: List[str], tape_count: int, alphabet: List[str]) -> bool:
        for tape_id, val in self.conditions:
            if tape_id < 0 or tape_id >= tape_count:
                self.__print_err__(f"Tape 'T.{tape_id}' is not defined")
                return False
            if type(val).__name__ == "int":
                if val < 0 or val >= tape_count:
                    self.__print_err__(f"Tape 'T.{val}' is not defined")
                    return False
            else:
                if val not in alphabet:
                    self.__print_err__(f"Value '{val}' is not defined in the alphabet")
                    return False

        return True

class ElseNode(Node):
    def __init__(self, line: SectionLine):
        super().__init__(NodeType.ELSE, line)

class ThenNode(Node):
    def __init__(self, line: SectionLine):
        super().__init__(NodeType.THEN, line)

class GotoNode(Node):
    def __init__(self, line: SectionLine):
        super().__init__(NodeType.GOTO, line)
        self.execute_result = None

    def add_execution_result(self, next_state: TokenValue, actions: List[Tuple[TokenValue, TokenValue, TokenValue]]) -> bool:
        if next_state.value is None:
            return False
        self.add_line(next_state.line)

        tape_movement = {}
        tape_values = {}

        for tape_id, value_token, move in actions:
            tape_id_val = get_tape_id(tape_id)
            if tape_id_val is None:
                print_err("Wrong tape reference format. Expected: T.<n>", tape_id.line)
                return False
            if tape_id_val in tape_values:
                print_err(f"Multiple action definitions for tape T.{tape_id_val}", tape_id.line)
                return False
            if value_token.value is None:
                print_err(f"Wrong next tape value format. Expected variable or const value declaration.", value_token.line)
                return False
            if value_token.token == Token.CONST:
                tape_values[tape_id_val] = (value_token.value, value_token.line)
            elif value_token.token == Token.VAR:
                value = get_tape_id(value_token)
                if value is None:
                    print_err("Wrong tape reference format, in next tape value declaration. Expected: T.<n>", value_token.line)
                    return False
                tape_values[tape_id_val] = (value, value_token.line)
            else:
                print_err("Wrong next tape value format. Exepected variable or const value declaration.", value_token.line)
                return False

            if move.token == Token.MOV_L:
                tape_movement[tape_id_val] = -1
            elif move.token == Token.MOV_R:
                tape_movement[tape_id_val] = 1
            else:
                print_err("Wrong tape movement value. Expected MOV_L or MOV_R", move.line)
                return False

            self.add_line(tape_id.line)
            self.add_line(value_token.line)
            self.add_line(move.line)

        if not self.__parse_execution_results__(next_state.value, tape_movement, tape_values):
            return False

        return True

    def __parse_execution_results__(self, next_state: str, tape_movement: Dict[int, int], tape_values: Dict[int, Tuple[str | int, SectionLine]]) -> bool:
        tape_move_result = []
        tape_value_result = []
        for tape_id, value in sorted(list(tape_values.items()), key=lambda val: val[0]):
            if tape_id >= len(tape_values):
                print_err(f"Tape id T.{tape_id} is out of range", value[1])
                return False
            elif tape_id < 0:
                print_err(f"Tape id T.{tape_id} is out of range", value[1])
                return False

            if tape_id not in tape_movement:
                print_err("Tape movement is not defined", value[1])
                return False
            tape_move = tape_movement[tape_id]

            tape_value_result.append(value[0])
            tape_move_result.append(tape_move)

        self.execute_result = NodeExecuteResult(tape_movement=tape_move_result, tape_value=tape_value_result, new_state=next_state)
        return True

    def self_check(self, states: List[str], tape_count: int, alphabet: List[str]) -> bool:
        if self.execute_result is None:
            self.__print_err__("No actions defined int the GOTO section.")
            return False
        if self.execute_result.new_state not in states:
            self.__print_err__(f"State '{self.execute_result.new_state}' is not defined")
            return False
        if len(self.execute_result.tape_movement) != tape_count:
            self.__print_err__(f"In GOTO section, there should be an action defined for each tape (found: {len(self.execute_result.tape_movement)}, expected: {tape_count})")
            return False
        if len(self.execute_result.tape_value) != tape_count:
            self.__print_err__(f"In GOTO section, there should be an action defined for each tape (found: {len(self.execute_result.tape_value)}, expected: {tape_count})")
            return False
        for move in self.execute_result.tape_movement:
            if move != -1 and move != 1:
                self.__print_err__(f"Unrecognized tape move value: {move}.")
                return False
        for value in self.execute_result.tape_value:
            if type(value).__name__ == "int":
                if value < 0 or value >= tape_count:
                    self.__print_err__(f"Tape T.{value} is undefined")
                    return False
            else:
                if value not in alphabet:
                    self.__print_err__(f"Value '{value}' is not defined in the alphabet")
                    return False
        return True

class ProgramAST:
    def __init__(self, tape_count: int, alphabet: List[str]):
        self.alphabet = alphabet
        self.tape_count = tape_count
        self.start_node = None
        self.nodes = {}

    def set_start_node(self, start_node: str):
        self.start_node = start_node

    def add_node(self, name: str, node: Node):
        self.nodes[name] = node

    def check_syntax(self) -> bool:
        if self.start_node is None:
            self.__print_err__("Start state is not defined!")
            return False

        if self.start_node not in self.nodes:
            self.__print_err__(f"Start state '{self.start_node}' is not defined")
            return False

        for state_name, state in self.nodes.items():
            if not state.does_end_with_goto():
                self.__print_err__(f"State '{state_name}' have a path that does not result in tape action.")
                return False
            if not state.self_check(list(self.nodes.keys()), self.tape_count, self.alphabet):
                return False
            if not state.check_children(list(self.nodes.keys()), self.tape_count, self.alphabet):
                return False
        return True

    def __print_err__(self, msg: str):
        print(msg)

def parse_program(tokenizer_result: TokenizerProgram, tape_count: int, alphabet: List[str]) -> ProgramAST | None:
    ast = ProgramAST(tape_count, alphabet)
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
        if start_state.value is None:
            print_err("Missing variable name declaration.", start_state.line)
            return None
        ast.set_start_node(start_state.value)

        while True:
            state = parse_state(tokens)
            if state is None:
                return None
            ast.add_node(state.name, state)
    except StopIteration:
        pass

    return ast

def parse_state(tokens_iter: Iterator[TokenValue]) -> StateNode | None:
    state_name = tokens_iter.__next__()
    if state_name.token != Token.VAR:
        print_err("Expected state definition.", state_name.line)
        return None
    if state_name.value is None:
        print_err("Missing variable name declaration.", state_name.line)
        return None
    state = StateNode(state_name.value, state_name.line)
    section_start = tokens_iter.__next__()
    if section_start.token != Token.SECTION_START:
        print_err(f"Expected '{{', found {section_start}", section_start.line)
        return None
    state.add_line(section_start.line)
    section_end = tokens_iter.__next__()
    try:
        while section_end.token != Token.SECTION_END:
            node = parse_node(section_end, tokens_iter)
            if node is None:
                return None
            state.add_child(node)
            section_end = tokens_iter.__next__()
    except StopIteration:
        print_err(f"Expected closing tag '}}' for tag opened at line '{section_start.line.no}: {section_start.line.value}', found {section_end}", section_end.line)
        return None

    state.add_line(section_end.line)

    return state

def parse_node(current_token: TokenValue, tokens_iter: Iterator[TokenValue]) -> Node | None:
    if current_token.token == Token.IF:
        return parse_if_node(tokens_iter, is_elif=False)
    elif current_token.token == Token.ELSE_IF:
        return parse_if_node(tokens_iter, is_elif=True)
    elif current_token.token == Token.ELSE:
        return parse_else_node(tokens_iter)
    elif current_token.token == Token.GOTO:
        return parse_goto_node(tokens_iter)
    else:
        print_err(f"Unexpected token {current_token.token}", current_token.line)
        return None

def parse_if_node(tokens_iter: Iterator[TokenValue], is_elif: bool) -> IfNode | None:
    then_token = tokens_iter.__next__()
    if_node = IfNode(then_token.line)
    if is_elif:
        if_node.change_to_elif()

    try:
        while then_token.token != Token.THEN:
            if then_token.token == Token.AND:
                lhs = tokens_iter.__next__()
            else:
                lhs = then_token
            if lhs.token != Token.VAR:
                print_err("In IF statement, left side argument must be a variable.", lhs.line)
                return None
            if lhs.token.value is  None:
                print_err("Missing variable name declaration", lhs.line)
                return None
            comp = tokens_iter.__next__()
            if comp.token not in [Token.EQUAL, Token.NOT_EQUAL]:
                print_err("Unexpected comparision token. Expected values are: '==' and '!='", comp.line)
                return None
            rhs = tokens_iter.__next__()
            if rhs.token == Token.CONST:
                if rhs.token.value is None:
                    print_err("Missing const value definition", rhs.line)
                    return None
                if not if_node.add_condition_const(lhs, rhs):
                    print_err("Wrong format of tape reference, expected: T.<n>", rhs.line)
                    return None
            elif rhs.token == Token.VAR:
                if rhs.token.value is None:
                    print_err("Missing variable name declaration", lhs.line)
                    return None
                if not if_node.add_condition_ref(lhs, rhs):
                    print_err("Wrong format of tape reference, expects: T.<n>", rhs.line)
                    return None
            else:
                print_err("In IF statement, right side argument must be either a variable or a const value", rhs.line)
                return None
            then_token = tokens_iter.__next__()
    except StopIteration:
        print_err("Expected THEN tag after IF statement", then_token.line)
        return None

    then_node = parse_then_node(tokens_iter)
    if then_node is None:
        return None
    if_node.add_child(then_node)

    return if_node

def parse_then_node(tokens_iter: Iterator[TokenValue]) -> ThenNode | None:
    begin_then_section = tokens_iter.__next__()
    if begin_then_section.token != Token.SECTION_START:
        print_err("Expected {{ tag not found after THEN statement.", begin_then_section.line)
        return None

    then_node = ThenNode(begin_then_section.line)

    end_then_section = tokens_iter.__next__()
    try:
        while end_then_section.token != Token.SECTION_END:
            node = parse_node(end_then_section, tokens_iter)
            if node is None:
                return None
            then_node.add_child(node)
            end_then_section = tokens_iter.__next__()
    except StopIteration:
        print_err(f"Expected }} tag, for the section opened at line: '{begin_then_section.line.no}: {begin_then_section.line.value}', not found.", end_then_section.line)
        return None

    then_node.add_line(end_then_section.line)

    return then_node

def parse_else_node(tokens_iter: Iterator[TokenValue]) -> ElseNode | None:
    begin_section = tokens_iter.__next__()
    if begin_section.token != Token.SECTION_START:
        print_err("Expected '{{' tag.", begin_section.line)
        return None
    else_node = ElseNode(begin_section.line)

    end_section = tokens_iter.__next__()
    try:
        while end_section.token != Token.SECTION_END:
            node = parse_node(end_section, tokens_iter)
            if node is None:
                return None
            else_node.add_child(node)
            end_section = tokens_iter.__next__()
    except StopIteration:
        print_err(f"Expected '}}' tag, for the section opened at line: '{begin_section.line.no}: {begin_section.line.value}' not found.", end_section.line)
        return None

    else_node.add_line(end_section.line)

    return else_node

def parse_goto_node(tokens_iter: Iterator[TokenValue]) -> GotoNode | None:
    next_state = tokens_iter.__next__()
    if next_state.token != Token.VAR:
        print_err("Expected the STATE variable.", next_state.line)
        return None
    goto_node = GotoNode(next_state.line)

    begin_section = tokens_iter.__next__()
    if begin_section.token != Token.SECTION_START:
        print_err("Expected {{ tag.", begin_section.line)
        return None

    tape_actions = []
    end_section = tokens_iter.__next__()
    while end_section.token != Token.SECTION_END:
        if end_section.token == Token.SEPARATOR:
            tape_id = tokens_iter.__next__()
        else:
            tape_id = end_section

        assign_token = tokens_iter.__next__()
        if assign_token.token != Token.ASSIGN:
            print_err("Expected ':' tag.", assign_token.line)
            return None

        begin_tuple = tokens_iter.__next__()
        if begin_tuple.token != Token.TAB_START:
            print_err("Expected '[' tag.", begin_tuple.line)
            return None

        value = tokens_iter.__next__()

        separator = tokens_iter.__next__()
        if separator.token != Token.SEPARATOR:
            print_err("Expected ',' separator after a value in tuple.", separator.line)
            return None

        movement = tokens_iter.__next__()

        end_tuple = tokens_iter.__next__()
        if end_tuple.token == Token.SEPARATOR:
            end_tuple = tokens_iter.__next__()

        if end_tuple.token != Token.TAB_END:
            print_err(f"Expected ']' tag for the tuple opened at line: '{end_tuple.line.no}: {end_tuple.line.value}.'", end_tuple.line)
            return None

        tape_actions.append((tape_id, value, movement))

        end_section = tokens_iter.__next__()
        if end_section.token == Token.SEPARATOR:
            end_section = tokens_iter.__next__()

    goto_node.add_line(end_section.line)

    if not goto_node.add_execution_result(next_state, tape_actions):
        print_err(f"Failed to parse the GOTO actions.", begin_section.line)
        return None
    return goto_node

