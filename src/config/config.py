from dataclasses import dataclass
from typing import List

@dataclass
class ConfigAST:
    structure: str

@dataclass
class Config:
    tape_count: int
    alphabet: List[str]
    tapes: List[List[str]]
    program: ConfigAST

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

    return load_from_string("\n".join(file_content))

def load_from_string(config: str) -> Config:
    pass

