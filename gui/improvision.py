import threading
import math

from lib.gibindings import Gdk
import lib.color

from lib.pycompat import xrange
from lib.pycompat import PY3

import gui.overlays
import gui.drawutils
from gui.framewindow import FrameOverlay

from lib.gibindings import Gtk

from .toolstack import SizedVBoxToolWidget, TOOL_WIDGET_NATURAL_HEIGHT_SHORT
from lib.gettext import gettext as _
from .widgets import inline_toolbar

class IMproVision(gui.overlays.Overlay):
    ## Class constants

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
        self.step = 0
        self.stepinc = 1
        self.step_changed = False
        self.continuous = False

        self.update_thread = threading.Thread(target=self.updateVision, daemon=True)
        self.play_thread = threading.Thread(target=self.processSound, daemon=True)
        self.threads_started = False
        self.sleeper = threading.Event()
        self.data_ready = threading.Event()

        self.active_row = []

    def _realize_cb(self, drawwindow):
        frame = None
        for o in self.app.doc.tdw.display_overlays:
            if isinstance(o, FrameOverlay):
                frame = o
                break
        assert frame is not None
        self.frame = frame

    def trigger_one(self, event):
        self.continuous = False
        self.step = 0
        self._start()

    def loop(self, event):
        self.continuous = True
        self._start()

    def _start(self):
        if not self.threads_started:
            self.update_thread.start()
            self.play_thread.start()
            self.threads_started = True
        self.active = True
        self.sleeper.set()
        if not self.frame.doc.model.frame_enabled:
            self.app.find_action("FrameEditMode").activate()

    def stop(self, event):
        self.active = False
        self.step = 0
        self.redraw()
        self.sleeper.set()

    def redraw(self):
        self.frame.doc.tdw.queue_draw()

    def paint(self, cr):
        if self.active:

            # TODO: consider angles
            base, _, _, top = self.frame._display_corners
            base = (base[0] + self.step, base[1])
            top = (top[0] + self.step, top[1])
            h = int(top[1] - base[1])

            if self.step_changed:
                self.step_changed = False

                surf = self.frame.doc.tdw.renderer._new_image_surface_from_visible_area(int(base[0]), int(base[1]), 1, h, use_filter=False)
                self.active_row = Gdk.pixbuf_get_from_surface(surf, 0, 0, 1, h)

                self.data_ready.set()

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
                base, side, _, _ = self.frame._display_corners
                w = int(side[0] - base[0])
                if w == 0:
                    self.sleeper.wait(timeout=0.01)
                    continue
                interrupt = False
                if self.continuous:
                    self.step = (self.step + self.stepinc) % w
                else:
                    if self.step + self.stepinc > w:
                        interrupt = True
                        self.step = w-1
                    else:
                        self.step += self.stepinc
                self.step_changed = True
                self.redraw()
                if interrupt:
                    self.active = False
                    continue
                else:
                    timeres = self.app.preferences[IMproVisionTool.SCANLINE_PREF_TIMERES] / 1000
                    bpm = self.app.preferences[IMproVisionTool.SCANLINE_PREF_BPM]
                    beats = self.app.preferences[IMproVisionTool.SCANLINE_PREF_BEATS]
                    sleeptime = ((60 / bpm) * beats) / w
                    if sleeptime < timeres:
                        self.stepinc = math.ceil(timeres / sleeptime)
                        sleeptime = timeres
                    self.sleeper.wait(timeout=sleeptime)
            else:
                self.sleeper.wait()

    def processSound(self):
        while True:
            self.data_ready.wait()
            self.data_ready.clear()


            n_channels = self.active_row.get_n_channels()
            assert n_channels in (3, 4)
            data = self.active_row.get_pixels()

            print("got color row: {}x{}, data size: {}".format(self.active_row.get_width(), self.active_row.get_height(), len(data)))

            notes = []
            window = 0
            windowsize = 0
            colors = []
            for y in xrange(self.active_row.get_height()):
                if PY3:
                    col = lib.color.RGBColor(data[y + n_channels]/255,
                                             data[y + n_channels + 1]/255,
                                             data[y + n_channels + 2]/255)
                else:
                    col = lib.color.RGBColor(ord(data[y + n_channels])/255,
                                             ord(data[y + n_channels + 1])/255,
                                             ord(data[y + n_channels + 2])/255)

                colors.append((col.get_luma(), col))
                if col.get_luma() < 0.1:
                    window += y
                    windowsize += 1
                else:
                    if windowsize > 0:
                        notes.append(int(window / windowsize))
                        window = 0
                        windowsize = 0

            print("step {}, got notes: {}, colors: {}".format(self.step, notes, colors))
            # TODO: process self.active_row


