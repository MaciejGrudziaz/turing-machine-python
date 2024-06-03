from dataclasses import dataclass
import re
from typing import List, Dict
from enum import Enum

class Token(Enum):
    START = 0
    END = 1
    GOTO = 2
    IF = 3
    THEN = 4
    ELSE = 5
    ELSE_IF = 6
    MOV_L = 7
    MOV_R = 8
    TAB_START = 9
    TAB_END = 10
    SECTION_START = 11
    SECTION_END = 12
    EQUAL = 13
    NOT_EQUAL = 14
    AND = 15
    ASSIGN = 15
    SEPARATOR = 17
    VAR = 18
    CONST = 19

@dataclass
class SectionLine:
    no: int
    value: str

@dataclass
class TokenValue:
    token: Token
    value: str | None
    line: SectionLine

@dataclass
class TokenizerProgram:
    tokens: List[TokenValue]

@dataclass
class TokenizerResult:
    alphabet: List[str]
    tapes: List[List[str]]
    program_content: TokenizerProgram

@dataclass
class TokenizerSection:
    name: str
    content: List[SectionLine]

class TokenizerError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

__MANDATORY_SECTIONS__ = ["tape", "program"]

def tokenize(config: str) -> TokenizerResult | None:
    current_section = None
    result = TokenizerResult(alphabet=[], tapes=[], program_content=TokenizerProgram(tokens=[]))
    found_sections = []
    for line_no, line in enumerate(config.split("\n")):
        line_no = line_no + 1
        line = line.strip()
        if line == "":
            continue
        if line.startswith("#"):
            continue
        pattern = r'^\[(\w+)\]$'
        match = re.search(pattern, line)
        if match:
            section_name = match.group(1)
            found_sections.append(section_name)
            if current_section is None:
                current_section = TokenizerSection(name=section_name, content=[])
            else:
                if current_section.name != section_name:
                    if not __parse_section__(result, current_section):
                        return None
                    current_section = TokenizerSection(name=section_name, content=[])
                else:
                    print(f"Failed to tokenize the config file. Found multiple definitions of the same section in line {line_no} (section='{section_name}')")
                    return None
        else:
            if current_section is None:
                print(f"Failed to tokenize the config file. Line: '{line_no}: {line}' doesn't belong to any section.")
            else:
                current_section.content.append(SectionLine(no=line_no, value=line))

    if current_section is not None:
        if not __parse_section__(result, current_section):
            return None

    for section in __MANDATORY_SECTIONS__:
        if section not in found_sections:
            print(f"Failed to tokenize the config. Section {section} is not defined.")
            return None

    if not __check_tapes__(result):
        return None

    return result

def __parse_section__(result: TokenizerResult, section: TokenizerSection) -> bool:
    if section.name.lower() == "tape":
        return __parse_tapes_section__(result, section)
    if section.name.lower() == "program":
        program = __tokenize_program_section__(section)
        if program is not None:
            result.program_content = program
        return program is not None

    print(f"Failed to tokenize the config. Section {section.name} is not allowed")
    return False

def __parse_tape_section_alphabet__(value: str, line_no: int, line: str) -> List[str] | None:
    alphabet = []
    for alphabet_val in value.split(","):
        alphabet_val_pattern = r'^(\w)-(\w)$'
        alphabet_val = alphabet_val.strip()

        val_match = re.search(alphabet_val_pattern, alphabet_val)
        if val_match is None:
            wrong_range_pattern = r'^(\w+)-(\w+)$'
            if re.search(wrong_range_pattern, alphabet_val) is not None:
                print(f"Failed to parse alphabet value in [machine] section. Range can only be defined with single character values ({line_no}: {line}, wrong range: {alphabet_val}).")
                return None
            if alphabet_val not in alphabet:
                alphabet.append(alphabet_val)
        else:
            start = val_match.group(1)
            end = val_match.group(2)
            if ord(start) > ord(end):
                print(f"Failed to parse alphabet value in [machine] section. In range {alphabet_val}, value {start} is greater than {end}, could not iterate through range")
                return None
            for i in range(ord(start), ord(end) + 1):
                if chr(i) not in alphabet:
                    alphabet.append(chr(i))

    return alphabet

