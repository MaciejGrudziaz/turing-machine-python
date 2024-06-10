from typing import Iterator
from src.compiler.tokenizer.tokenizer import Token, TokenValue
from src.compiler.parser.node.goto_node import GotoNode
from src.compiler.parser import print_err

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


