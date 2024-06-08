from abc import ABC, abstractmethod

class Tape:
    def __init__(self, tape):
        self.tape = list(tape)
        self.head = 0

    def move_left(self):
        self.head -= 1

    def move_right(self):
        self.head += 1

    def get_value(self):
        return self.tape[self.head]

    def set_value(self, val):
        self.tape[self.head] = val

    def __str__(self):
        return ''.join(self.tape)


class TuringMachine(ABC):
    def __init__(self, tapes, initial_state, final_states):
        self.initial_tapes = [Tape(tape) for tape in tapes]
        self.initial_state = initial_state
        self.final_states = final_states
        self.reset()

    def reset(self):
        self.tapes = [Tape(tape.tape) for tape in self.initial_tapes]
        self.state = self.initial_state
        self.match_position = -1

    def get_tapes(self):
        return [tape.tape for tape in self.tapes]

    @abstractmethod
    def run_auto(self):
        pass

    def set_tapes(self, new_values):
        for tape, value in zip(self.tapes, new_values):
            tape.set_value(value)

    def move_tapes(self, operations):
        for tape, operation in zip(self.tapes, operations):
            if operation == 1:
                tape.move_right()
            elif operation == -1:
                tape.move_left()

    def step(self):
        tape_state = self.get_tapes()
        new_state, new_values, operations = self.run_auto()
        self.state = new_state
        self.set_tapes(new_values)
        self.move_tapes(operations)
        if self.state in self.final_states:
            self.match_position = [tape.head for tape in self.tapes]
        return self.state

    def run(self):
        while self.state not in self.final_states:
            self.step()
            self.print_status()

    def run_tick(self):
        while self.state not in self.final_states:
            input("Press Enter to execute the next step...")
            self.step()
            self.print_status()

    def print_status(self):
        tapes_str = ' | '.join([str(tape) for tape in self.tapes])
        heads_str = ' | '.join([str(tape.head) for tape in self.tapes])
        print(f"Tapes: {tapes_str}")
        print(f"Head Positions: {heads_str}")
        print(f"Current State: {self.state}")

    def get_match_position(self):
        return self.match_position
