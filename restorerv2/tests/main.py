
import os

from restorerv2.model import Application
from restorerv2.interpreter import Interpreter

TESTS_LIST = [
        "fds"
#       "counter",
#       "forks"
        ]

ROOT_TESTS_PATH = "restorerv2/tests"

def run_test(test_name):
    print("Test: {}".format(test_name))
    test_path = os.path.join(ROOT_TESTS_PATH, test_name)
    dump_path = os.path.join(test_path, "dump")
    program_path = os.path.join(test_path, "program.json")
    
    dumped_app = Application.load_from_jsons(dump_path)
    interpreter = Interpreter()
    restored_app = interpreter.execute_program(program_path)
    if dumped_app == restored_app:
        print("OK!")
    else:
        print("Failed!")
        print("Dumped:")
        print(dumped_app)
        print("Restored:")
        print(restored_app)


def main():
    for test in TESTS_LIST:
        run_test(test)
    

if __name__ == "__main__":
    main()
