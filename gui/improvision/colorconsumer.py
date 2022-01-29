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
from .configurable import (
    Configurable,
    NumericConfiguration,
    ListConfiguration,
    SliderConfiguration,
    BoolConfiguration,
)
from .colorrange import ColorRangeConfiguration, ThreeValueColorRange
from gui.colors.sliders import HCYLumaSlider

from lib import color

_consumers_ids = [0]


class ColorConsumer(threading.Thread, Configurable):
    def __init__(self, renderer: NoteRenderer, players: [NotePlayer]):
        threading.Thread.__init__(self, daemon=True)
        self.renderer = renderer
        if type(players) is list:
            self.players = players
        else:
            self.players = [players]
        self._cid = _consumers_ids[-1] + 1
        _consumers_ids.append(self._cid)
        enabled = BoolConfiguration("Enabled", "enabled", True)
        Configurable.__init__(
            self,
            confmap={"enabled": enabled},
            subconfigs=self.players + [self.renderer],
        )
        self.queue = queue.SimpleQueue()

        def toggle_enabled(t):
            if not t.get_active():
                self.stop()

        enabled.toggle.connect("toggled", toggle_enabled)

    def run(self) -> None:
        while True:
            notes = self.renderer.render(self.process_data(self.queue.get(True, None)))
            for p in self.players:
                p.play(notes)

    def stop(self):
        for p in self.players:
            p.stop()

    def data_ready(self, color_column):
        if self.enabled:
            self.queue.put(color_column, False)

    # subclasses must implement this method
    def process_data(self, color_column) -> ([int], int):
        raise NotImplementedError


class LumaConsumer(ColorConsumer, Configurable):
    def __init__(
        self,
        renderer: NoteRenderer,
        players: [NotePlayer],
        minluma: float,
        maxluma: float,
    ):
        ColorConsumer.__init__(self, renderer, players)

        def configureDecimalSpinbuttons(sb: Gtk.SpinButton):
            sb.set_digits(2)

        self.setup_configurable(
            "Luma Detector",
            "luma-" + str(self._cid),
            confmap={
                "minluma": SliderConfiguration(
                    "Min Luma", "minluma", minluma, HCYLumaSlider()
                ),
                "maxluma": SliderConfiguration(
                    "Max Luma", "maxluma", maxluma, HCYLumaSlider()
                ),
            },
        )

    def process_data(self, color_column):
        notes = []
        window = 0
        windowsize = 0
        maxv = len(color_column)
        if self.minluma <= self.maxluma:
            minluma = self.minluma
            maxluma = self.maxluma
        else:
            minluma = self.maxluma
            maxluma = self.minluma
        for y in range(maxv):
            luma = color_column[y].get_luma()
            if minluma <= luma <= maxluma:
                window += y
                windowsize += 1
            else:
                if windowsize > 0:
                    notes.append(maxv - int(window / windowsize))
                    window = 0
                    windowsize = 0

        return (notes, maxv)


class ThreeValueColorConsumer(ColorConsumer, Configurable):
    def __init__(
        self,
        renderer: NoteRenderer,
        players: [NotePlayer],
        default_range: ThreeValueColorRange,
    ):

        ColorConsumer.__init__(self, renderer, players)

        self.setup_configurable(
            "Color Detector",
            "color-" + str(self._cid),
            confmap={
                "colorrange": ColorRangeConfiguration(
                    "Color range",
                    "color_range",
                    default_range,
                ),
            },
        )

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
