from abc import ABC, abstractmethod

class Tape:
    def __init__(self, tape):
        self.tape = tape
        self.head = 0

    def move_left(self):
        if self.head <= 0:
            raise Exception("Tape head moved out of bounds (less than 0)")
        self.head -= 1

    def move_right(self):
        if self.head >= len(self.tape) - 1:
            raise Exception("Tape head moved out of bounds (greater than tape length)")
        self.head += 1

    def get_value(self):
        return self.tape[self.head]

    def set_value(self, val):
        self.tape[self.head] = val

    def clone(self):
        return Tape(self.tape[:])

    def __str__(self):
        tape_str = ", ".join(self.tape)
        tape_str_with_head = tape_str[:self.head*3] + f"[{self.tape[self.head]}]" + tape_str[self.head*3 + 1:]
        return f"[{tape_str_with_head}]"

class TuringMachine(ABC):
    def __init__(self, tapes, initial_state, final_states):
        self.initial_tapes = [Tape(tape) for tape in tapes]
        self.initial_state = initial_state
        self.final_states = final_states
        self.tapes = None
        self.state = None
        self.reset()

    def reset(self):
        self.tapes = [tape.clone() for tape in self.initial_tapes]
        self.state = self.initial_state

    def get_tapes_values(self):
        return [tape.get_value() for tape in self.tapes]

    def get_tape_positions(self):
        return [tape.head for tape in self.tapes]

    @abstractmethod
    def run_state(self, state, tape_values):
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
        tape_state = self.get_tapes_values()
        new_state, new_values, operations = self.run_state(self.state, tape_state)
        self.state = new_state
        self.set_tapes(new_values)
        self.move_tapes(operations)
        return self.state

    def run(self):
        while self.state not in self.final_states:
            self.step()
            self.print_status()

    def run_auto(self):
        while self.state not in self.final_states:
            self.step()

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
        return self.get_tape_positions()
