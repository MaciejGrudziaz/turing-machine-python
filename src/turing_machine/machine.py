class TuringMachine:
    def __init__(self, tape, initial_state, final_states, transition_function):
        self.tape = list(tape)
        self.head = 0
        self.state = initial_state
        self.final_states = final_states
        self.transition_function = transition_function
        self.match_position = -1

    def step(self):
        current_char = self.tape[self.head]
        if (self.state, current_char) in self.transition_function:
            next_state, write_char, direction = self.transition_function[(self.state, current_char)]
            self.tape[self.head] = write_char
            self.state = next_state
            if direction == 'R':
                self.head += 1
            elif direction == 'L':
                self.head -= 1
            if self.state in self.final_states:
                self.match_position = self.head
        else:
            raise Exception("Error")

    def run(self):
        while self.state not in self.final_states:
            self.step()

    def get_tape(self):
        return ''.join(self.tape)

    def get_match_position(self):
        return self.match_position

def build_transition_function(substring):
    transition_function = {}
    for i, char in enumerate(substring):
        transition_function[(f'q{i}', char)] = (f'q{i+1}', char, 'R')
    transition_function[(f'q{len(substring)}', '_')] = (f'q{len(substring)}', '_', 'R')
    return transition_function