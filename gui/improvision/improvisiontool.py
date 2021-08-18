from lib.gibindings import Gtk

from gui.toolstack import SizedVBoxToolWidget, TOOL_WIDGET_NATURAL_HEIGHT_SHORT
from lib.gettext import gettext as _
from gui.widgets import inline_toolbar
from .improvision import IMproVision
from .configurable import Configurable

class IMproVisionTool (SizedVBoxToolWidget, Configurable):
    """Dockable panel showing options for IMproVision
    """

    ## Class constants

    SIZED_VBOX_NATURAL_HEIGHT = TOOL_WIDGET_NATURAL_HEIGHT_SHORT

    tool_widget_icon_name = "improvision-group-symbolic"
    tool_widget_title = _("IMproVision")
    tool_widget_description = _("IMproVision related configurations and activators")

    __gtype_name__ = 'MyPaintIMproVisionTool'

    def __init__(self):
        SizedVBoxToolWidget.__init__(self)
        from gui.application import get_app
        self.app = get_app()

        self._overlay = IMproVision(self.app)
        self.app.doc.tdw.display_overlays.append(self._overlay)

        Configurable.__init__(self, subconfigs=self._overlay)

        toolbar = inline_toolbar(
            self.app, [
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

        self.add_to_grid(grid, 0)

        options.add(grid)
        options.show_all()

        self.pack_start(options, True, True, 0)

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
