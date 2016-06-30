import os
import copy
import json
from collections import defaultdict

import pycriu


class TaskState:
    alive  = 1
    dead   = 2
    stoped = 3
    helper = 4


class Process:
    def __init__(self, pid, ppid, sid, is_zombie=False, is_child_reaper=False):
        self.pid = pid
        self.ppid = ppid
        self.sid = sid
        self.is_zombie = is_zombie
        self.is_child_reaper = is_child_reaper
        self.fd_table = {}

    def __repr__(self):
        return ("Process(pid: {pid},\n"
                "        ppid: {ppid},\n"
                "        sid: {sid},\n"
                "        is_zombie: {is_zombie},\n"
                "        fd_table: {fd_table})").format(**self.__dict__)
    
    def __eq__(self, other):
        ignored = ["is_child_reaper", # FIXME where is placed this field in images?
                   "fd_table"] 
        d1 = self.__dict__
        d2 = other.__dict__
        for k1, v1 in d1.iteritems():
            if not k1 in ignored and (k1 not in d2 or d2[k1] != v1):
                return False
        for k2, v2 in d2.iteritems():
            if not k2 in ignored and k2 not in d1:
                return False
        return True
        
    def set_child_reaper(self, value):
        self.is_child_reaper = value

    def set_sid(self):
        self.sid = self.pid

    def exit(self):
        self.is_zombie = True

    def reparent(self, new_ppid):
        self.ppid = new_ppid

    def fork(self, child_pid):
        p = Process(child_pid, self.pid, self.sid)
        p.fd_table = copy.copy(self.fd_table)
        return p

    def get_fd_by_ifd(self, ifd):
        for k, v in self.fd_table.items():
            if v == ifd:
                return k
        return None

    def add_fd(self, fd, ifd):
        if fd in self.fd_table:
            raise ValueError("fd: {} is alredy presented in {}".
                    format(fd, self.pid))
        self.fd_table[fd] = ifd


class RegFile:
    def __init__(self, path, pos=0, size=0):
        # RegFile._check_pos(pos, size)
        self.size = size
        self.pos = pos
        self.path = path

    def __repr__(self):
        return "RegFile(path: {path}, pos: {pos}, size:{size})".format(**self.__dict__)

    @staticmethod
    def _check_pos(pos, size):
        if pos < 0 or pos > size:
            raise ValueError("Incorrect position: {} in regular file with size: {}"
                    .format(pos, size))

    def lseek(self, new_pos):
        # RegFile._check_pos(new_pos, size)
        self.pos = new_pos

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __hash__(self):
        return hash((self.path, self.pos))


