from typing import Dict, Iterator, List, Optional, Tuple, Union
from src.compiler.tokenizer.tokenizer import SectionLine, Token, TokenValue, TokenizerProgram, TokenizerResult
from enum import Enum
from src.compiler.parser.node.if_node import IfNode, IfCondition, IfConditionType
from src.compiler.parser import print_err, get_tape_id

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

#    then_node = parse_then_node(tokens_iter)
#    if then_node is None:
#        return None
#    if_node.add_child(then_node)

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


