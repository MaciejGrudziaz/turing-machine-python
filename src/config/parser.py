from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional, Tuple, Union
from src.config.tokenizer import SectionLine, Token, TokenValue, TokenizerProgram, TokenizerResult
from enum import Enum
from functools import reduce
import re

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

    def execute(self, tape_state: List[str]) -> NodeExecuteResult | None:
        for child in self.children:
            result = child.execute(tape_state)
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

class StateNode(Node):
    def __init__(self, name: str, line: SectionLine):
        super().__init__(NodeType.STATE, line)
        self.name = name

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

    def execute(self, tape_state: List[str]) -> NodeExecuteResult | None:
        if self.condition is None:
            return None
        if self.condition.check_condition(tape_state):
            for child in self.children:
                return child.execute(tape_state)
        return None

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

    def execute(self, tape_state: List[str]) -> NodeExecuteResult | None:
        return self.execute_result

class ProgramAST:
    def __init__(self, tape_count: int, alphabet: List[str]):
        self.alphabet = alphabet
        self.tape_count = tape_count
        self.start_node = None
        self.end_nodes = []
        self.nodes = {}

    def set_start_node(self, start_node: str):
        self.start_node = start_node

    def set_end_nodes(self, end_nodes: List[str]):
        self.end_nodes = end_nodes

    def add_node(self, name: str, node: Node):
        self.nodes[name] = node

    def check_syntax(self) -> bool:
        if self.start_node is None:
            self.__print_err__("Start state is undefined!")
            return False

        if self.start_node not in self.nodes:
            self.__print_err__(f"Start state '{self.start_node}' is undefined")
            return False

        if not self.__check_end_nodes__():
            return False

        for state_name, state in self.nodes.items():
            if not state.does_end_with_goto():
                if state_name not in self.end_nodes:
                    self.__print_err__(f"State '{state_name}' have a path that does not result in tape action.")
                    return False
            if not state.self_check(list(self.nodes.keys()), self.tape_count, self.alphabet):
                return False
            if not state.check_children(list(self.nodes.keys()), self.tape_count, self.alphabet):
                return False
        return True

    def get_state(self, name: str) -> Node | None:
        return self.nodes[name]

    def __check_end_nodes__(self) -> bool:
        if len(self.end_nodes) == 0:
            self.__print_err__("End states are undefined!")
            return False

        for node in self.end_nodes:
            if node not in self.nodes:
                self.__print_err__(f"End state '{node}' is undefined")
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

        end_token = tokens.__next__()
        if end_token.token != Token.END:
            print_err("Missed END declaration (it should immediately follow the START declaration).", end_token.line)
            return None

        end_state = tokens.__next__()
        end_states = []
        if end_state.token != Token.VAR:
            if end_state.token != Token.TAB_START:
                print_err("END states must be defined either as a single variable or a list of states (expected: END S0/END [S0, S1, S2])", end_state.line)
                return None
            while end_state.token != Token.TAB_END:
                end_state = tokens.__next__()
                if end_state.token != Token.VAR:
                    if end_state.token == Token.TAB_END:
                        break
                    print_err(f"Unexpected token {end_state.token} (expected state variable)", end_state.line)
                    return None
                if end_state.value is None:
                    print_err("Missing variable name declaration", end_state.line)
                    return None
                end_states.append(end_state.value)
                end_state = tokens.__next__()
                if end_state.token != Token.SEPARATOR and end_state.token != Token.TAB_END:
                    print_err(f"Unexpected token {end_state.token} (expected ',' or ']')", end_state.line)
                    return None
        else:
            if end_state.value is None:
                print_err("Missing variable name declaration.", end_state.line)
                return None
            end_states = [end_state.value]
        ast.set_end_nodes(end_states)

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
    start_group_token = tokens_iter.__next__()
    if_node = IfNode(start_group_token.line)
    if is_elif:
        if_node.change_to_elif()

    try:
        if start_group_token.token != Token.GROUP_START:
            print(f"start_group: {start_group_token}")
            print_err("IF statement condition must be inside parenthesis ('(...)').", start_group_token.line)
            return None
        if_cond_group = parse_if_node_group(start_group_token, tokens_iter)
        if if_cond_group is None:
            print_err("First pass of the IF statement parser failed", start_group_token.line)
            return None
        if_cond_group = parse_condition_group(if_cond_group)
        if if_cond_group is None:
            print_err("Second pass of the IF statement parser failed", start_group_token.line)
            return None
        if_cond = parse_condition_group_into_if_condition(if_cond_group)
        if if_cond is None:
            print_err("Fail while parsing IF condition into nodes", start_group_token.line)
            return None
        if_node.set_condition(if_cond)
        then_token = tokens_iter.__next__()
        if_node.add_line(then_token.line)
        if then_token.token != Token.THEN:
            print_err("IF condition group must be followed with the THEN statement.", then_token.line)
            return None
    except StopIteration:
        print_err("Expected THEN tag after IF statement", start_group_token.line)
        return None

    then_node = parse_then_node(tokens_iter)
    if then_node is None:
        return None
    if_node.add_child(then_node)

    return if_node

