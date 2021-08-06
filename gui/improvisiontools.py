from lib.gibindings import Gtk
from . import widgets

from .toolstack import SizedVBoxToolWidget, TOOL_WIDGET_NATURAL_HEIGHT_SHORT
from lib.gettext import gettext as _
from .widgets import inline_toolbar

class IMproVisionTool (SizedVBoxToolWidget):
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
        app = get_app()
        self.app = app
        toolbar = inline_toolbar(
            app, [
                ("IMproVisionTrigger", None),
                ("IMproVisionLoop", None),
                ("IMproVisionStop", None),
            ])

        self.pack_start(toolbar, False, True, 0)
