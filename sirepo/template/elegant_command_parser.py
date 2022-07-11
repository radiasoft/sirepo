# -*- coding: utf-8 -*-
"""elegant command parser.

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo.template.line_parser import LineParser
import re


_SKIP_COMMANDS = ["subprocess"]


def parse_file(command_text, update_filenames):
    parser = LineParser(0)
    lines = command_text.replace("\r", "").split("\n")
    prev_line = ""
    commands = []

    for line in lines:
        parser.increment_line_number()
        if re.search(r"^#", line):
            continue
        line = re.sub(r"\!.*$", "", line)
        if not line:
            continue
        if re.search(r"\&end", line):
            if not _parse_line(parser, prev_line + " " + line, commands):
                break
            prev_line = ""
        elif re.search(r"\&", line) or prev_line:
            prev_line += " " + line
        else:
            # ignoring lines between command markers
            pass
    if prev_line and re.search(r"\&", prev_line):
        parser.raise_error("missing &end for command: {}".format(prev_line))
    if update_filenames:
        _update_lattice_names(commands)
    return commands


def _parse_array_value(parser):
    # read off the end of the array value list
    # parse values until a "&end" or "value =" is reached
    #
    # response[2] = %s.vhrm, %s.hvrm,
    # distribution_type[0] = "gaussian", "gaussian",
    # enforce_rms_values[0] = 1,1,1,
    # distribution_type[0] = gaussian, gaussian, hard-edge,
    # distribution_type[0] = 3*"gaussian",
    # distribution_cutoff[0] = 3*3,
    res = ""
    index = parser.get_index()
    while True:
        value = parser.parse_value()
        if value == "&end":
            parser.reset_index(index)
            break
        parser.ignore_whitespace()
        if parser.peek_char() == "=":
            parser.reset_index(index)
            break
        if value:
            res += value
        else:
            if parser.peek_char() == ",":
                parser.assert_char(",")
                res += ","
            elif parser.peek_char() == "*":
                parser.assert_char("*")
                res += "*"
            else:
                parser.raise_error("expecting an array value")
        index = parser.get_index()
    if not res:
        parser.raise_error("missing array value")
    res = re.sub(r",$", "", res)
    return res


def _parse_line(parser, line, commands):
    parser.set_line(line)
    parser.ignore_whitespace()
    parser.assert_char("&")
    command = PKDict(
        _id=parser.next_id(),
        _type=parser.parse_value(r"\s+"),
    )
    if command["_type"] == "stop":
        return False
    parser.ignore_whitespace()
    while True:
        value = parser.parse_value()
        if not value:
            if parser.peek_char() == ",":
                parser.assert_char(",")
                continue
            parser.raise_error("expecting a command element")
        if value == "&end":
            break
        if parser.peek_char() == "=":
            parser.assert_char("=")
            if re.search(r"\[", value):
                command[value] = _parse_array_value(parser)
            else:
                command[value] = parser.parse_value(r"[\s,=\!)]")
        else:
            parser.raise_error("trailing input: {}".format(value))
    parser.assert_end_of_line()
    if not command["_type"] in _SKIP_COMMANDS:
        commands.append(command)
    return True


def _update_lattice_names(commands):
    # preserve the name of the first run_setup.lattice
    # others may map to previous save_lattice names
    is_first_run_setup = True
    save_lattices = []
    for cmd in commands:
        if cmd["_type"] == "save_lattice":
            name = re.sub(r"\%s", "", cmd["filename"])
            save_lattices.append(name)
        if cmd["_type"] == "run_setup":
            if is_first_run_setup:
                is_first_run_setup = False
                continue
            for index in reversed(range(len(save_lattices))):
                if re.search(
                    re.escape(save_lattices[index]), cmd["lattice"], re.IGNORECASE
                ):
                    cmd["lattice"] = (
                        "save_lattice"
                        if index == 0
                        else "save_lattice{}".format(index + 1)
                    )
                    break
            else:
                cmd["lattice"] = "Lattice"
