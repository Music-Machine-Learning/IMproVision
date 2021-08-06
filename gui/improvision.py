import threading
import math

from lib.gibindings import Gdk
import lib.color

from lib.pycompat import xrange
from lib.pycompat import PY3

import gui.overlays
import gui.drawutils


class IMproVision(gui.overlays.Overlay):
    ## Class constants


    # scanline default angle in radians, where 0 is left to right and
    # rotation goes on counter clockwise
    SCANLINE_DEFAULT_ANGLE = 0

    # scanline default cycle duration in hz
    SCANLINE_DEFAULT_SPEED_HZ = 1

    # scanline default time resolution in milliseconds
    SCANLINE_DEFAULT_TIME_RES_MS = 20

    def __init__(self, frame):
        """Constructor for improvision controller

        :param document: active document instance
        :type app: gui.document.Document

        """
        gui.overlays.Overlay.__init__(self)

        self.frame = frame
        self.angle = IMproVision.SCANLINE_DEFAULT_ANGLE
        self.speed = IMproVision.SCANLINE_DEFAULT_SPEED_HZ
        self.timeres = IMproVision.SCANLINE_DEFAULT_TIME_RES_MS / 1000
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

    def trigger_one(self):
        self.continuous = False
        self.step = 0
        self._start()

    def loop(self):
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
            self.frame.doc.app.find_action("FrameEditMode").activate()

    def stop(self):
        self.active = False
        self.step = 0
        self.redraw()

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
            if self.active:
                self.sleeper.clear()
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
                    sleeptime = (1.0 / self.speed) / w
                    if sleeptime < self.timeres:
                        self.stepinc = math.ceil(self.timeres / sleeptime)
                        sleeptime = self.timeres
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
