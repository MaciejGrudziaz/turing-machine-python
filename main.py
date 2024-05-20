from argparse import ArgumentParser

if __name__ != "__main__":
    exit(1)

parser = ArgumentParser(description="Turing machine for the course: Podstawy Algorytmiki, Warsaw University of Technology, Faculty of Electrical Engineering")
parser.add_argument("--input", type=str, help="Turing machine specification in text format")
parser.add_argument("--file", type=str, help="configuration file with the Turing machine specification")

args = parser.parse_args()

if args.input is None and args.file is None:
    print("No Turing machine config specified.\nUse option -h[--help] to check all the available options.")



