# coding=utf-8
# Copyright (C) 2021 by Marco Melletti <mellotanica@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


import math
import re
from typing import List
from .configurable import Configuration, NumericConfiguration

from lib.gibindings import Gtk


class Note:
    _note_names = [
        ("C"),
        ("C#", "Db"),
        ("D"),
        ("D#", "Eb"),
        ("E"),
        ("F"),
        ("F#", "Gb"),
        ("G"),
        ("G#", "Ab"),
        ("A"),
        ("A#", "Bb"),
        ("B"),
    ]
    _base_octave = -1

    def __init__(self, notedef, velocity=127):
        """
        :param notedef: based on the type the parameter will be interpreted as:
           - string: decode note from string name (e.g. A2, C#4+24, ...)
           - float: create note from frequency
           - int: create a note without any bending and specified note number
           - tuple: explicitly set note number and bend (e.g. (69, 0), (12, 32), ...)
           - Note: copy other note's values
        :param velocity: note intensity (accepted range [0-127])
        """

        self.bend = 0
        if type(notedef) is int:
            self.note = notedef
        elif type(notedef) is tuple:
            self.note = int(notedef[0])
            self.bend = int(notedef[1])
        elif type(notedef) is str:
            self.__from_string(notedef)
        elif type(notedef) is float:
            self.__from_frequency(notedef)
        elif type(notedef) is Note:
            self.note = notedef.note
            self.bend = notedef.bend

        self.velocity = velocity
        self.__validate__()

    def __repr__(self):
        return str(self) + ", note: {}, bend: {}, freq: {}, velo: {}".format(
            self.note, self.bend, self.freq(), self.velocity
        )

    def __bytes__(self):
        return bytes(str(self))

    def __hash__(self):
        return hash((self.note, self.bend, self.velocity))

    def __eq__(self, other):
        return (
            self.note == other.note
            and self.bend == other.bend
            and self.velocity == other.velocity
        )

    def __lt__(self, other):
        return self.note < other.note or (
            self.note == other.note
            and (
                self.bend < other.bend
                or (self.bend == other.bend and self.velocity < other.velocity)
            )
        )

    def __validate__(self):
        if self.note < 0 or self.note > 127:
            raise AttributeError("note {} out of midi range".format(self.note))
        if self.bend < 0 or self.bend > 127:
            raise AttributeError("bend {} out of midi range".format(self.bend))
        if self.velocity < 0 or self.velocity > 127:
            raise AttributeError("velocity {} out of midi range".format(self.velocity))

    def __add__(self, other):
        on = Note(other)
        note = self.note + on.note
        bend = self.bend + on.bend
        if bend > 127:
            note += 1
            bend -= 127
        if note > 127:
            note = 127
            bend = 127
        return Note((note, bend))

    def __sub__(self, other):
        on = Note(other)
        note = self.note - on.note
        bend = self.bend - on.bend
        if bend < 0:
            note -= 1
            bend += 127
        if note < 0:
            note = 0
            bend = 0
        return Note((note, bend))

    def __str__(self):
        note = self._note_names[self.note % len(self._note_names)][0]
        note += str(
            int(math.floor(self.note / len(self._note_names)) + self._base_octave)
        )
        if self.bend != 0:
            note += f"+{self.bend}"
        if self.velocity < 127:
            note += f"%{self.velocity}"
        return note

    def __from_string(self, notename: str):
        if type(notename) is not str:
            raise AttributeError("{} must be a string".format(notename))
        notename = notename.strip()
        notename = notename[0].upper() + notename[1:].lower()
        note = notename[:1]
        if notename[1] == "#" or notename[1] == "b":
            note = notename[:2]
        notenum = None
        for n in range(len(Note._note_names)):
            if note in Note._note_names[n]:
                notenum = n
        if notenum is None:
            raise AttributeError("{} is not a valid note name".format(notename))

        notename = notename[len(note) :]

        if "%" in notename:
            try:
                self.velocity = int(notename[notename.index("%") + 1 :])
            except ValueError:
                raise AttributeError(
                    "{} is not a valid velocity value ({})".format(velocity, notename)
                )
            notename = notename[: notename.index("%")]
        else:
            self.velocity = 127

        if "+" in notename:
            octave = notename[: notename.index("+")]
            bend = notename[notename.index("+") + 1 :]
        else:
            octave = notename
            bend = "0"

        try:
            octavenum = int(octave) - Note._base_octave
        except ValueError:
            raise AttributeError(
                "{} is not a valid octave number ({})".format(octave, notename)
            )
        self.note = notenum + (octavenum * 12)

        try:
            self.bend = int(bend)
        except ValueError:
            raise AttributeError(
                "{} is not a valid bending value ({})".format(bend, notename)
            )

        self.__validate__()

    def freq(self):
        notefreq = 440 * 2 ** ((self.note - 69) / 12)
        return notefreq * 2 ** (self.bend / (12 * 128))

    def __from_frequency(self, freq: float):
        self.note = int(12 * math.log2(freq / 440) + 69)
        self.bend = int((12 * 128) * math.log2(freq / self.freq()))
        if self.bend < 0:
            self.note -= 1
            self.bend = 127 + self.bend

        self.__validate__()


