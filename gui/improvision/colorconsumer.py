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
from .eventrenderer import EventRenderer
from .event import Event
from .player import EventPlayer
from .configurable import (
    Configurable,
    Configuration,
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
    """
    base consumer class, implements top level processing logic

    each consumer has a list of renderers and a list of playes

    if the consumer is enabled, at each scan cycle, the whole pixel column is sent to the
    local process_data function, which should search for matching areas, the areas are then
    converted to a percentual value and each matching percentual value generates an output
    play point.

    the process data should generate a list of play points for each active renderer, these
    points are then passed to the renderers and the output generated from the renderers is
    merged and sent to all the known players for actual output
    """

    def __init__(self, renderers: [EventRenderer], players: [EventPlayer]):
        threading.Thread.__init__(self, daemon=True)
        self.renderers = renderers
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
            subconfigs=self.players + self.renderers,
            removable=True,
        )
        self.queue = queue.SimpleQueue()
        self._should_exit = False

        def toggle_enabled(t):
            if not t.get_active():
                self.stop()

        enabled.toggle.connect("toggled", toggle_enabled)

    def run(self) -> None:
        while not self._should_exit:
            event = Event()
            data = self.queue.get(True, None)
            if self._should_exit:
                break
            playpoints_list = self.process_data(data)
            for r in range(min(len(self.renderers), len(playpoints_list))):
                # avoid errors, if too few renderers or playpoints are available only process what we can
                event.merge(self.renderers[r].render(playpoints_list[r]))
            for p in self.players:
                p.play(event)
        self.stop()

    def stop(self):
        for p in self.players:
            p.stop()

    def data_ready(self, color_column):
        if self.enabled:
            self.queue.put(color_column, False)

    def remove(self, _):
        super().remove(_)
        self.enabled = False
        self._should_exit = True
        self.data_ready([])
        self.stop()

    # subclasses must implement this method
    def process_data(self, color_column) -> [[float]]:
        """
        process a scanline
        :param color_column: a list of pixel data reflecting the currently processed scanline
        :return a list of lists of float, each inner element is a single play point (0~1),
                each list of play points is meant for the renderer at the same index
        """
        raise NotImplementedError


class ConsumerWidget(Configurable):
    """
    widget holding the actual active consumers, stores the list in preferences and handles
    addition and removal of active consumers
    """

    def __init__(self, name: str):
        super().__init__(name=name)
        self.active_consumers = Configuration(name, self.get_prefpath(), [])

    def add_to_grid(self, grid, row):
        pass


class LumaConsumer(ColorConsumer, Configurable):
    def __init__(
        self,
        renderer: EventRenderer,
        players: [EventPlayer],
        minluma: float,
        maxluma: float,
    ):
        ColorConsumer.__init__(self, [renderer], players)

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

    def process_data(self, color_column) -> [[float]]:
        playpoints = []
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
                    playpoints.append(1 - ((window / windowsize) / maxv))
                    window = 0
                    windowsize = 0

        return [playpoints]


class ThreeValueColorConsumer(ColorConsumer, Configurable):
    def __init__(
        self,
        hrenderer: EventRenderer,
        xrenderer: EventRenderer,
        yrenderer: EventRenderer,
        players: [EventPlayer],
        default_range: ThreeValueColorRange,
    ):
        """
        :param hrenderer: height renderer, will receive the graphical height of the matched color
        :param xrenderer: x component renderer, will receive the percent of x color component
        :param yrenderer: y component renderer, will receive the percent of the y color component
        """

        ColorConsumer.__init__(self, [hrenderer, xrenderer, yrenderer], players)

        hrenderer.label += " (height)"
        xrenderer.label += " (color x)"
        yrenderer.label += " (color y)"

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
        hplaypoints = []
        xplaypoints = []
        yplaypoints = []

        window = [0, 0, 0]
        windowsize = 0

        cr = self.colorrange

        maxv = len(color_column)
        for y in range(maxv):
            match, xv, yv = cr.in_range(color_column[y])

            if match:
                window[0] += y
                window[1] += xv
                window[2] += yv
                windowsize += 1
            else:
                if windowsize > 0:
                    hplaypoints.append(1 - ((window[0] / windowsize) / maxv))
                    xplaypoints.append(window[1] / windowsize)
                    yplaypoints.append(window[2] / windowsize)
                    window[0] = window[1] = window[2] = 0
                    windowsize = 0

        return [hplaypoints, xplaypoints, yplaypoints]
