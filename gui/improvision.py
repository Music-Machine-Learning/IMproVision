import threading
import math

import gui.framewindow
import gui.drawutils


class IMproVision(gui.framewindow.FrameOverlay):
    ## Class constants

    # scanline default angle in radians, where 0 is left to right and
    # rotation goes on counter clockwise
    SCANLINE_DEFAULT_ANGLE = 0

    # scanline default cycle duration in hz
    SCANLINE_DEFAULT_SPEED_HZ = 1

    # scanline default time resolution in milliseconds
    SCANLINE_DEFAULT_TIME_RES_MS = 20

    def __init__(self, doc):
        """Constructor for improvision controller

        :param document: active document instance
        :type app: gui.document.Document

        """
        self.angle = IMproVision.SCANLINE_DEFAULT_ANGLE
        self.speed = IMproVision.SCANLINE_DEFAULT_SPEED_HZ
        self.timeres = IMproVision.SCANLINE_DEFAULT_TIME_RES_MS / 1000
        self.active = False
        self.step = 0
        self.stepinc = 1
        self.step_changed = False

        self.update_thread = threading.Thread(target=self.updateVision, daemon=True)
        self.play_thread = threading.Thread(target=self.processSound, daemon=True)
        self.threads_started = False
        self.sleeper = threading.Event()
        self.data_ready = threading.Event()

        self.active_row = []

        gui.framewindow.FrameOverlay.__init__(self, doc)

    def toggleVision(self, active):
        if not self.threads_started:
            self.update_thread.start()
            self.play_thread.start()
            self.threads_started = True
        self.active = active
        self.step = 0
        self.doc.app.find_action("FrameEditMode").activate()

    def paint(self, cr):
        gui.framewindow.FrameOverlay.paint(self, cr)

        # TODO: consider angles
        base, _, _, top = self._display_corners
        base = (base[0] + self.step, base[1])
        top = (top[0] + self.step, top[1])

        if self.step_changed:
            self.step_changed = False

            self.active_row = [self.doc.tdw.pick_color(int(base[0]), y, 1) for y in range(int(base[1]), int(top[1]))]
            self.data_ready.set()

        # draw scanline
        cr.new_path()
        cr.move_to(*base)
        cr.line_to(*top)
        cr.set_line_width(0)
        gui.drawutils.render_drop_shadow(cr, z=1, line_width=self.OUTLINE_WIDTH)

    def updateVision(self):
        while True:
            if self.active:
                _, _, w, _ = self.doc.model.get_frame()
                if w == 0:
                    self.sleeper.wait(timeout=0.01)
                    continue
                w = int(w)
                self.step = (self.step + self.stepinc) % w
                self.step_changed = True
                self.redraw(True)
                sleeptime = (1.0 / self.speed) / w
                if sleeptime < self.timeres:
                    self.stepinc = math.ceil(self.timeres / sleeptime)
                    sleeptime = self.timeres
                self.sleeper.wait(timeout=sleeptime)

    def processSound(self):
        while True:
            self.data_ready.wait()
            self.data_ready.clear()

            print("new data: {}".format(self.active_row))
            # TODO: process self.active_row