class ControlValue:
    """
    represents a midi control change event
    """

    def __init__(self, control: int, value: int = 0):
        self.control = int(control)
        self.value = int(value)

        if self.control < 0 or self.control > 127:
            raise AttributeError(
                "self.control {} out of midi range".format(self.control)
            )
        if self.value < 0 or self.value > 127:
            raise AttributeError("self.value {} out of midi range".format(self.value))

    def __str__(self):
        return f"<{self.control}>{self.value}"

    def __repr__(self):
        return f"CC {self.control}: {self.value}"

    def __eq__(self, other):
        return self.control == other.control and self.value == other.value

    def __lt__(self, other):
        return self.control < other.control or (
            self.control == other.control and self.value < other.value
        )

    def __hash__(self):
        return hash((self.control, self.value))

    @staticmethod
    def from_str(strdef: str):
        m = re.match("<([0-9]+)>([0-9]+)$", strdef)
        if m is None:
            raise ValueError(
                f"{strdef} is not a valid control change string (must be in the format '<CC>Value')"
            )
        return ControlValue(int(m.group(1), int(m.group(2))))


class ProgramChange:
    """
    represents a midi program change event
    """

    def __init__(self, program):
        self.program = int(program)

        if self.program < 0 or self.program > 127:
            raise AttributeError("program {} out of midi range".format(self.program))

    def __str__(self):
        return str(self.program)

    def __repr__(self):
        return f"PC {self.program}"

    @staticmethod
    def from_str(strdef: str):
        return ProgramChange(int(strdef))

    def __eq__(self, other):
        return self.program == other.program

    def __lt__(self, other):
        return self.program < other.program


class Event:
    """
    represents an output event (note, control or program change set)
    """

    def __init__(
        self,
        notes: List[Note] = [],
        controls: List[ControlValue] = [],
        program: ProgramChange = None,
    ):
        self.notes = set(notes)
        self.controls = set(controls)
        self.program = program

    def merge(self, other):
        self.notes |= other.notes
        self.controls |= other.controls
        if self.program is None:
            self.program = other.program


class NoteConfiguration(Configuration):
    def __init__(
        self,
        name: str,
        pref_path: str,
        dfl_val: Note,
        lower: Note = Note(0),
        upper: Note = Note((127, 127)),
        gui_setup_cb=None,
    ):
        super().__init__(name, pref_path, str(dfl_val), gui_setup_cb)
        self._lower = lower
        self._upper = upper
        self._buf = None

    def specific_setup(self, pref_path, value):
        self._buf = Gtk.EntryBuffer()
        self._buf.set_text(value, len(value))

        def _text_deleted(b, p, n):
            self._set_value(str(self.get_value()))

        def _text_inserted(b, p, c, n):
            self._set_value(str(self.get_value()))

        self._buf.connect("deleted-text", _text_deleted)
        self._buf.connect("inserted-text", _text_inserted)

    def _get_gui_item(self):
        entry = Gtk.Entry()
        entry.set_buffer(self._buf)

        def _plus_cb(b):
            nn = str(self.get_value() + 1)
            self._buf.set_text(nn, len(nn))

        plus = Gtk.Button.new_with_label("+")
        plus.connect("clicked", _plus_cb)

        def _minus_cb(b):
            nn = str(self.get_value() - 1)
            self._buf.set_text(nn, len(nn))

        minus = Gtk.Button.new_with_label("-")
        minus.connect("clicked", _minus_cb)

        grid = Gtk.Grid()
        grid.attach(entry, 0, 0, 1, 1)
        grid.attach(minus, 1, 0, 1, 1)
        grid.attach(plus, 2, 0, 1, 1)

        return grid

    def get_value(self):
        try:
            n = Note(self._buf.get_text())
        except:
            n = Note(self._get_preference_value())
        return n
