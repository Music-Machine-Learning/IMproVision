from lib.gibindings import Gtk
from lib.gettext import gettext as _


class Configuration:
    def __init__(
            self,
            name: str,
            pref_path: str,
            gui_setup_cb = None,
    ):
        from gui.application import get_app
        self.app = get_app()
        self.name = name
        self.gui_setup_cb = gui_setup_cb
        self.pref_name = pref_path

    def specific_setup(self, pref_path):
        raise NotImplementedError

    def setup_preference(self, pref_path):
        if pref_path[-1] != '-':
            pref_path += '-'
        pref_path += self.pref_name

        self.specific_setup(pref_path)

    def add_to_grid(self, grid, row):
        label = Gtk.Label()
        label.set_text(_(self.name + ":"))
        label.set_alignment(1.0, 0.5)
        changer = self._get_gui_item()
        if self.gui_setup_cb is not None:
            self.gui_setup_cb(changer)
        grid.attach(label, 0, row, 1, 1)
        grid.attach(changer, 1, row, 1, 1)
        return row + 1

    def _get_gui_item(self):
        raise NotImplementedError

    def get_value(self):
        raise NotImplementedError


class NumericConfiguration(Configuration):
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
        super().__init__(name, pref_path, gui_setup_cb)
        self.gui_type = gui_type
        self._dfl_val = default_val
        self._lower = lower
        self._upper = upper
        self._step = step_incr
        self._page = page_incr
        self.adj = None

    def specific_setup(self, pref_path):
        if pref_path not in self.app.preferences:
            self.app.preferences[pref_path] = self._dfl_val

        self.adj = Gtk.Adjustment(value=self.app.preferences[pref_path],
                                  lower=self._lower,
                                  upper=self._upper,
                                  step_incr=self._step,
                                  page_incr=self._page)

        def _value_changed_cb(a):
            self.app.preferences[pref_path] = self.adj.get_value()

        self.adj.connect("value-changed", _value_changed_cb)

    def get_value(self):
        return self.adj.get_value()

    def _get_gui_item(self):
        changer = self.gui_type()
        changer.set_hexpand(True)
        changer.set_adjustment(self.adj)
        return changer


class Configurable(object):
    def __init__(self, label: str = None, name: str = None, confmap: {str: Configuration} = {}, subconfigs = [], expanded=False):
        self._parent = None
        self.label = None
        self.name = None
        self.confmap = {}
        self._subconfigs = []
        self.expanded = expanded
        self.setup_configurable(label, name, confmap, subconfigs)

    def setup_configurable(self, label: str = None, name: str = None, confmap : {str: Configuration} = None, subconfigs = None):
        if label is not None:
            self.label = label
        if name is not None:
            self.name = name

        if subconfigs is not None:
            if subconfigs is not None and type(subconfigs) is not list:
                self._subconfigs = [subconfigs]
            else:
                self._subconfigs = subconfigs
        for c in self._subconfigs:
            c._parent = self

        if confmap is not None:
            self._confmap = confmap

    def get_prefpath(self):
        ppath = ''
        if self._parent is not None:
            ppath = self._parent.get_prefpath()
            if len(ppath) > 0 and ppath[-1] != '-':
                ppath += '-'
        if self.name is not None:
            ppath += self.name
        return ppath

    def __getattr__(self, item):
        cm = object.__getattribute__(self, "_confmap")
        if item in cm:
            return cm[item].get_value()
        raise AttributeError

    def add_to_grid(self, grid, row):
        for c in self._confmap.values():
            c.setup_preference(self.get_prefpath())

        outgrid = grid
        outrow = row
        if self.label is not None:
            expander = Gtk.Expander(label=self.label)
            expander.set_expanded(self.expanded)
            outgrid = Gtk.Grid()
            expander.add(outgrid)
            grid.attach(expander, 1, row, 1, 1)
            outrow = 0
            row += 1

        for c in self._confmap.values():
            outrow = c.add_to_grid(outgrid, outrow)

        for sc in self._subconfigs:
            outrow = sc.add_to_grid(outgrid, outrow)

        if self.label is not None:
            return row
        return outrow