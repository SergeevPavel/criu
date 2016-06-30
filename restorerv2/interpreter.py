import json

from model import Process, Application

class Interpreter:
    def __init__(self, executor,
            commands_description_path="restorerv2/commands_description.json"):
        self.executor = executor
        with open(commands_description_path, "r") as commands_file:
            self.commands = json.load(commands_file)

    def execute_program(self, program_path):
        result = self._load_program(program_path)
        program = result["program"]
        errors = result["errors"]
        if errors:
            print("\n".join(errors))
            return None
        for statement in program:
            self._execute_statement(statement)

    def _fork(self, pid, child_pid, **extras):
        self.executor.fork(pid, child_pid)

    def _clone(self, pid, child_pid, **extras):
        raise NotImplementedError()

    def _set_child_reaper(self, pid, value, **extras):
        raise NotImplementedError()

    def _set_sid(self, pid, **extras):
        raise NotImplementedError()

    def _exit(self, pid, **extras):
        raise NotImplementedError()

    def _wait(self, pid, child_pid, **extras):
        raise NotImplementedError()

    def _open(self, pid, path, fd, **extras) :
        self.executor.open(pid, path, fd)

    def _close(self, pid, fd, **extras):
        self.executor.close(pid, fd)

    def _dup2(self, pid, old_fd, new_fd, **extras):
        self.executor.dup2(pid, old_fd, new_fd)

    def _lseek(self, pid, fd, offset, **extras):
        self.executor.lseek(pid, fd, offset)

    def _transfer_fd(self, from_pid, to_pid, fd, target_fd, **extras):
        self.executor.transfer_fd(from_pid, to_pid, fd, target_fd)

    def _mmap(self, pid, addr, length, fd, offset, is_shared, **extras):
        self.executor.mmap(pid, addr, length, fd, offset, is_shared)

    def _mmap_anon(self, pid, addr, length, is_shared, **extras):
        self.executor.mmap_anon(pid, addr, length, is_shared)

    def _mremap(self, pid, addr, new_addr, **extras):
        self.executor.mremap(pid, addr, new_addr)

    def _munmap(self, pid, addr, **extras):
        self.executor.munmap(pid, addr)

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
        memory_commands = {
                "MMAP"             : self._mmap,
                "MMAP_ANON"        : self._mmap_anon,
                "MREMAP"           : self._mremap,
                "MUNMAP"           : self._munmap
                }
        commands = {}
        commands.update(pstree_commands)
        commands.update(files_commands)
        commands.update(memory_commands)
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
