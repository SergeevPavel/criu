
import os

from restorerv2.loader import load_from_jsons
from restorerv2.executors import MockExecutor
from restorerv2.interpreter import Interpreter
from restorerv2.generator import ProgramBuilder
from restorerv2.utils import ApplicationComparator, ApplicationView

TESTS_LIST = [
#        "fds1",
#        "fds2"
#        "counter",
#        "forks"
        ]

ROOT_TESTS_PATH = "restorerv2/tests"

def run_test(test_name):
    print("Test: {}".format(test_name))
    test_path = os.path.join(ROOT_TESTS_PATH, test_name)
    dump_path = os.path.join(test_path, "dump")
    program_path = os.path.join(test_path, "program.json")
    dumped_app = load_from_jsons(dump_path)
    
    program_builder = ProgramBuilder()
    program_builder.write_program(dumped_app, program_path)

    executor = MockExecutor()
    interpreter = Interpreter(executor)
    interpreter.execute_program(program_path)
    restored_app = executor.get_application()
    if ApplicationComparator(dumped_app, restored_app).is_equals():
        print("OK!")
    else:
        print("Failed!")
        print("Dumped:")
        print(ApplicationView(dumped_app).text())
        print("Restored:")
        print(ApplicationView(restored_app).text())


def main():
    for test in TESTS_LIST:
        run_test(test)
    

if __name__ == "__main__":
    main()
