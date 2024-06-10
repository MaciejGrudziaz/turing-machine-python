from typing import List
from src.compiler.tokenizer.tokenizer import Token, TokenizerProgram
from src.compiler.parser import print_err
from src.compiler.parser.node.node import Node
from src.compiler.parser.node.parsers.state_parser import parse_state
from src.compiler.parser.node.parsers.node_parser import parse_node

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
            state = parse_state(tokens, parse_node)
            if state is None:
                return None
            ast.add_node(state.name, state)
    except StopIteration:
        pass

    return ast


