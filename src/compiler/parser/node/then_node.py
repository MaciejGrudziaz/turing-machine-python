from src.compiler.tokenizer.tokenizer import SectionLine
from src.compiler.parser.node.node import Node, NodeType

class ThenNode(Node):
    def __init__(self, line: SectionLine):
        super().__init__(NodeType.THEN, line)

