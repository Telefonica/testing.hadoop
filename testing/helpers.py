import sys
import collections
import os
import subprocess
import javaproperties


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
