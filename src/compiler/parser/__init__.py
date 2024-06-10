from src.compiler.tokenizer.tokenizer import SectionLine, Token, TokenValue
import re

def get_tape_id(token: TokenValue) -> int | None:
    if token.token != Token.VAR or token.value is None:
        return None
    tape_id_pattern = r'^t\.(\d+)$'
    match = re.search(tape_id_pattern, token.value)

    if match is None:
        return None

    try:
        return int(match.group(1))
    except Exception:
        return None

def print_err(message: str, line: SectionLine):
    print(f"Error at line '{line.no}: {line.value}'. Failed to parse program code. {message}")


