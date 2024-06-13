# Turing machine

## Running application

To run the application: `python main.py --file config.toml`.

To run in debug mode: `python main.py --file config.toml --debug 0`.

Available debug modes are `0` and `1`. Mode `1` offers more verbose messages about currently running state.

To get all of the available options: `python main.py -h`.

To run tests: `pytest test` (`pytest` package is required).

## Description

This application is a Turing machine 'interpreter'. It can execute programs defined in it's own simple language
(syntax similar to C), on the Turing machine model, implemented in the application.

Application can be split into 3 parts:
1. Compiler - defined in `src/compiler`, it reads the file (or text) specified on the input, tokenizes and parses it,
   and at the end it creates the state tree, representing all of the Turing machine states, with the transition conditions
   and tape operations;
2. Turing machine runtime - defined in `src/turing_machine`, is used as the runtime for the output of the 'compiler' described above
3. Turing machine code - it can be defined in the file and passed to the application as the `--file` option, or it can be passed as 
   the inline text as the `--input` option

## Configuration file description

The configuration file must define two sections: `[tape]` and `[program]`.

All the lines starting with the `#` character are considered as the comment, and are ignored during file parsing (both in `tape` and `program` sections).

### Tape section

Tape section must be defined before the `[program]` section.

In this section, each variable must be defined in the single line!

#### Variables:
#### `alphabet`
defines the alphabet that will be used by the Turing machine; it must be defined as the list of values (can be one or more characters long)
separated by the comma (','). The list must begin with the `[` character and end with `]`. All the values in the list are considered as a string 
inside the Turing machine.

The values in the alphabet list can de defined one by one, or by using ranges. The range can only be define on the single character values,
that are organized in alphabetical or numerical order. For example, the range `a-z` defines all the small case letters, from `a` to `z` (including). 
The same can be done for numbers, for example the range `0-9` defines all the numbers from `0` to `9`. The ranges can be defined multiple times inside 
the alphabet list, for example: `alphabet = [a-z, 0-9]`.

#### `T.<n>`
defines the nth tape for the Turing machine. The tape must be defined in this format (the unique tape names are not supported at the moment), where the `n`
value represents the tape id. The tapes can de defined in any order, but there cannot be any break, between two consecutive ids and the id of the first tape must be `0`.
This means that if the user defines the tape `T.4`, he has also define the tapes with id 0, 1, 2 and 3.

