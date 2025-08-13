#!/usr/bin/env python
import os
import select
import threading
from dbus import SystemBus, Interface
from inotify_simple import INotify, flags
import vdf
from pathlib import Path as path

import setproctitle
setproctitle.setproctitle("python-watcher")

bus = SystemBus()
login1 = bus.get_object("org.freedesktop.login1", "/org/freedesktop/login1")
manager = Interface(login1, "org.freedesktop.login1.Manager")

watch_dirs = []
def find_libraries():
    index_file = os.path.join(path.home(), path(".steam/steam/steamapps/libraryfolders.vdf"))
    index = vdf.load(open(index_file))
    for key, value in index["libraryfolders"].items():
        if "path" in value:
            watch_dirs.append(os.path.join(value["path"], path("steamapps/downloading/")))
            watch_dirs.append(os.path.join(value["path"], path("steamapps/workshop/downloads/")))

opened = {}
closed = {}
def main():
    find_libraries()
    print(f"Checking folders: {watch_dirs}")
    for watch_dir in watch_dirs:
        opened[watch_dir]=InotifyThread(
            watch_dir, 
            flags.ACCESS | flags.CREATE, 
            callback=start_inhibit
        )
        opened[watch_dir].daemon = True
        opened[watch_dir].start()
        closed[watch_dir]=InotifyThread(
            watch_dir,
            flags.CLOSE_WRITE,
            callback=stop_inhibit
        )
        closed[watch_dir].daemon = True
        closed[watch_dir].start()
    for watch_dir in watch_dirs:
        opened[watch_dir].join()
        closed[watch_dir].join()
    
    return opened, closed

fds = {}
def start_inhibit(event, flags_list):
    global fds
    file = event.name
    if "state_" in file:
        print("Starting inhibit;", end=" ")
        fds[file] = manager.Inhibit(
            "sleep",
            "Steam",
            f"Downloading {event.name}",
            "block"
        )
        print("Inhibiting files:")
        for i in fds:
            print(i)

def stop_inhibit(event, flags_list):
    global fds
    file = event.name
    if "state_" in file:
        print("Stopping inhibit;", end=" ")
        os.close(fds[file].take())
        del fds[file]
        print("Inhibiting files:")
        for i in fds:
            print(i)

class InotifyThread(threading.Thread):
    def __init__(self, path, masks, callback=None):
        self.__path = path
        self.__masks = masks
        self.__callback = callback

        # Initialize the parent class
        threading.Thread.__init__(self)

        # Create an inotify object
        self.__inotify = INotify()

        # Create a pipe
        self.__read_fd, write_fd = os.pipe()
        self.__write = os.fdopen(write_fd, "wb")

    def run(self):
        print("Thread started for " + self.__path)
        # Watch the current directory
        self.__inotify.add_watch(self.__path, self.__masks)

        while True:
            # Wait for inotify events or a write in the pipe
            rlist, _, _ = select.select(
                [self.__inotify.fileno(), self.__read_fd], [], []
            )

            # Print all inotify events
            if self.__inotify.fileno() in rlist:
                for event in self.__inotify.read(timeout=0):
                    flags_list = [f.name for f in flags.from_mask(event.mask)]
                    if self.__callback:
                        self.__callback(event, flags_list)
                    else:
                        print(f"{event} {flags_list}")

            # Close everything properly if requested
            if self.__read_fd in rlist:
                print("Stop signal received, exiting thread")
                os.close(self.__read_fd)
                self.__inotify.close()
                return

    def stop(self):
            # Request for stop by writing in the pipe
            if not self.__write.closed:
                self.__write.write(b"\x00")
                self.__write.close()


try:
    main()
except KeyboardInterrupt:
    print("Exiting")


