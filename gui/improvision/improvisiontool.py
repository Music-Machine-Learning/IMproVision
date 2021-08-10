from lib.gibindings import Gtk

from gui.toolstack import SizedVBoxToolWidget, TOOL_WIDGET_NATURAL_HEIGHT_SHORT
from lib.gettext import gettext as _
from gui.widgets import inline_toolbar
from .improvision import IMproVision

class IMproVisionTool (SizedVBoxToolWidget):
    """Dockable panel showing options for IMproVision
    """

    SCANLINE_MIN_BEATS = 1
    SCANLINE_DEFAULT_BEATS = 4
    SCANLINE_MAX_BEATS = 64

    SCANLINE_MIN_BPM = 1
    SCANLINE_DEFAULT_BPM = 120
    SCANLINE_MAX_BPM = 600

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
                ("IMproVisionStep", None),
                ("IMproVisionStop", None),
            ])

        self.pack_start(toolbar, False, True, 0)

        options = Gtk.Alignment.new(0.5, 0.5, 1.0, 1.0)
        options.set_padding(0, 0, 0, 0)
        options.set_border_width(3)

        grid = Gtk.Grid()
        row = 0

        def add_prop(self, label_text, propnam, grid, row, default, minv, maxv, prefname, step=1, page=1):
            label = Gtk.Label()
            label.set_text(_(label_text+":"))
            label.set_alignment(1.0, 0.5)
            if prefname not in self.app.preferences:
                self.app.preferences[prefname] = default
            adj = Gtk.Adjustment(value=self.app.preferences[prefname], lower=minv, upper=maxv, step_incr=step, page_incr=page)
            def cb(adj):
                self.app.preferences[prefname] = adj.get_value()
            adj.connect("value-changed", cb)
            setattr(self, "_"+propnam+"_adj", adj)
            spinbut = Gtk.SpinButton()
            spinbut.set_hexpand(True)
            spinbut.set_adjustment(adj)
            spinbut.set_numeric(True)
            grid.attach(label, 0, row, 1, 1)
            grid.attach(spinbut, 1, row, 1, 1)
            return row+1

        row = add_prop(
            self, "BPM", "bpm", grid, row,
            self.SCANLINE_DEFAULT_BPM, self.SCANLINE_MIN_BPM, self.SCANLINE_MAX_BPM,
            IMproVision.SCANLINE_PREF_BPM,
        )

        row = add_prop(
            self, "Loop beats", "beats", grid, row,
            self.SCANLINE_DEFAULT_BEATS, self.SCANLINE_MIN_BEATS, self.SCANLINE_MAX_BEATS,
            IMproVision.SCANLINE_PREF_BEATS,
        )

        row = add_prop(
            self, "Time Resolution (ms)", "timeres", grid, row,
            self.SCANLINE_DEFAULT_TIME_RES_MS, self.SCANLINE_MIN_TIME_RES_MS, self.SCANLINE_MAX_TIME_RES_MS,
            IMproVision.SCANLINE_PREF_TIMERES,
        )

        options.add(grid)
        options.show_all()

        self.pack_start(options, True, True, 0)

        self._overlay = IMproVision(app)
        self.app.doc.tdw.display_overlays.append(self._overlay)

        actions = {
            "IMproVisionTrigger": self._overlay.trigger_one,
            "IMproVisionStep": self._overlay.step_one,
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
