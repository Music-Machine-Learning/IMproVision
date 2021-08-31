# coding=utf-8
# Copyright (C) 2021 by Marco Melletti <mellotanica@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


import threading
import queue

from lib.gibindings import Gtk
from .noterenderer import NoteRenderer
from .player import NotePlayer
from .configurable import Configurable, NumericConfiguration, ListConfiguration

from lib import color

_consumers_ids = [0]


class ColorConsumer(threading.Thread, Configurable):
    def __init__(self,  renderer: NoteRenderer, players: [NotePlayer]):
        threading.Thread.__init__(self, daemon=True)
        self.renderer = renderer
        if type(players) is list:
            self.players = players
        else:
            self.players = [players]
        self._cid = _consumers_ids[-1]+1
        _consumers_ids.append(self._cid)
        Configurable.__init__(self, subconfigs=self.players+[self.renderer])
        self.queue = queue.SimpleQueue()

    def run(self) -> None:
        while True:
            notes = self.renderer.render(
                self.process_data(self.queue.get(True, None))
            )
            for p in self.players:
                p.play(notes)

    def stop(self):
        for p in self.players:
            p.stop()

    def data_ready(self, color_column):
        self.queue.put(color_column, False)

    # subclasses must implement this method
    def process_data(self, color_column) -> ([int], int):
        raise NotImplementedError


class LumaConsumer(ColorConsumer, Configurable):
    def __init__(self, renderer: NoteRenderer, players: [NotePlayer], minluma: float, maxluma: float):
        ColorConsumer.__init__(self, renderer, players)

        def configureDecimalSpinbuttons(sb: Gtk.SpinButton):
            sb.set_digits(2)

        self.setup_configurable('Luma Detector', "luma-"+str(self._cid), confmap={
            "minluma": NumericConfiguration(
                "Min Luma", "minluma", Gtk.SpinButton,
                minluma, 0, 1, step_incr=0.01, page_incr=0.1, gui_setup_cb=configureDecimalSpinbuttons
            ),
            "maxluma": NumericConfiguration(
                "Max Luma", "maxluma", Gtk.SpinButton,
                maxluma, 0, 1, step_incr=0.01, page_incr=0.1, gui_setup_cb=configureDecimalSpinbuttons
            ),
        })

    def process_data(self, color_column):
        notes = []
        window = 0
        windowsize = 0
        maxv = len(color_column)
        for y in range(maxv):
            luma = color_column[y].get_luma()
            if self.minluma <= luma <= self.maxluma:
                window += y
                windowsize += 1
            else:
                if windowsize > 0:
                    notes.append(maxv - int(window / windowsize))
                    window = 0
                    windowsize = 0

        return (notes, maxv)


class HSVConsumer(ColorConsumer, Configurable):
    references = {
        "hue": 0,
        "saturation": 1,
        "value": 2,
    }

    def __init__(self, renderer: NoteRenderer, players: [NotePlayer], default: float, firstrange: (float, float),
                     secondrange: (float, float), refvalue: str, firstref: str):

        ColorConsumer.__init__(self, renderer, players)

        def configureDecimalSpinbuttons(sb: Gtk.SpinButton):
            sb.set_digits(2)

        self.setup_configurable('HSV Detector', "hsv-"+str(self._cid), confmap={
            "ref": ListConfiguration("Reference parameter", "reference", refvalue, self.references),
            "firstrange": ListConfiguration("First range parameter", "firstrange", firstref, self.references),
            "refval": NumericConfiguration(
                "Reference", "refval", Gtk.SpinButton, default, 0, 1, step_incr=0.01, page_incr=0.1, gui_setup_cb=configureDecimalSpinbuttons
            ),
            "minfirst": NumericConfiguration(
                "First min", "minfirst", Gtk.SpinButton, firstrange[0], 0, 1, step_incr=0.01, page_incr=0.1, gui_setup_cb=configureDecimalSpinbuttons
            ),
            "maxfirst": NumericConfiguration(
                "First max", "maxfirst", Gtk.SpinButton, firstrange[1], 0, 1, step_incr=0.01, page_incr=0.1, gui_setup_cb=configureDecimalSpinbuttons
            ),
            "minsex": NumericConfiguration(
                "Second min", "minsec", Gtk.SpinButton, secondrange[0], 0, 1, step_incr=0.01, page_incr=0.1, gui_setup_cb=configureDecimalSpinbuttons
            ),
            "maxsec": NumericConfiguration(
                "Second max", "maxsec", Gtk.SpinButton, secondrange[1], 0, 1, step_incr=0.01, page_incr=0.1, gui_setup_cb=configureDecimalSpinbuttons
            ),
        })

    def process_data(self, color_column: [color.RGBColor]):
        notes = []
        window = 0
        windowsize = 0

        rv = self.ref
        fv = self.firstrange
        sv = 3 - rv - fv

        maxv = len(color_column)
        for y in range(maxv):
            col = color_column[y].get_hsv()

            if abs(col[rv]-self.refval) < 0.01 and self.minfirst <= col[fv] <= self.maxfirst and self.minsec <= col[sv] <= self.maxsec:
                window += y
                windowsize += 1
            else:
                if windowsize > 0:
                    notes.append(maxv - int(window / windowsize))
                    window = 0
                    windowsize = 0

        return (notes, maxv)