@dataclass
class TokenizerTape:
    index: int
    content: List[str]

def __parse_tapes_section__(result: TokenizerResult, section: TokenizerSection) -> bool:
    tape_pattern = r'^T\.(\d+)[ ]*=[ ]*\[(.+)\]$'
    alphabet_pattern = r'^alphabet[ ]*=[ ]*\[(.+)\]$'
    tapes = []
    is_alphabet_defined = False
    for line in section.content:
        line_str = line.value.strip()
        match = re.search(tape_pattern, line_str)
        if match is None:
            match = re.search(alphabet_pattern, line_str)
            if match is None:
                print(f"Failed to parse [tape] section. Error at line '{line.no}: {line.value}'. Expected format: T.<n> = [<value1>, <value2>, ...] or alphabet = [<value1>, <value2>, ...]")
                return False
            if is_alphabet_defined:
                print(f"Failed to parse [tape] section. Multiple alphabet definitions at line '{line.no}: {line.value}'")
                return False
            alphabet = __parse_tape_section_alphabet__(match.group(1), line.no, line.value)
            if alphabet is None:
                return False
            is_alphabet_defined = True
            result.alphabet = alphabet
        else:
            try:
                tape_id = int(match.group(1))
            except ValueError:
                print(f"Failed to parse [tape] section. Wrong tape name at line '{line.no}: {line.value}'. Expected name: T.<n>")
                return False
            for tape in tapes:
                if tape.index == tape_id:
                    print(f"Failed to parse [tape] section. Multiple definitions of tape {tape_id} at line '{line.no}: {line.value}'.")
                    return False
            tapes.append(TokenizerTape(index=tape_id, content=list(map(lambda val: val.strip(), match.group(2).split(",")))))

    if not is_alphabet_defined:
        print(f"Failed to parse [tape] section. Alphabet was not defined.")
        return False

    if len(tapes) == 0:
        print(f"Failed to parse [tape] section. No tape was defined.")
        return False

    tapes.sort(key=lambda tape: tape.index)
    for index, tape in enumerate(tapes):
        if index != tape.index:
            print(f"Failed to parse [tapes] section. Tape T.{tape.index} is defined out of order (the tapes must be defined starting from index 0, without any breaks in between)")
            return False

    result.tapes = list(map(lambda tape: tape.content, tapes))
    return True

def __check_tapes__(result: TokenizerResult) -> bool:
    for tape_id, tape in enumerate(result.tapes):
        for character in tape:
            if not character in result.alphabet:
                print(f"Failed to parse [tapes] section. Character '{character}' in tape T.{tape_id} is not defined in the alphabet.")
                return False
    return True

