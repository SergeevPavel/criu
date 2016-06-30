

class Application(object):
    def __init__(self):
        self.root_process = Process()
        self.processes = {self.root_process}

    def get_root_process(self):
        return self.root_process

    def add_process(self, process):
        self.processes.add(process)

    def _collect_regular_files(self):
        result = set()
        for p in self.processes:
            for d in p.descriptors:
                result.add(d.struct_file)
        return result

    def get_regular_files(self):
        regular_files = self._collect_regular_files()
        key = lambda rf: (rf.file_path.path, rf.size)
        return sorted(regular_files, key=key)

    def _collect_file_paths(self):
        result = {}
        for p in self.processes:
            for d in p.descriptors:
                result.add(d.struct_file.file_path)
            for vma in p.vmas:
                result.add(vma.file_path)
        return result

    def get_file_paths(self):
        file_paths = self._collect_file_paths()
        key = lambda fp: fp.path
        return sorted(file_paths, key=key)

    def get_file_path(self, path):
        try:
            return next(fp for fp in self._collect_file_paths() if fp.path == path)
        except:
            return None

    def get_children(self, process):
        children = [p for p in self.processes if p.ppid == process.pid]
        return sorted(children, key=lambda ch: ch.pid)

    def get_regular_files_by_process(self, process):
        key = lambda rf: (rf.path, rf.size)
        files = (d.struct_file for d in process.descriptors)
        return sorted(files, key=key)

    def find_process_by_pid(self, pid):
        try:
            return next(p for p in self.processes if p.pid == pid)
        except StopIteration:
            raise ValueError("Process with pid: {} does not exist.".format(pid))


class Process(object):
    def __init__(self, pid=0, ppid=-1):
        self._pid = pid
        self._ppid = ppid
        self._descriptors = set()
        self._vmas = set()

    @property
    def pid(self):
        return self._pid

    @pid.setter
    def pid(self, pid):
        self._pid = pid

    @property
    def ppid(self):
        return self._ppid

    @ppid.setter
    def ppid(self, ppid):
        self._ppid = ppid

    def add_file_descriptor(self, descriptor):
        self._descriptors.add(descriptor)

    def remove_file_descriptor(self, descriptor):
        self._descriptors.remove(descriptor)

    def add_vma(self, vma):
        self._vmas.add(vma)

    def remove_vma(self, vma):
        self._vmas.remove(vma)
    
    def get_file_descriptor(self, fd):
        try:
            return next(d for d in self._descriptors if d.fd == fd)
        except StopIteration:
            return None

    def get_vma(self, start):
        try:
            return next(vma for vma in self._vmas if vma.start == start)
        except StopIteration:
            return None

    @property
    def descriptors(self):
        return self._descriptors

    @property
    def vmas(self):
        return self._vmas

    @descriptors.setter
    def descriptors(self, descriptors):
        self._descriptors = descriptors

    def __str__(self):
        return "Process(pid: {_pid}, ppid: {_ppid})".format(**self.__dict__)

    def __repr__(self):
        return self.__str__()


class FileDescriptor(object):
    def __init__(self, fd, struct_file):
        self._fd = fd
        self._struct_file = struct_file

    @property
    def fd(self):
        return self._fd

    @fd.setter
    def fd(self, fd):
        self._fd = fd

    @property
    def struct_file(self):
        return self._struct_file

    @struct_file.setter
    def struct_file(self, struct_file):
        self._struct_file = struct_file


class RegularFile(object):
    def __init__(self, file_path, size, pos):
        self._file_path = file_path
        self._size = size
        self._pos = pos

    @property
    def file_path(self):
        return self._file_path

    @file_path.setter
    def file_path(self, file_path):
        self._file_path = file_path

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, size):
        self._size = size

    @property
    def pos(self):
        return self._pos

    @pos.setter
    def pos(self, pos):
        if self._size and pos > self._size:
            raise ValueError("Pos should be less than size")
        self._pos = pos


class Vma:
    def __init__(self,
            start=0,
            end=0,
            file_path=None,
            pgoff=None,
            is_shared=False):
        self._start = start
        self._end = end
        self._file_path = file_path
        self._pgoff = pgoff
        self._is_shared = is_shared

    @property
    def start(self):
        return self._start

    @start.setter
    def start(self, start):
        self._start = start

    @property
    def end(self):
        return self._end

    @end.setter
    def end(self, end):
        self._end = end

    @property
    def file_path(self):
        return self._file_path

    @file_path.setter
    def file_path(self, file_path):
        self._file_path = file_path

    @property
    def pgoff(self):
        return self._pgoff

    @pgoff.setter
    def pgoff(self, pgoff):
        self._pgoff = pgoff

    @property
    def is_shared(self):
        return self._is_shared

    @is_shared.setter
    def is_shared(self, is_shared):
        self._is_shared = is_shared


class FilePath:
    def __init__(self, path):
        self._path = path

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, path):
        self._path = path
