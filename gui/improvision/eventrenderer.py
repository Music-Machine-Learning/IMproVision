# coding=utf-8
# Copyright (C) 2021 by Marco Melletti <mellotanica@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


from .event import Note, NoteConfiguration, Event, ProgramChange, ControlValue
from .configurable import Configurable, NumericConfiguration, ListConfiguration
from lib.gibindings import Gtk
from .utils import map_to_range


class EventRenderer(Configurable):
    def __init__(self):
        super().__init__(expanded=True)

    def render(self, vals: ([float])) -> Event:
        event = Event()
        for val in vals:
            event.merge(self.render_event(val))
        return event

    def render_event(self, pctval: float) -> Event:
        """
        render a single event (note/cc/pc)
        :param pctval: percent input value (0~1)
        """
        raise NotImplementedError


class ChromaticRenderer(EventRenderer):
    type = "chromatic"

    def __init__(self, minnote: Note = Note(0), maxnote: Note = Note(127)):
        Configurable.__init__(
            self,
            "Chromatic Renderer",
            "chromatic-renderer",
            {
                "min_note": NoteConfiguration("Lowest Note", "minnote", minnote),
                "max_note": NoteConfiguration("Highest Note", "maxnote", maxnote),
            },
        )

    def render_event(self, val: float) -> Event:
        return Event(
            notes=[self.min_note + int(val * (self.max_note - self.min_note).note)]
        )


class ScaleConfiguration(ListConfiguration):
    def __init__(
        self, name: str, pref_path: str, default_val, items, gui_setup_cb=None
    ):
        items["custom"] = []
        super().__init__(name, pref_path, default_val, items, gui_setup_cb)

    def _get_gui_item(self):
        combo = super()._get_gui_item()
        return combo


class DiatonicRenderer(EventRenderer):
    type = "diatonic"

    scales = {
        "minor pentatonic": [Note(0), Note(3), Note(5), Note(7), Note(10)],
        "major pentatonic": [Note(0), Note(2), Note(4), Note(7), Note(9)],
        "major": [Note(0), Note(2), Note(4), Note(5), Note(7), Note(9), Note(11)],
        "minor natural": [
            Note(0),
            Note(2),
            Note(3),
            Note(5),
            Note(7),
            Note(8),
            Note(10),
        ],
        "minor harmonic": [
            Note(0),
            Note(2),
            Note(3),
            Note(5),
            Note(7),
            Note(8),
            Note(11),
        ],
    }

    def __init__(
        self,
        fundamental: Note = Note("C2"),
        octaves_range: int = 2,
        scale: str = "major",
    ):
        super().__init__()

        self.setup_configurable(
            "Diatonic Reader",
            "diatonic",
            {
                "range": NumericConfiguration(
                    "Octaves Range", "range", Gtk.SpinButton, octaves_range, 1, 16
                ),
                "fundamental": NoteConfiguration(
                    "Fundamental", "fundamental", fundamental
                ),
                "scale": ScaleConfiguration("Scale", "scale", scale, self.scales),
            },
        )

    def render_event(self, val: float) -> Event:
        scale = self.scale
        trasl = int(round(val * ((self.range * len(scale)) - 1), 0))
        scalenote = scale[trasl % len(scale)]
        octave = int(trasl / len(scale))
        return Event(notes=[self.fundamental + scalenote.note + (octave * 12)])


class ControlChangeRenderer(EventRenderer):
    type = "cc"

    def __init__(self, control: int = 7, minval: int = 0, maxval: int = 127):
        super().__init__()

        self.setup_configurable(
            "Control Change Reader",
            "control",
            {
                "control": NumericConfiguration(
                    "Control", "control", Gtk.SpinButton, control, 0, 127
                ),
                "minval": NumericConfiguration(
                    "Min Value", "minval", Gtk.SpinButton, minval, 0, 127
                ),
                "maxval": NumericConfiguration(
                    "Max Value", "maxval", Gtk.SpinButton, maxval, 0, 127
                ),
            },
        )

    def render_event(self, val: float) -> Event:
        e = Event(
            controls=[
                ControlValue(self.control, map_to_range(self.minval, self.maxval, val))
            ]
        )
        return e


renderertypes = [
    ChromaticRenderer,
    DiatonicRenderer,
    ControlChangeRenderer,
]

renderertypesmap = {r.type: r for r in renderertypes}
