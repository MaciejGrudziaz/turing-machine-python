from typing import Iterator, Callable
from src.compiler.tokenizer.tokenizer import SectionLine, Token, TokenValue, TokenizerProgram, TokenizerResult
from enum import Enum
from src.compiler.parser.node.if_node import IfNode, IfCondition, IfConditionType
from src.compiler.parser import print_err, get_tape_id

from src.compiler.parser.node.state_node import StateNode
from src.compiler.parser.node.node import Node

def parse_state(tokens_iter: Iterator[TokenValue], parse_node: Callable[[TokenValue, Iterator[TokenValue]], Node | None]) -> StateNode | None:
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
