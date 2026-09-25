# Cooperative garbage-collection support for MicroPython.
#
# This module provides a generator task which disables automatic garbage
# collection and performs a collection each time the cooperative scheduler runs
# the task.
#
# Original work:
#     Copyright (c) 2026 Charlie Refvem
#     Released under the GNU General Public License, version 3.0.
#
# This software is intended for educational use, but its use is not limited
# thereto.
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, version 3.0.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.

from gc import collect, disable


# Run garbage collection cooperatively with other tasks.
def run():
    disable()
    while True:
        collect()
        yield None
