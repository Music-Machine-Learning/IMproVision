from lib.gibindings import Gtk
from . import widgets


def _new_improvision_menu():
    from gui.application import get_app
    app = get_app()
    menu = Gtk.Menu()
    action_names = [
        "IMproVisionStartRead",
    ]
    for an in action_names:
        if an is None:
            item = Gtk.SeparatorMenuItem()
        else:
            action = app.find_action(an)
            item = Gtk.MenuItem()
            item.set_use_action_appearance(True)
            item.set_related_action(action)
        menu.append(item)
    return menu


class IMproVisionToolItem (widgets.MenuButtonToolItem):
    """Toolbar item for IMproVision settings

    This is instantiated by the app's UIManager using a FactoryAction which
    must be named "IMproVision" (see factoryaction.py).
    """

    __gtype_name__ = 'MyPaintIMproVisionToolItem'

    def __init__(self):
        widgets.MenuButtonToolItem.__init__(self)
        self.menu = _new_improvision_menu()