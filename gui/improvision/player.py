# coding=utf-8
# Copyright (C) 2021 by Marco Melletti <mellotanica@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


from pygame import midi
from .configurable import Configurable, NumericConfiguration, ListConfiguration
from lib.gibindings import Gtk
from .note import Note

_midi_devices = {}


class ControlValue:
    """
    represents a midi control change event
    """

    def __init__(self, control: int, value: int = 0):
        self.control = control
        self.value = value

    def __str__(self):
        return f"CC {self.control}: {self.value}"

    def __repr__(self):
        return str(self)


class ProgramChange:
    """
    represents a midi program change event
    """

    def __init__(self, program):
        self.program = program

    def __str__(self):
        return f"PC {self.program}"

    def __repr__(self):
        return str(self)


class NotePlayer(Configurable):
    def __init__(self):
        super().__init__()
        self.active_notes = set()

    def __del__(self):
        self.stop()

    def play(self, notes: set[Note]):
        stop_notes = self.active_notes - notes
        play_notes = notes - self.active_notes

        if len(play_notes) > 0:
            self.notes_on(play_notes)
        if len(stop_notes) > 0:
            self.notes_off(stop_notes)

        self.active_notes -= stop_notes
        self.active_notes |= play_notes

    def stop(self):
        self.notes_off(self.active_notes)
        self.active_notes = set()

    def notes_on(self, notes: set[Note]):
        raise NotImplementedError

    def notes_off(self, notes: set[Note]):
        raise NotImplementedError

    def send_cc(self, control: ControlValue):
        raise NotImplementedError

    def send_pc(self, program: ProgramChange):
        raise NotImplementedError


class LogPlayer(NotePlayer):
    def __init__(self):
        super().__init__()

    def notes_on(self, notes: set[Note]):
        print("notes on: {}, active_notes: {}".format(notes, self.active_notes))

    def notes_off(self, notes: set[Note]):
        print("notes off: {}, active_notes: {}".format(notes, self.active_notes))

    def send_cc(self, control):
        print(f"control change: {control}")

    def send_pc(self, program):
        print(f"program change: {program}")


class MidiPlayer(NotePlayer):
    MODES = ["note", "cv", "program"]

    def __init__(self, channel=1, device_id=None):
        super().__init__()
        self.output = None
        if not midi.get_init():
            midi.init()
        if device_id is None:
            device_id = midi.get_default_output_id()

        mididevs = {}
        dfldev = None
        for did in range(midi.get_count()):
            dev = midi.get_device_info(did)
            if dev[3] == 1:
                devname = dev[1].decode()
                mididevs[devname] = did
            if did == device_id:
                dfldev = devname

        def config_devbox(combo):
            def _set_dev_cb(c):
                self.set_device(self.device)

            combo.connect("changed", _set_dev_cb)
            self.set_device(self.device)

        self.setup_configurable(
            "MIDI Output",
            "midi",
            confmap={
                # "mode": ListConfiguration("Output Mode", "mode", default_val, items),
                "channel": NumericConfiguration(
                    "MIDI Channel",
                    "channel",
                    Gtk.SpinButton,
                    channel,
                    1,
                    16,
                    step_incr=1,
                    page_incr=1,
                ),
                "device": ListConfiguration(
                    "MIDI Device",
                    "device",
                    dfldev,
                    mididevs,
                    gui_setup_cb=config_devbox,
                ),
            },
        )

    def set_device(self, device_id):
        device_id = int(device_id)
        if device_id in _midi_devices:
            self.output = _midi_devices[device_id]
        else:
            self.output = midi.Output(device_id)
            _midi_devices[device_id] = self.output

    def notes_on(self, notes: set[Note]):
        if isinstance(self.output, midi.Output):
            for n in notes:
                self.output.note_on(
                    n.note, velocity=n.velocity, channel=int(self.channel) - 1
                )

    def notes_off(self, notes: set[Note]):
        if isinstance(self.output, midi.Output):
            for n in notes:
                self.output.note_off(n.note, velocity=0, channel=int(self.channel) - 1)

    def send_cc(self, control: ControlValue):
        if isinstance(self.output, midi.Output):
            status = 0xB0 + int(self.channel) - 1
            self.output.write_short(status, control.control, control.value)

    def send_pc(self, program: ProgramChange):
        if isinstance(self.output, midi.Output):
            self.output.set_instrument(program.program, channel=int(self.channel) - 1)


class MonoMidiPlayer(MidiPlayer):
    def __init__(self, device_id=None, channel=0, priority_high=False):
        super().__init__(device_id, channel)
        self.priority_high = priority_high

    def play(self, notes: set[Note]):
        if len(notes) > 0:
            pn = set()
            if self.priority_high:
                pn.add(max(notes))
            else:
                pn.add(min(notes))
        else:
            pn = notes
        super().play(pn)
