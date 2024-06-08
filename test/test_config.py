from src.config.parser import parse_program
from src.config.tokenizer import SectionLine, TokenizerSection, tokenize, __tokenize_program_section__, Token

def test_tokenize():
    config = r'''
[tape]
alphabet = [1, 2 ,3, 4, a-d, 4-9]
T.0 = [a, b, c, d, 1, 3, 3, 2]

[program]
# comment 1
START S0
# comment 2
END S0
S0 {
  IF T.0 == "1" THEN
    GOTO S1 {
      T.0: ["1", MOV_R]
    }
  ELSE
    GOTO S0 {
      T.0: [T.0, MOV_R]
    }
}

S1 {
  GOTO S0 {
    T.0: [T.0, MOV_L]
  }
}
    '''

    result = tokenize(config)

    assert result is not None
    assert result.alphabet == ["1", "2", "3", "4", "a", "b", "c", "d", "5", "6", "7", "8", "9"]
    assert len(result.tapes) == 1
    assert result.tapes[0] == ["a", "b", "c", "d", "1", "3", "3", "2"]
    assert len(result.program_content.tokens) == 49

def test_program_tokenize():
    program = r'START GOTO abc [test123: "457"]'
    result = __tokenize_program_section__(TokenizerSection(name="program", content=[SectionLine(no=0, value=program)]))

    assert result is not None
    assert len(result.tokens) == 8
    assert result.tokens[0].token == Token.START
    assert result.tokens[1].token == Token.GOTO
    assert result.tokens[2].token == Token.VAR
    assert result.tokens[2].value == "abc"
    assert result.tokens[3].token == Token.TAB_START
    assert result.tokens[4].token == Token.VAR
    assert result.tokens[4].value == "test123"
    assert result.tokens[5].token == Token.ASSIGN
    assert result.tokens[6].token == Token.CONST
    assert result.tokens[6].value == "457"
    assert result.tokens[7].token == Token.TAB_END

def test_program_tokenize_comments():
    program = r'''
# this is a comment line
start s0 goto abc
{
   test_line:without_spaces[123:"456"]
}
    '''

    result = __tokenize_program_section__(TokenizerSection(name="program", content=list(map(lambda enum_line: SectionLine(no=enum_line[0], value=enum_line[1]), enumerate(program.split("\n"))))))

    assert result is not None

    print(result.tokens)

    assert len(result.tokens) == 14
    assert result.tokens[0].token == Token.START
    assert result.tokens[1].token == Token.VAR
    assert result.tokens[1].value == "s0"
    assert result.tokens[2].token == Token.GOTO
    assert result.tokens[3].token == Token.VAR
    assert result.tokens[3].value == "abc"
    assert result.tokens[4].token == Token.SECTION_START
    assert result.tokens[5].token == Token.VAR
    assert result.tokens[5].value == "test_line"
    assert result.tokens[6].token == Token.ASSIGN
    assert result.tokens[7].token == Token.VAR
    assert result.tokens[7].value == "without_spaces"
    assert result.tokens[8].token == Token.TAB_START
    assert result.tokens[9].token == Token.VAR
    # add a case to tokenizer such that the VAR name can't start with a number
    assert result.tokens[9].value == "123"
    assert result.tokens[10].token == Token.ASSIGN
    assert result.tokens[11].token == Token.CONST
    assert result.tokens[11].value == "456"
    assert result.tokens[12].token == Token.TAB_END
    assert result.tokens[13].token == Token.SECTION_END

def test_program_parser():
    program = r'''
START S0
END S0
S0 {
    IF T.0 == "1" && T.1 == "0" THEN {
      GOTO S0 {
        T.0: ["0", MOV_L],
        T.1: ["1", MOV_R],
      }
    } ELIF T.0 == T.1 THEN {
        GOTO S0 {
          T.0: [T.1, MOV_L]
          T.1: [T.1, MOV_L]
        }
    } ELSE {
      GOTO S0 {
        T.0: ["1", MOV_R],
        T.1: ["0", MOV_L]
      }
    }
}
    '''

    tokenizer_result = __tokenize_program_section__(TokenizerSection(name="program", content=list(map(lambda enum_line: SectionLine(no=enum_line[0], value=enum_line[1]), enumerate(program.split("\n"))))))

    assert tokenizer_result is not None

    result = parse_program(tokenizer_result, 2, ["0", "1"])

    assert result is not None
    assert result.start_node is not None
    assert result.start_node == "s0"
    assert len(result.nodes) == 1
    assert result.nodes["s0"] is not None

    assert result.check_syntax()

