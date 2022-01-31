# coding=utf-8
# Copyright (C) 2021 by Marco Melletti <mellotanica@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


import threading
import queue
from typing import Callable

from lib.gibindings import Gtk
from .eventrenderer import EventRenderer, renderertypesmap
from .event import Event
from .player import EventPlayer, playertypesmap
from .configurable import (
    Configurable,
    Configuration,
    SliderConfiguration,
    BoolConfiguration,
)
from .colorrange import ColorRangeConfiguration, ThreeValueColorRange, HSVColorRange
from gui.colors.sliders import HCYLumaSlider

from . import eventrenderer, player, event

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
                if self.renderers[r] is not None:
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

    @staticmethod
    def from_str(confstr: str):
        """
        istantiate a new ColorConsumer item using confstring as input
        :param confstr: configuration string, the same value returned from str(self)
        :return new ColorConsumer with configurations loaded
        """
        raise NotImplementedError


class LumaConsumer(ColorConsumer, Configurable):
    type = "luma"

    def __init__(
        self,
        players: [EventPlayer],
        renderer: EventRenderer,
        minluma: float = 0,
        maxluma: float = 0.1,
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

    def __str__(self):
        return ",".join([p.type for p in self.players]) + f"/{self.renderers[0].type}"

    @staticmethod
    def from_str(confstr: str):
        players = [playertypesmap[p]() for p in confstr.split("/")[0].split(",")]
        renderer = renderertypesmap[confstr.split("/")[1]]()
        return LumaConsumer(players, renderer)


class ThreeValueColorConsumer(ColorConsumer, Configurable):
    type = "threeValue"

    def __init__(
        self,
        players: [EventPlayer],
        hrenderer: EventRenderer,
        xrenderer: EventRenderer = None,
        yrenderer: EventRenderer = None,
        default_range: ThreeValueColorRange = HSVColorRange(
            "value", 1, "hue", (0, 1), (0.7, 0.9)
        ),
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

    def __str__(self):
        out = ",".join([p.type for p in self.players]) + "/"
        for r in self.renderers:
            if r is None:
                out += "None"
            else:
                out += r.type
            out += ","
        return out[:-1]

    @staticmethod
    def from_str(confstr: str):
        players = [playertypesmap[p]() for p in confstr.split("/")[0].split(",")]
        renderers = []
        for r in renderertypesmap[confstr.split("/")[1]].split(","):
            if r == "None":
                renderers.append(None)
            else:
                renderers.append(renderertypesmap[r]())
        return ThreeValueColorConsumer(players, *renderers)


colorconsumertypes = [
    LumaConsumer,
    ThreeValueColorConsumer,
]

colorconsumertypesmap = {c.type: c for c in colorconsumertypes}


class NewConsumerPage:
    """
    page widget handling the addition of a new consumer
    """

    def new_consumer(self, add_consumer_cb: Callable):
        add_consumer_cb(
            LumaConsumer(
                [player.MidiPlayer()],
                eventrenderer.DiatonicRenderer(),
            )
        )

    def show(self):
        pass


class ConsumerWidget(Configurable, Configuration):
    """
    widget holding the actual active consumers, stores the list in preferences and handles
    addition and removal of active consumers
    """

    def __init__(self, name: str):
        Configurable.__init__(self, name=name)
        Configuration.__init__(self, "Consumers", "consumers", [])
        self.consumers = []
        self.consumers_widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.new_consumer_btn = Gtk.Button(label="Add consumer")
        self.main_widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.main_widget.pack_start(self.consumers_widget, False, True, 0)
        self.main_widget.pack_end(self.new_consumer_btn, False, True, 0)
        self.main_widget.show_all()
        self.new_consumer_page = NewConsumerPage()

        def new_consumer(_):
            self.new_consumer_page.new_consumer(self.add_consumer)
            self.new_consumer_page.show()

        self.new_consumer_btn.connect("clicked", new_consumer)

    def remove_child(self, consumer: ColorConsumer):
        if isinstance(consumer, ColorConsumer):
            found = None
            for cons in range(len(self.consumers)):
                if self.consumers[cons][0] is consumer:
                    found = cons
                    break

            if found is not None:
                self.consumers[found][1].destroy()
                del self.consumers[found]
                self._set_value(self.get_value())

    def add_consumer(self, consumer: ColorConsumer):
        cgrid = Gtk.Grid()
        self.consumers.append((consumer, cgrid))
        consumer._parent = self
        consumer._subid = len(self.consumers)
        consumer.add_to_grid(cgrid, 0)
        self.consumers_widget.pack_start(cgrid, False, True, 0)
        self.consumers_widget.show_all()

        self._set_value(self.get_value())

    def remove(self, _):
        self.consumers_widget.destroy()
        self.new_consumer_btn.destroy()
        self.main_widget.destroy()
        super().remove(_)

    def add_to_grid(self, grid, row):
        self.setup_preference(self.get_prefpath())

        row = super().add_to_grid(grid, row)
        grid.attach(self._get_gui_item(), 0, row, 2, 1)
        return row + 1

    def specific_setup(self, pref_path, value):
        for cons in value:
            cname = cons.split("-")[0]
            cconf = "-".join(cons.split("-")[1:])
            if cname in colorconsumertypesmap:
                self.add_consumer(colorconsumertypesmap[cname].from_str(cconf))

    def _get_gui_item(self):
        return self.main_widget

    def get_value(self):
        return [f"{c[0].type}-{c[0]}" for c in self.consumers]
