import json

from model import Process, Application

class Interpreter:
    def __init__(self, commands_description_path="restorerv2/commands_description.json"):
        with open(commands_description_path, "r") as commands_file:
            self.commands = json.load(commands_file)

    def execute_program(self, program_path):
        result = self._load_program(program_path)
        program = result["program"]
        errors = result["errors"]
        if errors:
            print("\n".join(errors))
            return None
        self.app = Application()
        for statement in program:
            self._execute_statement(statement)
        return self.app

    def _fork(self, pid, child_pid, **extras):
        self.app.fork(pid, child_pid)

    def _clone(self, pid, child_pid, **extras):
        self.app.clone(pid, child_pid)

    def _set_child_reaper(self, pid, value, **extras):
        self.app.set_child_reaper(pid, value)

    def _set_sid(self, pid, **extras):
        self.app.set_sid(pid)

    def _exit(self, pid, **extras):
        self.app.exit(pid)

    def _wait(self, pid, child_pid, **extras):
        self.app.wait(pid, child_pid)

    def _open(self, pid, path, fd, **extras) :
        self.app.open(pid, path, fd)

    def _close(self, pid, fd, **extras):
        pass

    def _dup2(self, pid, old_fd, new_fd, **extras):
        pass

    def _lseek(self, pid, fd_offset, **extras):
        pass

    def _transfer_fd(self, from_pid, to_pid, fd, target_fd, **extras):
        pass

    def _execute_statement(self, statement):
        pstree_commands = {
                "FORK"             : self._fork,
                "CLONE"            : self._clone,
                "SET_CHILD_REAPER" : self._set_child_reaper,
                "SET_SID"          : self._set_sid,
                "EXIT"             : self._exit,
                "WAIT"             : self._wait
                }
        files_commands = {
                "OPEN"             : self._open,
                "CLOSE"            : self._close,
                "DUP2"             : self._dup2,
                "LSEEK"            : self._lseek,
                "TRANSFER_FD"      : self._transfer_fd
                }
        commands = {}
        commands.update(pstree_commands)
        commands.update(files_commands)
        return commands[statement["command"]](**statement)

    def _check_args(self, statement, required_args):
        keys = statement.keys()
        errors = []
        for arg in required_args:
            if not arg in keys:
                errors.append("In {} required {} field.".format(statement["command"], arg))
        return errors

    def _verify_statement(self, statement):
        try:
            command_name = statement["command"]
        except KeyError:
            return ['Field "command" not found.']
        try:
            command_description = next((c for c in self.commands if c["name"] == command_name))
            return self._check_args(statement, command_description["args"])
        except StopIteration:
            return ['Command "{}" unrecognized.'.format(command_name)]

    def _verify_program(self, program):
        errors = []
        for (num, statement) in enumerate(program):
            stat_errors = self._verify_statement(statement)
            if stat_errors:
                errors.append("In {} statement:".format(num))
                for stat_error in stat_errors:
                    errors.append("    {}".format(stat_error))
        return errors

    def _load_program(self, program_path):
        try:
            with open(program_path, "r") as program_file:
                program = json.load(program_file)
        except ValueError as exception:
            return {"program": None, "errors": [str(exception)]}
        errors = self._verify_program(program)
        return {"program": program, "errors": errors}
