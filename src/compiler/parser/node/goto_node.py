from typing import Dict, List, Tuple
from src.compiler.tokenizer.tokenizer import SectionLine, Token, TokenValue, TokenizerProgram, TokenizerResult
from src.compiler.parser.node.node import Node, NodeType, NodeExecuteResult
from src.compiler.parser import get_tape_id, print_err

class GotoNode(Node):
    def __init__(self, line: SectionLine):
        super().__init__(NodeType.GOTO, line)
        self.execute_result = None
        self.next_state = None
        self.tape_values = {}
        self.tape_movement = {}

    def add_execution_result(self, next_state: TokenValue, actions: List[Tuple[TokenValue, TokenValue, TokenValue]]) -> bool:
        if next_state.value is None:
            return False
        self.add_line(next_state.line)

        tape_movement = {}
        tape_values = {}

        for tape_id, value_token, move in actions:
            tape_id_val = get_tape_id(tape_id)
            if tape_id_val is None:
                print_err("Wrong tape reference format. Expected: T.<n>", tape_id.line)
                return False
            if tape_id_val in tape_values:
                print_err(f"Multiple action definitions for tape T.{tape_id_val}", tape_id.line)
                return False
            if value_token.value is None:
                print_err(f"Wrong next tape value format. Expected variable or const value declaration.", value_token.line)
                return False
            if value_token.token == Token.CONST:
                tape_values[tape_id_val] = value_token.value
            elif value_token.token == Token.VAR:
                value = get_tape_id(value_token)
                if value is None:
                    print_err("Wrong tape reference format, in next tape value declaration. Expected: T.<n>", value_token.line)
                    return False
                tape_values[tape_id_val] = value
            else:
                print_err("Wrong next tape value format. Exepected variable or const value declaration.", value_token.line)
                return False

            if move.token == Token.MOV_L:
                tape_movement[tape_id_val] = -1
            elif move.token == Token.MOV_R:
                tape_movement[tape_id_val] = 1
            elif move.token == Token.STAY:
                tape_movement[tape_id_val] = 0
            else:
                print_err("Wrong tape movement value. Expected MOV_L or MOV_R", move.line)
                return False

            self.add_line(tape_id.line)
            self.add_line(value_token.line)
            self.add_line(move.line)

        if not self.__set_goto_state_actions__(next_state.value, tape_movement, tape_values):
            return False

        return True

    def __set_goto_state_actions__(self, next_state: str, tape_movement: Dict[int, int], tape_values: Dict[int, str | int]) -> bool:
        self.next_state = next_state
        self.tape_values = tape_values
        self.tape_movement = tape_movement
        return True

    def self_check(self, states: List[str], tape_count: int, alphabet: List[str]) -> bool:
        execute_result = self.__parse_execute_result__(tape_count)
        if execute_result is None:
            return False
        self.execute_result = execute_result

        if self.execute_result.new_state not in states:
            self.__print_err__(f"State '{self.execute_result.new_state}' is not defined")
            return False
        for move in self.execute_result.tape_movement:
            if move not in [-1, 0, 1]:
                self.__print_err__(f"Unrecognized tape move value: {move}.")
                return False
        for value in self.execute_result.tape_value:
            if type(value).__name__ == "int":
                if value < 0 or value >= tape_count:
                    self.__print_err__(f"Tape T.{value} is undefined")
                    return False
            else:
                if value not in alphabet:
                    self.__print_err__(f"Value '{value}' is not defined in the alphabet")
                    return False
        return True

    def __parse_execute_result__(self, tape_count: int) -> NodeExecuteResult | None:
        tape_values = []
        tape_mov = []

        if self.next_state is None:
            self.__print_err__("Next state is not defined")
            return None

        for i in range(tape_count):
            val = self.tape_values.get(i)
            move = self.tape_movement.get(i)
            if val is None or move is None:
                tape_values.append(i)
                tape_mov.append(0)
            else:
                tape_values.append(val)
                tape_mov.append(move)

        return NodeExecuteResult(tape_movement=tape_mov, tape_value=tape_values, new_state=self.next_state)

    def execute(self, tape_state: List[str], is_debug_mode: bool = False) -> NodeExecuteResult | None:
        if is_debug_mode:
            print(f"    > Changing state:")
            print(f"{self}")
        return self.execute_result

