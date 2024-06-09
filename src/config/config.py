from dataclasses import dataclass
from typing import List
from src.config.tokenizer import tokenize
from src.config.parser import parse_program, ProgramAST

@dataclass
class Config:
    alphabet: List[str]
    tapes: List[List[str]]
    program: ProgramAST

def load_from_file(filepath: str) -> Config | None:
    file_content = None

    try:
        with open(filepath) as f:
            file_content = f.readlines()
    except FileNotFoundError:
        print(f"The file {filepath} was not found.")
    except PermissionError:
        print(f"You don not have permissions to read the file {filepath}")
    except IOError as e:
        print(f"An I/O error occured: {e.strerror}")
    except Exception as e:
        print(f"An unexpected error occured: {e}")

    if file_content is None:
        print(f"Failed to read config file")
        return None

    return load_from_string("".join(file_content))

def load_from_string(config: str) -> Config | None:
    tokenizer_result = tokenize(config)
    if tokenizer_result is None:
        return None

    program = parse_program(tokenizer_result.program_content, len(tokenizer_result.tapes), tokenizer_result.alphabet)
    if program is None:
        return None

    if not program.check_syntax():
        return None

    return Config(alphabet=tokenizer_result.alphabet, tapes=tokenizer_result.tapes, program=program)

