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
from .colorrange import ColorRangeConfiguration, HSVColorRange

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

    def __init__(self, renderer: NoteRenderer, players: [NotePlayer]):

        ColorConsumer.__init__(self, renderer, players)

        self.setup_configurable('HSV Detector', "hsv-"+str(self._cid), confmap={
            "colorrange": ColorRangeConfiguration("Color range", "color_range", HSVColorRange(
                'hue', 0, 'saturation', (0.8, 1), (0.4, 0.6)
            )),
        })

    def process_data(self, color_column: [color.RGBColor]):
        notes = []
        window = 0
        windowsize = 0

        cr = self.colorrange

        maxv = len(color_column)
        for y in range(maxv):
            match, xv, yv = cr.in_range(color_column[y])

            if match:
                window += y
                windowsize += 1
            else:
                if windowsize > 0:
                    notes.append(maxv - int(window / windowsize))
                    window = 0
                    windowsize = 0

        return (notes, maxv)
