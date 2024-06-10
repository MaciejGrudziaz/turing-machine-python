from argparse import ArgumentParser
from src.config.config import load_from_file, load_from_string
from src.turing_machine.ast_turing_machine import ASTTuringMachine

if __name__ != "__main__":
    exit(1)

parser = ArgumentParser(description="Turing machine created as an exercise for the course 'Podstawy Algorytmiki' at Warsaw University of Technology, Faculty of Electrical Engineering")
parser.add_argument("--input", type=str, help="Turing machine specification in text format")
parser.add_argument("--file", type=str, help="configuration file with the Turing machine specification")
parser.add_argument("--debug", type=int, help="run in debug mode [DEBUG represents the debug level; available options: 0, 1 (default: 0)]")

args = parser.parse_args()

if args.input is None and args.file is None:
    print("No Turing machine config specified.\nUse option -h[--help] to check all the available options.")
    exit(1)

config = None
if args.file is not None:
    config = load_from_file(args.file)
else:
    config = load_from_string(args.input)

if config is None:
    print("Failed to load config")
    exit(1)

machine = ASTTuringMachine(config, args.debug is not None and args.debug == 1)

print("Machine initial state:")
machine.print_status()

try:
    if args.debug is not None:
        if args.debug not in [0, 1]:
            print(f"Unexpected debug value {args.debug}. Available options are: 0, 1")
            exit(1)
        machine.run_tick()
    else:
        machine.run_auto()
except Exception as e:
    print(f"Error occurred during machine runtime: {e}")
    exit(2)

print("--------------------------------------------------------------------------------")
print("Machine finished! Final state:")
machine.print_status()

