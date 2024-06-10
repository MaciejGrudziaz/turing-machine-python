from typing import Callable, Dict, Iterator, List, Optional, Tuple, Union
from src.compiler.tokenizer.tokenizer import SectionLine, Token, TokenValue, TokenizerProgram, TokenizerResult
from src.compiler.parser import print_err
from src.compiler.parser.node.then_node import ThenNode
from src.compiler.parser.node.node import Node

def parse_then_node(tokens_iter: Iterator[TokenValue], parse_node: Callable[[TokenValue, Iterator[TokenValue]], Node | None]) -> ThenNode | None:
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


