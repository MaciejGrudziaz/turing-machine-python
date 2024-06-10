from typing import Iterator
from src.compiler.tokenizer.tokenizer import Token, TokenValue

from src.compiler.parser.node.node import Node
from src.compiler.parser import print_err

from src.compiler.parser.node.if_node import IfNode
from src.compiler.parser.node.parsers.if_node_parser import parse_if_node
from src.compiler.parser.node.parsers.then_node_parser import parse_then_node
from src.compiler.parser.node.parsers.else_node_parser import parse_else_node
from src.compiler.parser.node.parsers.goto_node_parser import parse_goto_node

def parse_node(current_token: TokenValue, tokens_iter: Iterator[TokenValue]) -> Node | None:
    if current_token.token == Token.IF:
        return parse_if_then_node(tokens_iter, is_elif=False)
    elif current_token.token == Token.ELSE_IF:
        return parse_if_then_node(tokens_iter, is_elif=True)
    elif current_token.token == Token.ELSE:
        return parse_else_node(tokens_iter, parse_node)
    elif current_token.token == Token.GOTO:
        return parse_goto_node(tokens_iter)
    else:
        print_err(f"Unexpected token {current_token.token}", current_token.line)
        return None

def parse_if_then_node(tokens_iter: Iterator[TokenValue], is_elif: bool) -> IfNode | None:
    if_node = parse_if_node(tokens_iter, is_elif)
    if if_node is None:
        return None
    then_node = parse_then_node(tokens_iter, parse_node)
    if then_node is None:
        return None
    if_node.add_child(then_node)
    return if_node


