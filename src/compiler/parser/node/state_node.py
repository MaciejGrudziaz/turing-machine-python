from src.compiler.parser.node.node import Node, NodeType, NodeExecuteResult
from src.compiler.tokenizer.tokenizer import SectionLine, Token, TokenValue, TokenizerProgram, TokenizerResult
from typing import List

class StateNode(Node):
    def __init__(self, name: str, line: SectionLine):
        super().__init__(NodeType.STATE, line)
        self.name = name

    def execute(self, tape_state: List[str], is_debug_mode: bool = False) -> NodeExecuteResult | None:
        if is_debug_mode:
            print(f"    > Current state: {self.name}")
            print(f"{self}")
        return super().execute(tape_state, is_debug_mode)