class IMproVisionTool (SizedVBoxToolWidget):
    """Dockable panel showing options for IMproVision
    """

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

    ## Class constants

    SIZED_VBOX_NATURAL_HEIGHT = TOOL_WIDGET_NATURAL_HEIGHT_SHORT

    tool_widget_icon_name = "improvision-group-symbolic"
    tool_widget_title = _("IMproVision")
    tool_widget_description = _("IMproVision related configurations and activators")

    __gtype_name__ = 'MyPaintIMproVisionTool'

    def __init__(self):
        SizedVBoxToolWidget.__init__(self)
        from gui.application import get_app
        app = get_app()
        self.app = app
        toolbar = inline_toolbar(
            app, [
                ("IMproVisionTrigger", None),
                ("IMproVisionLoop", None),
                ("IMproVisionStop", None),
            ])

        self.pack_start(toolbar, False, True, 0)

        options = Gtk.Alignment.new(0.5, 0.5, 1.0, 1.0)
        options.set_padding(0, 0, 0, 0)
        options.set_border_width(3)

        grid = Gtk.Grid()
        row = 0

        def add_prop(self, label_text, propnam, grid, row, default, minv, maxv, step=1, page=1):
            label = Gtk.Label()
            label.set_text(_(label_text+":"))
            label.set_alignment(1.0, 0.5)
            adj = Gtk.Adjustment(value=default, lower=minv, upper=maxv, step_incr=step, page_incr=page)
            cb = getattr(self, "_"+propnam+"_changed_cb")
            adj.connect("value-changed", cb)
            setattr(self, "_"+propnam+"_adj", adj)
            spinbut = Gtk.SpinButton()
            spinbut.set_hexpand(True)
            spinbut.set_adjustment(adj)
            spinbut.set_numeric(True)
            grid.attach(label, 0, row, 1, 1)
            grid.attach(spinbut, 1, row, 1, 1)
            cb(adj)
            return row+1

        row = add_prop(
            self, "BPM", "bpm", grid, row,
            self.SCANLINE_DEFAULT_BPM, self.SCANLINE_MIN_BPM, self.SCANLINE_MAX_BPM,
        )

        row = add_prop(
            self, "Loop beats", "beats", grid, row,
            self.SCANLINE_DEFAULT_BEATS, self.SCANLINE_MIN_BEATS, self.SCANLINE_MAX_BEATS,
        )

        row = add_prop(
            self, "Time Resolution (ms)", "timeres", grid, row,
            self.SCANLINE_DEFAULT_TIME_RES_MS, self.SCANLINE_MIN_TIME_RES_MS, self.SCANLINE_MAX_TIME_RES_MS,
        )

        options.add(grid)
        options.show_all()

        self.pack_start(options, True, True, 0)

        self._overlay = IMproVision(app)
        self.app.doc.tdw.display_overlays.append(self._overlay)
        self.app.doc.tdw.connect("realize", self._overlay._realize_cb)

        actions = {
            "IMproVisionTrigger": self._overlay.trigger_one,
            "IMproVisionLoop": self._overlay.loop,
            "IMproVisionStop": self._overlay.stop,
        }

        for a, cb in actions.items():
            action = self.app.doc.action_group.get_action(a)
            action.connect("activate", cb)


    @property
    def bpm(self):
        return int(self._bpm_adj.get_value())

    @property
    def beats(self):
        return int(self._beats_adj.get_value())

    @property
    def timeres(self):
        return int(self._timeres_adj.get_value())

    def _bpm_changed_cb(self, adj):
        self.app.preferences[self.SCANLINE_PREF_BPM] = self.bpm

    def _beats_changed_cb(self, adj):
        self.app.preferences[self.SCANLINE_PREF_BEATS] = self.beats

    def _timeres_changed_cb(self, adj):
        self.app.preferences[self.SCANLINE_PREF_TIMERES] = self.timeres

