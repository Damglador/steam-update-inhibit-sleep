A relatively simple python script that watches some Steam directories to detect if Steam is installing something and not let system suspend during that.

It searches for all Steam libraries in `.steam/steam/steamapps/libraryfolders.vdf`, and watches `steamapps/downloading/` (games) and `steamapps/workshop/downloads/` (workshop items) in them with inotify.

Right now it's incompatible with Steam flatpak without manual changes (manually fillind watch_dirs variable)