class IfNodeConditionToken(Enum):
    AND = '&&'
    OR = '||'

class ConditionCompOp:
    def __init__(self, comp_token: IfConditionType, lhs: int, rhs: int | str):
        self.comp = comp_token
        self.lhs = lhs
        self.rhs = rhs

    def __str__(self):
        return f"{self.lhs} {self.comp.value} {self.rhs}"

class ConditionGroup:
    # first_condition: IfNodeCondition
    def __init__(self, first_condition):
        self.first = first_condition

    def __str__(self):
        return f"({self.first})"

class ConditionArg:
    def __init__(self):
        self.comp_op: Optional[ConditionCompOp] = None
        self.cond_group: Optional[ConditionGroup] = None

    def is_comp_op(self) -> bool:
        return self.cond_group is None and self.comp_op is not None

    def is_cond_group(self) -> bool:
        return self.cond_group is not None

    def __str__(self):
        if self.cond_group is not None:
            return f"{self.cond_group}"
        else:
            return f"{self.comp_op}"

class IfNodeCondition:
    def __init__(self, cond_type: IfNodeConditionToken | None = None):
        self.type: Optional[IfNodeConditionToken] = cond_type
        self.lhs: Optional[ConditionArg] = None
        self.rhs: Optional[ConditionArg] = None
        self.next: Optional[IfNodeCondition] = None
        self.prev: Optional[IfNodeCondition] = None

    def __str__(self):
        return f"{self.lhs} {self.type} {self.rhs} | {self.next}"

def get_if_condition_type_from_token(comp_token: TokenValue) -> IfConditionType | None:
    if comp_token.token == Token.EQUAL:
        return IfConditionType.EQUAL
    if comp_token.token == Token.NOT_EQUAL:
        return IfConditionType.NOT_EQUAL
    return None

def get_if_bool_op_token_from_token(bool_token: TokenValue) -> IfNodeConditionToken | None:
    if bool_token.token == Token.AND:
        return IfNodeConditionToken.AND
    if bool_token.token == Token.OR:
        return IfNodeConditionToken.OR
    return None

def parse_if_node_group(current_token: TokenValue, tokens_iter: Iterator[TokenValue]) -> ConditionGroup | None:
    current_cond: Optional[IfNodeCondition] = None
    lhs_arg: Optional[ConditionArg] = None
    while current_token.token != Token.GROUP_END:
        if current_token.token == Token.AND or current_token.token == Token.OR:
            if lhs_arg is None:
                print_err(f"Bool operation ('||' or '&&') must be preceded by a comparision operation or another condition group '(...)'", current_token.line)
                return None
            bool_op_token = get_if_bool_op_token_from_token(current_token)
            if bool_op_token is None:
                print_err(f"Unrecognized bool operation for token {current_token}.", current_token.line)
                return None
            new_cond = IfNodeCondition(bool_op_token)
            if current_cond is not None:
                current_cond.rhs = lhs_arg
                new_cond.prev = current_cond
                current_cond.next = new_cond
            current_cond = new_cond
            current_cond.lhs = lhs_arg

        lhs = tokens_iter.__next__()
        if lhs.token == Token.GROUP_START:
            cond_group = parse_if_node_group(lhs, tokens_iter)
            if cond_group is None:
                return None
            lhs_arg = ConditionArg()
            lhs_arg.cond_group = cond_group
            current_token = tokens_iter.__next__()
            continue

        comp = tokens_iter.__next__()
        rhs = tokens_iter.__next__()

        if lhs.token != Token.VAR:
            print_err(f"Expected tape reference, found '{lhs.token.value}'", lhs.line)
            return None
        if_cond_type = get_if_condition_type_from_token(comp)
        if if_cond_type is None:
            print_err(f"Expected '==' or '!=' comparision operator, found '{comp.token.value}'", comp.line)
            return None
        if rhs.token != Token.VAR and rhs.token != Token.CONST:
            print_err(f"Expected tape reference or const value, found '{rhs.token.value}'", rhs.line)
            return None
        if rhs.value is None:
            print_err(f"No value defined for token '{rhs.token}", rhs.line)
            return None
        lhs_tape_id = get_tape_id(lhs)
        if lhs_tape_id is None:
            print_err(f"Wrong format of tape reference. Expected 'T.<n>'.", lhs.line)
            return None
        if rhs.token == Token.CONST:
            lhs_arg = ConditionArg()
            lhs_arg.comp_op = ConditionCompOp(if_cond_type, lhs_tape_id, rhs.value)
        else:
            rhs_tape_id = get_tape_id(rhs)
            if rhs_tape_id is None:
                print_err(f"Wrong format of tape reference. Expected 'T.<n>'.", rhs.line)
                return None
            lhs_arg = ConditionArg()
            lhs_arg.comp_op = ConditionCompOp(if_cond_type, lhs_tape_id, rhs_tape_id)

        current_token = tokens_iter.__next__()

    if current_cond is not None:
        if lhs_arg is None:
            print_err(f"Missing right side argument for bool operation.", current_token.line)
            return None
        current_cond.rhs = lhs_arg

    if current_cond is None:
        current_cond = IfNodeCondition()
        current_cond.lhs = lhs_arg

    while current_cond.prev is not None:
        current_cond = current_cond.prev

    return ConditionGroup(current_cond)

