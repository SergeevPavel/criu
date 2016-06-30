
from copy import copy
import random

import restorerv2.nodes as nodes

class MockExecutor():
    def __init__(self):
        self.app = nodes.Application()

    def fork(self, pid, child_pid):
        parent = self.app.find_process_by_pid(pid)
        descriptors = parent.descriptors
        p = nodes.Process(child_pid, pid)
        for d in descriptors:
            p.add_file_descriptor(nodes.FileDescriptor(d.fd, d.struct_file))
        for vma in vmas:
            p.add_vma(nodes.Vma(vma.start,
                                vma.end,
                                vma.file_path,
                                vma.pgoff,
                                vma.is_shared))
        self.app.add_process(p)

    def open(self, pid, path, fd):
        file_path = self.app.get_file_path(path)
        if not file_path:
            file_path = nodes.FilePath(path)
        rf = nodes.RegularFile(file_path=file_path, size=None, pos=0)
        descriptor = nodes.FileDescriptor(fd, rf)
        p = self.app.find_process_by_pid(pid)
        p.add_file_descriptor(descriptor)

    def close(self, pid, fd):
        p = self.app.find_process_by_pid(pid)
        descriptor = p.get_file_descriptor(fd)
        p.remove_file_descriptor(descriptor)

    def dup2(self, pid, old_fd, new_fd):
        p = self.app.find_process_by_pid(pid)
        descriptor = p.get_file_descriptor(old_fd)
        new_descriptor = copy(descriptor)
        new_descriptor.fd = new_fd
        p.add_file_descriptor(new_descriptor)

    def lseek(self, pid, fd, offset):
        p = self.app.find_process_by_pid(pid)
        descriptor = p.get_file_descriptor(fd)
        descriptor.struct_file.pos = offset

    def transfer_fd(self, from_pid, to_pid, fd, target_fd):
        p = self.app.find_process_by_pid(from_pid)
        descriptor = p.get_file_descriptor(fd)
        target_process = self.app.find_process_by_pid(to_pid)
        target_descriptor = nodes.FileDescriptor(target_fd, descriptor.struct_file)
        target_process.add_file_descriptor(target_descriptor)

    def mmap(self, pid, addr, length, fd, offset, is_shared):
        p = self.app.find_process_by_pid(pid)
        descriptor = p.get_file_descriptor(fd)
        file_path = descriptor.struct_file.file_path
        vma = nodes.Vma(start=addr,
                        end=addr + length,
                        file_path=file_path,
                        pgoff=offset,
                        is_shared=is_shared)
        p.add_vma(vma)

    def mmap_anon(self, pid, addr, length, is_shared):
        p = self.app.find_process_by_pid(pid)
        if is_shared:
            file_path = nodes.FilePath("/tmp/{}".format(random.randint(1000, 10000)))
        else:
            file_path = None
        vma = nodes.Vma(start=addr,
                        end=addr + length,
                        file_path=path_path,
                        is_shared=is_shared)
        p.add_vma(vma)

    def mremap(self, pid, addr, new_addr):
        p = self.app.find_process_by_pid(pid)
        vma = p.get_vma(addr)
        length = vma.end - vma.start
        vma.start = addr
        vma.end = vma.start + length

    def munmap(self, pid, addr):
        p = self.app.find_process_by_pid(pid)
        vma = p.get_vma(addr)
        p.remove_vma(vma)

    def get_application(self):
        return self.app

