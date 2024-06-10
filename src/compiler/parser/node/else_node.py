from typing import List
from src.compiler.tokenizer.tokenizer import SectionLine, Token, TokenValue, TokenizerProgram, TokenizerResult
from src.compiler.parser.node.node import Node, NodeExecuteResult, NodeType

class ElseNode(Node):
    def __init__(self, line: SectionLine):
        super().__init__(NodeType.ELSE, line)

    def execute(self, tape_state: List[str], is_debug_mode: bool = False) -> NodeExecuteResult | None:
        if is_debug_mode:
            print("    > Running ELSE statement")
            print(f"{self}")
        return super().execute(tape_state, is_debug_mode)

