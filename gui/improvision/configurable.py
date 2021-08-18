from lib.gibindings import Gtk
from lib.gettext import gettext as _


class Configuration:
    def __init__(
            self,
            name: str,
            pref_path: str,
            gui_type: type,
            default_val,
            lower,
            upper,
            step_incr = 1,
            page_incr = 10,
            gui_setup_cb = None,
    ):
        from gui.application import get_app
        self.app = get_app()
        self.name = name
        self.gui_type = gui_type
        self.gui_setup_cb = gui_setup_cb
        if pref_path not in self.app.preferences:
            self.app.preferences[pref_path] = default_val
        self.adj = Gtk.Adjustment(value=self.app.preferences[pref_path], lower=lower, upper=upper, step_incr=step_incr,
                             page_incr=page_incr)

        def _value_changed_cb(a):
            self.app.preferences[pref_path] = self.adj.get_value()

        self.adj.connect("value-changed", _value_changed_cb)

    def add_to_grid(self, grid, row):
        label = Gtk.Label()
        label.set_text(_(self.name + ":"))
        label.set_alignment(1.0, 0.5)
        changer = self.gui_type()
        changer.set_hexpand(True)
        changer.set_adjustment(self.adj)
        if self.gui_setup_cb is not None:
            self.gui_setup_cb(changer)
        grid.attach(label, 0, row, 1, 1)
        grid.attach(changer, 1, row, 1, 1)
        return row + 1

    def get_value(self):
        return self.adj.get_value()


class Configurable(object):
    def __init__(self, name: str = None, confmap: {str: Configuration} = {}, subconfigs=None):
        self._parent = None
        self.name = name
        self.set_confmap(confmap)
        self.set_subconfigs(subconfigs)

    def set_confmap(self, confmap: {str: Configuration}):
        self._confmap = confmap

    def set_subconfigs(self, subconfigs):
        if subconfigs is not None and type(subconfigs) is not list:
            self._subconfigs = [subconfigs]
        elif subconfigs is None:
            self._subconfigs = []
        else:
            self._subconfigs = subconfigs
        for c in self._subconfigs:
            c._parent = self

    def set_name(self, name):
        self.name = name

    def __getattr__(self, item):
        cm = object.__getattribute__(self, "_confmap")
        if item in cm:
            return cm[item].get_value()
        raise AttributeError

    def add_to_grid(self, grid, row):
        if self.name is not None:
            label = Gtk.Label()
            label.set_text(_(self.name + ":"))
            label.set_alignment(1.0, 1.0)

            grid.attach(label, 0, row, 1, 1)
            row += 1

        for c in self._confmap.values():
            row = c.add_to_grid(grid, row)

        for sc in self._subconfigs:
            row = sc.add_to_grid(grid, row)

        return row