def __tokenize_program_section__(section: TokenizerSection) -> TokenizerProgram | None:
    tokens = []
    for line in section.content:
        if line.value.startswith("#"):
            continue
        line_str = re.sub(r'\s+', ' ', line.value.lower())
        try:
            for word in line_str.split(" "):
                if word == "start":
                    tokens.append(TokenValue(token=Token.START, value=None, line=line))
                elif word == "end":
                    tokens.append(TokenValue(token=Token.END, value=None, line=line))
                elif word == "goto":
                    tokens.append(TokenValue(token=Token.GOTO, value=None, line=line))
                elif word == "if":
                    tokens.append(TokenValue(token=Token.IF, value=None, line=line))
                elif word == "then":
                    tokens.append(TokenValue(token=Token.THEN, value=None, line=line))
                elif word == "else":
                    tokens.append(TokenValue(token=Token.ELSE, value=None, line=line))
                elif word == "elif":
                    tokens.append(TokenValue(token=Token.ELSE_IF, value=None, line=line))
                elif word == "mov_l":
                    tokens.append(TokenValue(token=Token.MOV_L, value=None, line=line))
                elif word == "mov_r":
                    tokens.append(TokenValue(token=Token.MOV_R, value=None, line=line))
                elif word == "[":
                    tokens.append(TokenValue(token=Token.TAB_START, value=None, line=line))
                elif word == "]":
                    tokens.append(TokenValue(token=Token.TAB_END, value=None, line=line))
                elif word == "{":
                    tokens.append(TokenValue(token=Token.SECTION_START, value=None, line=line))
                elif word == "}":
                    tokens.append(TokenValue(token=Token.SECTION_END, value=None, line=line))
                elif word == "==":
                    tokens.append(TokenValue(token=Token.EQUAL, value=None, line=line))
                elif word == "!=":
                    tokens.append(TokenValue(token=Token.NOT_EQUAL, value=None, line=line))
                elif word == "&&":
                    tokens.append(TokenValue(token=Token.AND, value=None, line=line))
                else:
                    letters = []
                    SINGLE_CHAR_TOKENS = [":", "{", "}", "[", "]", ","]
                    for c in word:
                        value = "".join(letters)
                        if c == "=":
                            if len(letters) == 0:
                                letters.append(c)
                            elif len(letters) == 1 and letters[0] == "=":
                                tokens.append(TokenValue(token=Token.EQUAL, value=None, line=line))
                                letters = []
                            elif len(letters) == 1 and letters[0] == "!":
                                tokens.append(TokenValue(token=Token.NOT_EQUAL, value=None, line=line))
                                letters = []
                            else:
                                tokens.append(__parse_non_special_token__(value, line=line))
                                letters = []
                        elif c == "!":
                            if len(letters) == 0:
                                letters.append(c)
                            else:
                                tokens.append(__parse_non_special_token__(value, line=line))
                                letters = ["!"]
                        elif c in SINGLE_CHAR_TOKENS:
                            tokens.append(__parse_non_special_token__(value, line=line))
                            letters = []
                            if c == ":":
                                tokens.append(TokenValue(token=Token.ASSIGN, value=None, line=line))
                            elif c == "{":
                                tokens.append(TokenValue(token=Token.SECTION_START, value=None, line=line))
                            elif c == "}":
                                tokens.append(TokenValue(token=Token.SECTION_END, value=None, line=line))
                            elif c == "[":
                                tokens.append(TokenValue(token=Token.TAB_START, value=None, line=line))
                            elif c == "]":
                                tokens.append(TokenValue(token=Token.TAB_END, value=None, line=line))
                            elif c == ",":
                                tokens.append(TokenValue(token=Token.SEPARATOR, value=None, line=line))
                            else:
                                raise TokenizerError("Compiler error. Missed the handler for the single char token '{c}'")
                        else:
                            letters.append(c)
                    if len(letters) != 0:
                        tokens.append(__parse_non_special_token__("".join(letters), line))
        except TokenizerError as e:
           print(f"Failed to tokenize the program at line '{line.no}: {line.value}' {e}")
           return None

    return TokenizerProgram(tokens=list(filter(lambda token: token is not None, tokens)))

def __parse_non_special_token__(value: str, line: SectionLine) -> TokenValue | None:
    if len(value) == 0:
        return None

    if __check_if_const_value__(value):
        return TokenValue(token=Token.CONST, value=value[1:-1], line=line)

    SPECIAL_TOKENS = ["=", "!", ",", "{", "}", "[", "]", ":", "\"", "&"]
    for token in SPECIAL_TOKENS:
        if token in value:
            raise TokenizerError(f"Restricted token '{token}' found in the value.")

    if value == "mov_l":
        return TokenValue(token=Token.MOV_L, value=None, line=line)
    elif value == "mov_r":
        return TokenValue(token=Token.MOV_R, value=None, line=line)
    return TokenValue(token=Token.VAR, value=value, line=line)

def __check_if_const_value__(value: str) -> bool:
    if len(value) < 2:
        return False
    if value[0] != "\"" or value[-1] != "\"":
        return False

    prev_char = None
    for c in value[1:-1]:
        if c == "\"":
            if prev_char is None or prev_char != "\\":
                raise TokenizerError(f"Found unescaped character '\"' inside constant value definition.")
        prev_char = c
    return True

