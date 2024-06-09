from src.turing_machine.machine import TuringMachine
from src.config.config import Config
from typing import List

def parse_tape_value_result(result: List[str | int], tape_value: List[str]) -> List[str]:
    return [val if type(val).__name__ == "str" else tape_value[val] for val in result]

class ASTTuringMachine(TuringMachine):
    def __init__(self, cfg: Config, is_debug_mode: bool = False):
        self.program = cfg.program
        self.is_debug_mode = is_debug_mode
        initial_state = cfg.program.start_node
        final_states = cfg.program.end_nodes
        if initial_state is None or final_states is None:
            raise Exception("Initial state or final states are undefined in the config file")
        super().__init__(cfg.tapes, initial_state, final_states)

    def run_state(self, state: str, tape_values: List[str]) -> tuple[str, List[str], List[int]]:
        current_state = self.program.get_state(state)
        if current_state is None:
            raise Exception(f"State {state} is undefined")
        if self.is_debug_mode:
            print("--------------------------------------------------------------------------------")
        result = current_state.execute(tape_values, self.is_debug_mode)
        if self.is_debug_mode:
            print("--------------------------------------------------------------------------------")
        if result is None:
            raise Exception(f"Failed when running state {state}")

        return (result.new_state, parse_tape_value_result(result.tape_value, tape_values), result.tape_movement)