The tape is defined the same way as the alphabet (tape definitions don't support ranges!), it is a list of comma separated values. All the values used in the tape 
must be defined in the alphabet first.

#### Example
Example of the `[tape]` section definition:
```
[tape]
alphabet = [a-z, A-Z, 0-9, _, ^, $]
T.0 = [^, a, b, c, _, t, e, t, e, s, _, d, a, l, s, z, y, _, t, e, k, s, t, _, t, e, s, t, _, p, r, z, y, k, l, a, d, $]
T.1 = [^, t, e, s, t, $]
T.2 = [^, 0, 0, 0, $]
```

### Program section

After the `[program]` section header (starting with the following line), all of the text is considered as the source code for the Turing machine defined in the custom language (not yet named, 
let's call it `Turing lang`, for the remainder of this instruction). The description of the `Turing lang` is defined further in the instruction.

## Turing lang

`Turing lang` is a simple, C-like language, describing the states of the Turing machine and conditional transitions between them. It's case insensitive and 
has only one data type, string.

### START

```
START <state>
```

Declares the `state` which will be used as the first state in the Turing machine runtime. It must be defined as the first statement in the program code!

Example:
```
START machine_begin
```

### END

```
END [<state 1>, <state 2>, ...]
```

Declares the list of states that will be used as the finishing states in the Turing machine runtime (if the machine transitions to the any of these states it will end the execution).
The `END` statement must be defined right after the `START` statement.

Example:
```
END [machine_end, machine_error]
```

### State definition

```
<state_name> {
    ...
}

```

States can be defined in any order. The state name can consist of any character except whitespaces. The name cannot be any of the special values used by the language itself.
The state body is defined inside the curly braces `{..}`. Inside the state, only two types of the operations are accepted. `IF` statements and `GOTO` command (both are further 
described below). The states that are declared in the `END` statement, can have empty body.

Example:
```
check_if_zero {
    IF(T.0 == "0") THEN {
        GOTO is_zero {
            T.0: ["1", MOV_R],
        }
    } ELSE {
        GOTO check_if_zero {
            T.0: [T.0, STAY],
        }
    }
}
```

### GOTO

```
GOTO <state> {
    T.<tape_id>: [<value>, <move>],
    ...
}
```

`GOTO` command defines the transition from the state where it is defined to the `<state>` declared in the statement. The body of the `GOTO` command is defined inside the curly 
braces `{..}`. In the body, is a comma separated list of operations to perform for each tape. For each tape, there can be only one operation. The operation defines, what value 
will be written to the tape after transition to the new state, and how the head will move on the tape.

The `value` in the operation, can be either a constant string value defined between the double quotes `".."` or a tape name (`T.<n>`). If the `value` is a const, 
it has to be a valid value from the `alphabet`. If the `value` is a tape name, the current value from the declared tape will be written on the current position of the target tape.

The `move` can be one of the three values: `MOV_R`, `MOV_L` and `STAY`. `MOV_R` moves the tape head one position to the right. Analogically, `MOV_L` moves the head one position 
to the left. `STAY` means that the tape head will stay at the current position.

If for the tape, there is no operation defined, it will execute the default operation: `T.<i> = [T.i, STAY]`. This operation doesn't move the tape head from the current position 
and it doesn't change the current value on the tape.

Example:
```
GOTO new_state {
    T.0: ["0", MOV_L],
    T.1: [T.0, MOV_R],
    T.2: [T.2, STAY],
}
```

### IF

```
IF (<condition>) THEN { ... }
[ELIF (<condition>) THEN { ... }]
ELSE { ... }
```

The `IF` statement checks the `condition` and if the result is a boolean `true` value, the program executes the code inside the statement body. If the condition result is `false` 
it goes to the next `ELIF` or `ELSE` statement. Each `IF` statement must end with the `ELSE` statement, which catches all conditions that don't match any of the preceding 
`IF` and `ELIF` statements. `ELIF` statement is optional, and can be defined multiple times for the single `IF` statement.

In the body of the `IF` statement can be declared either another `IF` statement or a `GOTO` statement. Each `IF` branch, has to, in the end, execute the `GOTO` command. 
This, in combination with the requirement of the `ELSE` statement, fulfills the requirement, that each state of the Turing machine tapes will be handled.

#### condition

The condition has to be defined inside the parenthesis `(...)` and must be followed by the `THEN` statement.

Condition is a sequence of the boolean operations, joined with the one of the two boolean operators `||`, which is a boolean OR and `&&`, which is a boolean AND. 
The sequence of the boolean operations depends on the operators. The priority have the AND operator, which will be executed in order, from left to right.

The boolean operations can be grouped with the parenthesis `(...)`. The operation inside the parenthesis has the priority before any other comparison operation.

Comparison operation has to be define in the following way:
```
T.<n> <op> <value>
```
where:
* `T.<n>` is a tape id, which represents the current value of the specified tape
* `op` is a comparison operator, either `==` which check if the value on the tape is equal to the `value` or `!=` which checks for the opposite condition
* `value` can be either a const value from the alphabet or a tape id (the same way as in `GOTO` command)

Example:
```
IF (T.0 != T.1) THEN { ... }
ELIF (T.0 == "0") THEN { ... }
ELSE { ... }
```

## Runtime

The Turing machine runtime, executes the program defined in the configuration file, starting with the state declared in the `START` statement. The head of each of the tapes
starts at position 0 (the first value on the tape).

When the machine transitions to any of the states declared in the `END` statement, it finishes the execution. The result of the program is both the last state of the machine 
and the state of the tapes.

By default, the program is run automatically and it only outputs the final result. If you want to run the program step by step, launch the application with the `--debug` flag.

The working example is defined in the `config.toml` file (the file extensions has no meaning in the context of the machine, it's only defined this way to work with the default 
`toml` linter in code editor). It's an algorithm for checking for the pattern in the text. The input text is defined on tape `T.0`, the pattern is on tape `T.1` and on tape `T.2` 
will be index, where in the input text the pattern begins, if the final state is `ok_found`. The resulting state are:
* `ok_found` - the pattern was found in the input text
* `ok_not_found` - the pattern was not found
* `err_index_overflow` - the index value on tape `T.2` reached over the maximum value (999)
* `err_index_unexpected_value` - found unexpected value on the index tape `T.2` (only accepted values are `^`, `0-9` and `$`)
* `err_format_tape_<n>` - error in the definition of the nth tape

Each tape must start with the `^` token and end with `$` token. In the context of the index, the character `^` on the beginning of the input text tape is not considered 
as a text character (it doesn't count into the length of the text).
