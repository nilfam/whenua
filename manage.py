#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


PY3 = sys.version_info[0] == 3
if PY3:
    import builtins
else:
    import __builtin__ as builtins

try:
    builtins.profile
except AttributeError:
    builtins.profile = lambda x: x

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", 'scrape.settings')

    from django.core.management import execute_from_command_line

    if sys.argv[1] != 'runserver':
        os.environ['RUN_COMMAND'] = 'true'

    execute_from_command_line(sys.argv)
