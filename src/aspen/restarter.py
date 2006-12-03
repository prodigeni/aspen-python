import os
import sys
import threading
import time


FLAG = '_ASPEN_RESTART_FLAG'


def look_for_changes():
    """See if any of our available modules have changed on the filesystem.
    """

    mtimes = {}
    while 1:
        for module in sys.modules.values():

            # Get out early if we can.
            # ========================

            filename = getattr(module, '__file__', None)
            if filename is None:
                continue
            if filename.endswith(".pyc"):
                filename = filename[:-1]


            # The file may have been removed from the filesystem.
            # ===================================================

            if not os.path.isfile(filename):
                print >> sys.stderr, "missing: %s" % filename
                if filename in mtimes:
                    return # trigger restart


            # Or not, in which case, check the mod time.
            # ==========================================

            mtime = os.stat(filename).st_mtime
            if filename not in mtimes: # first time we've seen it
                mtimes[filename] = mtime
                continue
            if mtime > mtimes[filename]:
                print >> sys.stderr, "outdated: %s" % filename
                return # trigger restart

        time.sleep(0.1)


if FLAG in os.environ:
    _thread = threading.Thread(target=look_for_changes)
    _thread.setDaemon(True)
    _thread.start()

    def restart():
        return not _thread.isAlive()
else:
    def restart():
        return False
