from typing import Iterator, Callable
from src.compiler.tokenizer.tokenizer import SectionLine, Token, TokenValue, TokenizerProgram, TokenizerResult
from src.compiler.parser.node.else_node import ElseNode
from src.compiler.parser import print_err
from src.compiler.parser.node.node import Node

def parse_else_node(tokens_iter: Iterator[TokenValue], parse_node: Callable[[TokenValue, Iterator[TokenValue]], Node | None]) -> ElseNode | None:
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