def test_program_parser_single_if():
    program = r'''
START S0
END S0
S0 {
    IF T.0 == "1" && T.1 == "0" THEN {
      GOTO S1 {
        T.0: ["0", MOV_L],
        T.1: ["1", MOV_R],
      }
    }
}
'''

    tokenizer_result = __tokenize_program_section__(TokenizerSection(name="program", content=list(map(lambda enum_line: SectionLine(no=enum_line[0], value=enum_line[1]), enumerate(program.split("\n"))))))

    assert tokenizer_result is not None

    result = parse_program(tokenizer_result, 2, ["0", "1"])

    assert result is not None
    assert not result.check_syntax()

def test_porgram_parser_single_else():
    program = r'''
START S0
END S0
S0 {
    ELSE {
      GOTO S1 {
        T.0: ["0", MOV_L],
        T.1: ["1", MOV_R],
      }
    }
}
'''

    tokenizer_result = __tokenize_program_section__(TokenizerSection(name="program", content=list(map(lambda enum_line: SectionLine(no=enum_line[0], value=enum_line[1]), enumerate(program.split("\n"))))))

    assert tokenizer_result is not None

    result = parse_program(tokenizer_result, 2, ["0", "1"])

    assert result is not None
    assert not result.check_syntax()

def test_program_parser_if_chain():
    program = r'''
START S0
END S0
S0 {
    IF T.0 == "1" THEN {
      GOTO S0 {
        T.0: ["0", MOV_L]
      }
    }
    ELIF T.0 == "1" THEN {
      GOTO S0 {
        T.0: [T.0, MOV_L]
      }
    }
    ELIF T.0 == "1" THEN {
      GOTO S0 {
        T.0: ["0", MOV_L]
      }
    }
    ELSE {
      GOTO S0 {
        T.0: ["0", MOV_L]
      }
    }
}
'''

    tokenizer_result = __tokenize_program_section__(TokenizerSection(name="program", content=list(map(lambda enum_line: SectionLine(no=enum_line[0], value=enum_line[1]), enumerate(program.split("\n"))))))

    assert tokenizer_result is not None

    result = parse_program(tokenizer_result, 1, ["0", "1"])

    assert result is not None
    assert result.check_syntax()

def test_end_declaration():
    program = r'''
START S0
END [S0, S1,]
S0 {
    IF T.0 == "1" THEN {
      GOTO S0 {
        T.0: ["0", MOV_L]
      }
    }
    ELSE {
      GOTO S1 {
        T.0: ["0", MOV_L]
      }
    }
}
S1 {
    IF T.0 == "1" THEN {
      GOTO S0 {
        T.0: ["0", MOV_L]
      }
    }
    ELSE {
      GOTO S1 {
        T.0: ["0", MOV_L]
      }
    }
}
'''

    tokenizer_result = __tokenize_program_section__(TokenizerSection(name="program", content=list(map(lambda enum_line: SectionLine(no=enum_line[0], value=enum_line[1]), enumerate(program.split("\n"))))))

    assert tokenizer_result is not None

    result = parse_program(tokenizer_result, 1, ["0", "1"])

    assert result is not None
    assert result.check_syntax()
    assert 2 == len(result.end_nodes)
    assert "s0" in result.end_nodes
    assert "s1" in result.end_nodes

def test_if_conditions_grouping():
    program = r'''
IF (T.0== "1"||T.0=="0")&&T.1=="3"||T.2!=T.1
    '''

    tokenizer_result = __tokenize_program_section__(TokenizerSection(name="program", content=list(map(lambda enum_line: SectionLine(no=enum_line[0], value=enum_line[1]), enumerate(program.split("\n"))))))

    assert tokenizer_result is not None
    assert 18 == len(tokenizer_result.tokens)
    tokens = tokenizer_result.tokens
    assert Token.IF == tokens[0].token
    assert Token.GROUP_START == tokens[1].token
    assert Token.VAR == tokens[2].token
    assert Token.EQUAL == tokens[3].token
    assert Token.CONST == tokens[4].token
    assert Token.OR == tokens[5].token
    assert Token.VAR == tokens[6].token
    assert Token.EQUAL == tokens[7].token
    assert Token.CONST == tokens[8].token
    assert Token.GROUP_END == tokens[9].token
    assert Token.AND == tokens[10].token
    assert Token.VAR == tokens[11].token
    assert Token.EQUAL == tokens[12].token
    assert Token.CONST == tokens[13].token
    assert Token.OR == tokens[14].token
    assert Token.VAR == tokens[15].token
    assert Token.NOT_EQUAL == tokens[16].token
    assert Token.VAR == tokens[17].token

