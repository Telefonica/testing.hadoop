import sys
import collections
import os
import subprocess
import javaproperties


class SkipIfNotInstalledDecorator(object):
    name = ''

    def search_server(self):
        pass  # raise exception if not found

    def __call__(self, arg=None):
        if sys.version_info < (2, 7):
            from unittest2 import skipIf
        else:
            from unittest import skipIf

        def decorator(fn, path=arg):
            if path:
                cond = not os.path.exists(path)
            else:
                try:
                    self.search_server()
                    cond = False  # found
                except Exception:
                    cond = True  # not found

            return skipIf(cond, "%s not found" % self.name)(fn)

        if isinstance(arg, collections.Callable):  # execute as simple decorator
            return decorator(arg, None)
        else:  # execute with path argument
            return decorator


def get_path_of(name):
    if os.name == 'nt':
        which = 'where'
    else:
        which = 'which'
    try:
        path = subprocess.Popen([which, name],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE).communicate()[0]
        if path:
            return path.rstrip().decode('utf-8')
        else:
            return None
    except Exception:
        return None


def modify_conf_properties(filename, modified_properties):
    with open(filename, 'r') as fp:
        properties = javaproperties.load(fp)

    with open(filename, 'w') as fp:
        properties.update(modified_properties)
        javaproperties.dump(properties, fp)
    return properties