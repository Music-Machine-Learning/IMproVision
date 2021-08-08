import threading
import math

import lib.color

from lib.pycompat import xrange
from lib.pycompat import PY3

import gui.overlays
import gui.drawutils
from gui.framewindow import FrameOverlay
from gui import improvisionconsumer

class IMproVision(gui.overlays.Overlay):
    ## Class constants

    # preferences names
    SCANLINE_PREF_BEATS = "improvision-beats"
    SCANLINE_PREF_BPM = "improvision-bpm"
    SCANLINE_PREF_TIMERES = "improvision-timeres"

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

        self.consumers = [
            improvisionconsumer.IMproVisionLumaConsumer(0, 0.1)
        ]

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

    def redraw(self):
        self.frame.doc.tdw.queue_draw()

    def paint(self, cr):
        if self.active or self.single_step:

            if self.step_changed:
                self.step_changed = False

                self.active_row = self.app.doc.model.frame[:]
                self.active_row[0] += self.step
                self.active_row[2] = 1

                self.data_ready.set()

            base = self.app.doc.tdw.model_to_display(self.active_row[0], self.active_row[1])
            top = self.app.doc.tdw.model_to_display(self.active_row[0], self.active_row[1] + self.active_row[3])

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
                frame = self.app.doc.model.get_frame()
                w = frame[2]
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
                        self.step = w-1
                    else:
                        self.step += self.stepinc
                self.step_changed = True
                self.redraw()
                if interrupt:
                    self.active = False
                    continue
                else:
                    timeres = self.app.preferences[self.SCANLINE_PREF_TIMERES] / 1000
                    bpm = self.app.preferences[self.SCANLINE_PREF_BPM]
                    beats = self.app.preferences[self.SCANLINE_PREF_BEATS]
                    sleeptime = ((60 / bpm) * beats) / w
                    if sleeptime < timeres:
                        self.stepinc = math.ceil(timeres / sleeptime)
                        sleeptime = timeres
                    self.sleeper.wait(timeout=sleeptime)
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

                pixbuf = self.app.doc.model._layers.render_layer_as_pixbuf(self.app.doc.model._layers, actual_row)

                n_channels = pixbuf.get_n_channels()
                assert n_channels in (3, 4)
                data = pixbuf.get_pixels()

                colors = []
                rowstride = pixbuf.get_rowstride()
                for y in xrange(min(self.active_row[3], pixbuf.get_height())):
                    if PY3:
                        col = lib.color.RGBColor(data[y*rowstride + n_channels]/255,
                                                 data[y*rowstride + n_channels + 1]/255,
                                                 data[y*rowstride + n_channels + 2]/255)
                    else:
                        col = lib.color.RGBColor(ord(data[y*rowstride + n_channels])/255,
                                                 ord(data[y*rowstride + n_channels + 1])/255,
                                                 ord(data[y*rowstride + n_channels + 2])/255)
                    colors.append(col)

                #print("step {}, colors: {}".format(self.step, colors))
                for c in self.consumers:
                    c.data_ready(colors)

            except Exception as e:
                print("error getting color data: {}".format(e))
