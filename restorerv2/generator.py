#!/usr/bin/env python

import argparse
import sys
import os

import pycriu

class ApplicationModel:
    def __init__(self, images_folder):
        self.images_folder = os.path.abspath(images_folder)
        pstree_data = self._load_image_data(self.images_folder, "pstree.img")
        pstree_entry = pstree_data["entries"][0]
        self.pid = pstree_entry["pid"]
        self.pgid = pstree_entry["pgid"]
        self.sid = pstree_entry["sid"]

        fdinfo_data = self._load_image_data(self.images_folder, "fdinfo-2.img")
        self.fds = fdinfo_data["entries"]

        reg_files_data = self._load_image_data(self.images_folder, "reg-files.img")
        self.reg_files = reg_files_data["entries"]


    def write_restorer_program(self, output):
        output.write("images_folder={}\n".format(self.images_folder))
        output.write("create_process(pid={},pgid={},sid={})\n".\
                format(self.pid, self.pgid, self.sid))
        output.write("init_core()\n")
        output.write("init_memory()\n")
        self._write_open_file_commands(output)


    def _write_open_file_commands(self, output):
        for fd_entry in self.fds:
            reg_file = filter(lambda rf: rf["id"] == fd_entry["id"], self.reg_files)[0]
            fd = fd_entry["fd"]
            flags = fd_entry["flags"]
            pos = reg_file["pos"]
            name = reg_file["name"]
            size = reg_file["size"]
            output.write("open_reg_file(fd={},flags={},pos={},name={},size={})\n".\
                    format(fd, flags, pos, name, size))


    def _load_image_data(self, images_folder, image_name):
        image_path = os.path.join(images_folder, image_name)
        with open(image_path, "r") as f:
            try:
                return pycriu.images.load(f, True)
            except pycriu.images.MagicException as exc:
                print >>sys.stderr, "Unknown magic %#x.\n"\
                        "Maybe you are feeding me an image with "\
                        "raw data(i.e. pages.img)?" % exc.magic
                return None # TODO fix error handling


def main():
    parser = argparse.ArgumentParser(description="Restore instructions generator")
    parser.add_argument("--images", help="images folder", default=".")
    parser.add_argument("--output", help="output file",
            type=argparse.FileType("w"), default=sys.stdout)
    args = parser.parse_args()
    opts = vars(args)
    model = ApplicationModel(opts["images"])
    model.write_restorer_program(opts["output"])


if __name__ == "__main__":
    main()