def parse_condition_group(group: ConditionGroup) -> ConditionGroup | None:
    cond_iter: IfNodeCondition | None = group.first
    prev_cond_iter: IfNodeCondition | None = group.first

    if cond_iter is not None and cond_iter.prev is None and cond_iter.next is None:
        return group

    while cond_iter is not None:
        if cond_iter.lhs is not None and cond_iter.lhs.is_cond_group():
            new_group = parse_condition_group(cond_iter.lhs.cond_group)
            new_arg = ConditionArg()
            new_arg.cond_group = new_group
            cond_iter.lhs = new_arg
        if cond_iter.rhs is not None and cond_iter.rhs.is_cond_group():
            new_group = parse_condition_group(cond_iter.rhs.cond_group)
            new_arg = ConditionArg()
            new_arg.cond_group = new_group
            cond_iter.rhs = new_arg
        if cond_iter.type == IfNodeConditionToken.AND:
            new_group = ConditionGroup(cond_iter)
            new_arg = ConditionArg()
            new_arg.cond_group = new_group
            prev_cond = cond_iter.prev
            next_cond = cond_iter.next
            if prev_cond is not None:
                prev_cond.rhs = new_arg
                prev_cond.next = next_cond
            if next_cond is not None:
                next_cond.lhs = new_arg
                next_cond.prev = prev_cond

            new_group.first.prev = None
            new_group.first.next = None
            prev_cond_iter = prev_cond
            cond_iter = next_cond
        else:
            prev_cond_iter = cond_iter
            cond_iter = cond_iter.next


    if prev_cond_iter is None:
        return None
    while prev_cond_iter.prev is not None:
        prev_cond_iter = prev_cond_iter.prev

    return ConditionGroup(prev_cond_iter)

def parse_condition_group_into_if_condition(group: ConditionGroup) -> IfCondition | None:
    cond_iter: IfNodeCondition | None = group.first
    first: IfCondition | None = None
    if_cond: IfCondition | None = None
    while cond_iter is not None:
        left_arg = cond_iter.lhs
        comp = cond_iter.type
        right_arg = cond_iter.rhs
        if left_arg is None:
            return None
        if comp is None:
            return parse_if_condition(left_arg)
        if right_arg is None:
            return None
        if if_cond is None:
            if_cond = parse_if_condition(left_arg)
            first = if_cond
            if if_cond is None:
                return None
        right_side_if_cond = parse_if_condition(right_arg)
        if cond_iter.type == IfNodeConditionToken.OR:
            if_cond.next = right_side_if_cond
            if_cond = right_side_if_cond
        else:
            if_cond.down = right_side_if_cond
        cond_iter = cond_iter.next

    return first

def parse_if_condition(arg: ConditionArg) -> IfCondition | None:
    if arg.is_cond_group():
        return parse_condition_group_into_if_condition(arg.cond_group)

    if arg.comp_op is None:
        return None

    return IfCondition(arg.comp_op.comp, arg.comp_op.lhs, arg.comp_op.rhs)

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

