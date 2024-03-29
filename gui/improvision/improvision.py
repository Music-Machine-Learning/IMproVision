# coding=utf-8
# Copyright (C) 2021 by Marco Melletti <mellotanica@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


import threading
import math

import lib.color

from lib.pycompat import xrange
from lib.pycompat import PY3

from lib.gibindings import Gtk

import gui.overlays
import gui.drawutils
from gui.framewindow import FrameOverlay
from . import colorconsumer, eventrenderer, player, colorrange
from .event import Note
from .configurable import Configurable, NumericConfiguration


class IMproVision(gui.overlays.Overlay, Configurable):
    ## Class constants

    # preferences
    SCANLINE_PREF_BEATS = "improvision-beats"
    SCANLINE_MIN_BEATS = 1
    SCANLINE_DEFAULT_BEATS = 4
    SCANLINE_MAX_BEATS = 64

    SCANLINE_PREF_BPM = "improvision-bpm"
    SCANLINE_MIN_BPM = 1
    SCANLINE_DEFAULT_BPM = 120
    SCANLINE_MAX_BPM = 600

    SCANLINE_PREF_TIMERES = "improvision-timeres"
    SCANLINE_MIN_TIME_RES_MS = 10
    SCANLINE_DEFAULT_TIME_RES_MS = 20
    SCANLINE_MAX_TIME_RES_MS = 1000

    # scanline default angle in radians, where 0 is left to right and
    # rotation goes on counter clockwise
    SCANLINE_DEFAULT_ANGLE = 0

    def __init__(self, app):
        """Constructor for improvision controller

        :param document: active document instance
        :type app: gui.document.Document

        """
        gui.overlays.Overlay.__init__(self)
        self.app = app
        self.frame = None

        self.angle = IMproVision.SCANLINE_DEFAULT_ANGLE
        self.active = False
        self.step = -1
        self.stepinc = 1
        self.step_changed = False
        self.continuous = False
        self.single_step = False

        self.update_thread = threading.Thread(target=self.updateVision, daemon=True)
        self.play_thread = threading.Thread(target=self.processSound, daemon=True)
        self.threads_started = False
        self.sleeper = threading.Event()
        self.data_ready = threading.Event()

        # XXX: setup note consumers here
        self.consumers = [
            colorconsumer.LumaConsumer(
                eventrenderer.DiatonicRenderer(Note("A1"), 3, "minor pentatonic"),
                [player.MidiPlayer(channel=0)],
                0,
                0.1,
            ),
            colorconsumer.ThreeValueColorConsumer(
                eventrenderer.DiatonicRenderer(Note("C2"), 5, "major pentatonic"),
                eventrenderer.ControlChangeRenderer(7, 0, 127),
                eventrenderer.ControlChangeRenderer(9, 0, 127),
                [player.MidiPlayer(channel=1)],
                colorrange.HSVColorRange("hue", 0, "saturation", (0.8, 1), (0.4, 0.6)),
            ),
            colorconsumer.ThreeValueColorConsumer(
                eventrenderer.DiatonicRenderer(Note("C2"), 5, "major pentatonic"),
                eventrenderer.ControlChangeRenderer(7, 0, 127),
                eventrenderer.ControlChangeRenderer(9, 0, 127),
                [player.MidiPlayer(channel=1)],
                colorrange.RGBColorRange("red", 0, "green", (0.8, 1), (0.4, 0.6)),
            ),
        ]

        Configurable.__init__(
            self,
            None,
            "improvision",
            {
                "bpm": NumericConfiguration(
                    "BPM",
                    "bpm",
                    Gtk.SpinButton,
                    self.SCANLINE_DEFAULT_BPM,
                    self.SCANLINE_MIN_BPM,
                    self.SCANLINE_MAX_BPM,
                ),
                "beats": NumericConfiguration(
                    "Loop beats",
                    "beats",
                    Gtk.SpinButton,
                    self.SCANLINE_DEFAULT_BEATS,
                    self.SCANLINE_MIN_BEATS,
                    self.SCANLINE_MAX_BEATS,
                ),
                "timeres": NumericConfiguration(
                    "Time Resolution (ms)",
                    "timeres",
                    Gtk.SpinButton,
                    self.SCANLINE_DEFAULT_TIME_RES_MS,
                    self.SCANLINE_MIN_TIME_RES_MS,
                    self.SCANLINE_MAX_TIME_RES_MS,
                ),
            },
            self.consumers,
            expanded=True,
        )

        self.active_row = None

    def init_frame(self):
        if self.frame is None:
            frame = None
            for o in self.app.doc.tdw.display_overlays:
                if isinstance(o, FrameOverlay):
                    frame = o
                    break
            assert frame is not None
            self.frame = frame

    def trigger_one(self, event):
        self.continuous = False
        self.single_step = False
        self.step = -1
        self._start()

    def step_one(self, event):
        self.single_step = True
        self._start()

    def loop(self, event):
        self.continuous = True
        self.single_step = False
        self._start()

    def _start(self):
        self.init_frame()
        if not self.threads_started:
            self.update_thread.start()
            self.play_thread.start()
            for c in self.consumers:
                c.start()
            self.threads_started = True
        self.active = True
        self.sleeper.set()
        if not self.frame.doc.model.frame_enabled:
            self.app.find_action("FrameEditMode").activate()

    def stop(self, event):
        self.active = False
        self.single_step = False
        self.step = -1
        self.redraw()
        self.sleeper.set()
        for c in self.consumers:
            c.stop()

    def redraw(self):
        self.app.doc.tdw.queue_draw()

    def paint(self, cr):
        if self.active or self.single_step:

            if self.step_changed:
                self.step_changed = False

                self.active_row = self.app.doc.model.frame[:]
                self.active_row[0] += self.step
                self.active_row[2] = 1

                self.data_ready.set()

            base = self.app.doc.tdw.model_to_display(
                self.active_row[0], self.active_row[1]
            )
            top = self.app.doc.tdw.model_to_display(
                self.active_row[0], self.active_row[1] + self.active_row[3]
            )

            # draw scanline
            cr.new_path()
            cr.move_to(*base)
            cr.line_to(*top)
            cr.set_source_rgb(255, 255, 255)
            cr.set_line_width(2)
            cr.stroke()
            cr.new_path()
            cr.move_to(*base)
            cr.line_to(*top)
            gui.drawutils.render_drop_shadow(cr, z=1, line_width=2)

    def updateVision(self):
        while True:
            self.sleeper.clear()
            if self.active:
                w = self.app.doc.model.get_frame()[2]
                if w == 0:
                    self.sleeper.wait(timeout=0.01)
                    continue
                interrupt = False
                if self.single_step:
                    interrupt = True
                    self.step = (self.step + 1) % w
                elif self.continuous:
                    self.step = (self.step + self.stepinc) % w
                else:
                    if self.step + self.stepinc > w:
                        interrupt = True
                        self.stop(None)
                        self.step = w - 1
                    else:
                        self.step += self.stepinc
                self.step_changed = True
                self.redraw()
                if interrupt:
                    self.active = False
                    continue
                else:
                    timeres = self.timeres / 1000
                    pixel_duration = ((60 / self.bpm) * self.beats) / w
                    if pixel_duration < timeres:
                        self.stepinc = math.ceil(timeres / pixel_duration)
                        pixel_duration *= self.stepinc
                    self.sleeper.wait(timeout=pixel_duration)
            else:
                self.sleeper.wait()

    def processSound(self):
        while True:
            try:
                self.data_ready.wait()
                self.data_ready.clear()

                # horrible hack, the render_layer_as_pixbuf reads one pixel ahead, so we bring
                # the rendering window back before getting color data
                actual_row = self.active_row[:]
                actual_row[0] -= 1

                pixbuf = self.app.doc.model._layers.render_layer_as_pixbuf(
                    self.app.doc.model._layers, actual_row
                )

                n_channels = pixbuf.get_n_channels()
                assert n_channels in (3, 4)
                data = pixbuf.get_pixels()

                colors = []
                rowstride = pixbuf.get_rowstride()
                for y in xrange(min(self.active_row[3], pixbuf.get_height())):
                    if PY3:
                        col = lib.color.RGBColor(
                            data[y * rowstride + n_channels] / 255,
                            data[y * rowstride + n_channels + 1] / 255,
                            data[y * rowstride + n_channels + 2] / 255,
                        )
                    else:
                        col = lib.color.RGBColor(
                            ord(data[y * rowstride + n_channels]) / 255,
                            ord(data[y * rowstride + n_channels + 1]) / 255,
                            ord(data[y * rowstride + n_channels + 2]) / 255,
                        )
                    colors.append(col)

                # print("step {}, colors: {}".format(self.step, colors))
                for c in self.consumers:
                    c.data_ready(colors)

            except Exception as e:
                print("error getting color data: {}".format(e))