class Application:
    def __init__(self):
        self.processes = [Process(0, 0, 0, is_child_reaper=True)]
        self.reg_files = {}

    def __repr__(self):
        result = "Application(\n"
        result += "Processes:\n"
        for process in self.processes:
            result += "    {}\n".format(process)
        result += "Files:\n"
        for ifd, rf in self.reg_files.items():
            result += "    {}: {}\n".format(ifd, rf)
        result += ")"
        return result

    def _find_by_pid(self, pid):
        try:
            return next(p for p in self.processes if p.pid == pid)
        except StopIteration:
            raise ValueError("Process with pid: {} does not exist.".format(pid))

    def _del_process(self, p):
        self.processes.remove(p)
            
    def fork(self, pid, child_pid):
        parent = self._find_by_pid(pid)
        self.processes.append(parent.fork(child_pid))

    def clone(self, pid, child_pid):
        sib = self._find_by_pid(pid)
        parent = self._find_by_pid(sib.ppid)
        self.processes.append(parent.fork(child_pid))

    def set_child_reaper(self, pid, value):
        p = self._find_by_pid(pid)
        p.set_child_reaper(value)

    def set_sid(self, pid):
        p = self._find_by_pid(pid)
        p.set_sid()

    def _get_chidlren(self, ppid):
        return [p for p in self.processes if p.ppid == ppid]

    def _find_child_reaper(self, pid):
        ppid = pid
        while True:
            ppid = self._find_by_pid(ppid).ppid
            parent = self._find_by_pid(ppid)
            if parent.is_child_reaper:
                return parent

    def exit(self, pid):
        p = self._find_by_pid(pid)
        children = self._get_chidlren(pid)
        child_reaper = self._find_child_reaper(pid)
        for child in children:
            child.reparent(child_reaper.pid)
        p.exit()

    def wait(self, pid, child_pid):
        p = self._find_by_pid(child_pid)
        if p.ppid != pid:
            raise ValueError("Process with pid: {} is not children of: {}"
                    .format(child_pid, pid))
        self._del_process(p)

    def open(self, pid, path, fd):
        p = self._find_by_pid(pid)
        new_file = RegFile(path)
        ifd = len(self.reg_files)
        self.reg_files[ifd] = new_file
        p.add_fd(fd, ifd)

    def close(self, pid, fd):
        p = self._find_by_pid(pid)
        ifd = p.fd_table.pop(fd, None)
        holders = self._get_file_holders_by_ifd(ifd)
        if not holders:
            self.reg_files.pop(ifd, None)

    def dup2(self, pid, old_fd, new_fd):
        p = self._find_by_pid(pid)
        p.fd_table[new_fd] = p.fd_table[old_fd]

    def lseek(self, pid, fd, pos):
        p = self._find_by_pid(pid)
        ifd = p.fd_table[fd]
        self.reg_files[ifd].lseek(pos)

    def transfer_fd(self, from_pid, to_pid, fd, target_fd):
        source = self._find_by_pid(from_pid)
        target = self._find_by_pid(to_pid)
        target.fd_table[target_fd] = source.fd_table[fd]

    def _get_file_holders_by_ifd(self, ifd):
        holders = []
        for p in self.processes:
            fd = p.get_fd_by_ifd(ifd)
            if fd:
                holders.append((p.pid, fd))
        return tuple(holders)

    def _get_file_holders_by_file_mapping(self):
        holders = defaultdict(set)
        for ifd, f in self.reg_files.items():
            holders[f].add(self._get_file_holders_by_ifd(ifd))
        return holders

    def _compare_opened_files(self, other):
        self_holders = self._get_file_holders_by_file_mapping()
        other_holders = other._get_file_holders_by_file_mapping()
        return self_holders == other_holders

    def _compare_pstree(self, other):
        ordered = lambda p: sorted(p, key=lambda s: s.pid)
        return ordered(self.processes) == ordered(other.processes)

    def __eq__(self, other):
        return self._compare_opened_files(other) and \
                self._compare_pstree(other)

    @staticmethod
    def load(source_path, item_type):
        pstree_item = load_item(source_path, "pstree", item_type)
        app = Application()
        
        reg_files = load_item(source_path, "reg-files", item_type)
        for entry in reg_files["entries"]:
            app.reg_files[entry["id"]] = RegFile(entry["name"], entry["pos"])

        for entry in pstree_item["entries"]:
            core_item = load_item(source_path, "core-{}".format(entry["pid"]), item_type)
            task_state = core_item["entries"][0]["tc"]["task_state"]
            if task_state in (TaskState.stoped, TaskState.helper):
                print("Unexpected task state for {}".format(extry["pid"]))
            process = Process(
                    pid = entry["pid"],
                    ppid = entry["ppid"],
                    sid = entry["sid"],
                    is_zombie = task_state is TaskState.dead)
            ids_item = load_item(source_path, "ids-{}".format(entry["pid"]),
                    item_type)
            files_id = ids_item["entries"][0]["files_id"]
            fd_info = load_item(source_path, "fdinfo-{}".format(files_id), item_type)
            for entry in fd_info["entries"]:
                process.fd_table[entry["fd"]] = entry["id"]
            app.processes.append(process)
        return app

    @staticmethod
    def load_from_imgs(imgs_path):
        return Application.load(imgs_path, "img")

    @staticmethod
    def load_from_jsons(jsons_path):
        return Application.load(jsons_path, "json")


class Vma:
    def __init__(self, start, end, is_private, is_named):
        self.start = start
        self.end = end
        self.is_private = is_private
        self.is_named = is_named


def load_img(imgs_folder, img_name):
    img_path = os.path.join(imgs_folder, img_name)
    with open(img_path, "r") as f:
        try:
            return pycriu.images.load(f, True)
        except pycriu.images.MagicException as exc:
            print("Incorrect magic in {}".format(img_path))
            return None


def load_item(source_path, item_name, item_type):
        if item_type == "json":
            item_path = os.path.join(source_path, "{}.json".format(item_name))
            with open(item_path, "r") as f:
                return json.load(f)
        elif item_type == "img":
            return load_img(source_path, "{}.img".format(item_name))
        raise ValueError("Unknown item_type: {}".format(item_type))
