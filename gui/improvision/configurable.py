# coding=utf-8
# Copyright (C) 2021 by Marco Melletti <mellotanica@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


from lib.gibindings import Gtk
from lib.gettext import gettext as _
from gui.colors.adjbases import SliderColorAdjuster, PREFS_KEY_CURRENT_COLOR
from gui.colors import ColorManager


class Configuration:
    def __init__(self, name: str, pref_path: str, dfl_val, gui_setup_cb=None):
        from gui.application import get_app

        self.app = get_app()
        self.name = name
        self._dfl_val = dfl_val
        self.gui_setup_cb = gui_setup_cb
        self.pref_name = pref_path
        self._label = None
        self._changer = None

    def setup_preference(self, pref_path):
        if pref_path[-1] != "-":
            pref_path += "-"
        self.pref_path = pref_path + self.pref_name

        if self.pref_path not in self.app.preferences:
            self.app.preferences[self.pref_path] = self._dfl_val

        self.specific_setup(self.pref_path, self.app.preferences[self.pref_path])

    def _get_preference_value(self):
        return self.app.preferences[self.pref_path]

    def _set_value(self, val):
        self.app.preferences[self.pref_path] = val

    def remove(self):
        if self._label is not None:
            self._label.destroy()
        if self._changer is not None:
            self._changer.destroy()

    def add_to_grid(self, grid, row):
        self._label = Gtk.Label()
        self._label.set_text(_(self.name + ":"))
        self._label.set_alignment(1.0, 0.5)
        self._changer = self._get_gui_item()
        if self.gui_setup_cb is not None:
            self.gui_setup_cb(self._changer)
        grid.attach(self._label, 0, row, 1, 1)
        grid.attach(self._changer, 1, row, 1, 1)
        return row + 1

    def specific_setup(self, pref_path, value):
        raise NotImplementedError

    def _get_gui_item(self):
        raise NotImplementedError

    def get_value(self):
        raise NotImplementedError


class BoolConfiguration(Configuration):
    def __init__(self, name: str, pref_path: str, default_val: bool):
        super().__init__(name, pref_path, default_val)
        self.toggle = None
        self.btn_label = Gtk.Label()
        self.toggle = Gtk.ToggleButton()
        self.toggle.add(self.btn_label)

    def specific_setup(self, pref_path, value):
        self.toggle.set_active(value)

        def _value_changed_cb(t):
            self._set_value(self.get_value())
            if self.get_value():
                self.btn_label.set_text("On")
            else:
                self.btn_label.set_text("Off")

        self.toggle.connect("toggled", _value_changed_cb)
        _value_changed_cb(self.toggle)

    def get_value(self):
        return self.toggle.get_active()

    def _get_gui_item(self):
        return self.toggle


class NumericConfiguration(Configuration):
    def __init__(
        self,
        name: str,
        pref_path: str,
        gui_type: type,
        default_val,
        lower,
        upper,
        step_incr=1,
        page_incr=10,
        gui_setup_cb=None,
    ):
        super().__init__(name, pref_path, default_val, gui_setup_cb)
        self.gui_type = gui_type
        self._lower = lower
        self._upper = upper
        self._step = step_incr
        self._page = page_incr
        self.adj = None

    def specific_setup(self, pref_path, value):
        self.adj = Gtk.Adjustment(
            value=value,
            lower=self._lower,
            upper=self._upper,
            step_incr=self._step,
            page_incr=self._page,
        )

        def _value_changed_cb(a):
            self._set_value(self.get_value())

        self.adj.connect("value-changed", _value_changed_cb)

    def get_value(self):
        return self.adj.get_value()

    def _get_gui_item(self):
        changer = self.gui_type()
        changer.set_hexpand(True)
        changer.set_adjustment(self.adj)
        return changer


class SliderConfiguration(Configuration):
    def __init__(
        self,
        name,
        pref_path,
        default_val,
        slider: SliderColorAdjuster,
        color_manager=None,
    ):
        Configuration.__init__(
            self,
            name,
            pref_path,
            default_val,
        )
        self.slider = slider
        self._loc_prefs = {
            PREFS_KEY_CURRENT_COLOR: self.slider.get_color_for_bar_amount(default_val)
        }
        self.color_manager = color_manager
        setattr(self.slider, "set_managed_color", self.set_managed_color)

    def set_managed_color(self, color):
        SliderColorAdjuster.set_managed_color(self.slider, color)
        self._set_value(self.get_value())

    def get_value(self):
        return self.slider.get_bar_amount_for_color(self.slider.managed_color)

    def specific_setup(self, pref_path, value):
        if self.color_manager is None:
            self.color_manager = ColorManager(
                self._loc_prefs,
                "",
            )
        self.slider.set_color_manager(self.color_manager)
        self.set_managed_color(self.slider.get_color_for_bar_amount(value))

    def _get_gui_item(self):
        return self.slider


class ListConfiguration(Configuration):
    # items can be both a list or a dict, if it's the latter, the keys will be displayed and the values will be used internally
    def __init__(
        self, name: str, pref_path: str, default_val, items, gui_setup_cb=None
    ):
        super().__init__(name, pref_path, default_val, gui_setup_cb)

        if default_val not in items:
            raise AttributeError(
                "default value '{}' not in item list: {}".format(default_val, items)
            )

        self._items = items

    def specific_setup(self, pref_path, value):
        pass

    def get_value(self):
        if isinstance(self._items, dict):
            return self._items[self._get_preference_value()]
        return self._get_preference_value()

    def _get_gui_item(self):
        def _value_changed_cb(combo):
            self._set_value(combo.get_active_text())

        box = Gtk.ComboBoxText()
        items = self._items
        box.connect("changed", _value_changed_cb)
        if isinstance(self._items, dict):
            items = list(self._items.keys())
        for i in items:
            box.append_text(i)

        try:
            box.set_active(items.index(self._get_preference_value()))
        except ValueError:
            box.set_active(items.index(self._dfl_val))

        return box


class Configurable(object):
    """
    a configurable item is something that will hold a mix of configurations and other configurable items

    these isntances are used to group features together and to automatically generate preference paths
    """

    def __init__(
        self,
        label: str = None,
        name: str = None,
        confmap: {str: Configuration} = {},
        subconfigs=[],
        expanded=False,
        removable=False,
    ):
        """
        :param label: if not None, this configurable contents will be inside an expander labeled with label
        :param name: name will be used to generate the inner configurations paths inside main preferences dict
        :param confmap: configurations associated with this instance
        :param subconfigs: nested configurable items
        :param expanded: if True, start with expander open (only meaningful if label is not None)
        :param removable: if True, add a button that removes the whole configurable object if pressed
        """
        self._parent = None
        self._subid = ""
        self.label = None
        self.name = None
        self.removable = removable
        self._confmap = {}
        self._subconfigs = []
        self.expanded = expanded
        self.setup_configurable(label, name, confmap, subconfigs)

    def setup_configurable(
        self,
        label: str = None,
        name: str = None,
        confmap: {str: Configuration} = None,
        subconfigs=None,
        reset_confmap: bool = False,
    ):
        if label is not None:
            self.label = label
        if name is not None:
            self.name = name

        if subconfigs is not None:
            if subconfigs is not None and type(subconfigs) is not list:
                self._subconfigs = [subconfigs]
            else:
                self._subconfigs = subconfigs
        for c in range(len(self._subconfigs)):
            self._subconfigs[c]._parent = self
            if len(self._subconfigs) > 1:
                self._subconfigs[c]._subid = str(c)

        if confmap is not None:
            if reset_confmap:
                self._confmap = confmap
            else:
                self._confmap.update(confmap)

        self._remove_btn = None
        self._expander = None

    def add_configurations(self, confmap: {str: Configuration}):
        if confmap is not None:
            self._confmap.update(confmap)

    def get_prefpath(self):
        ppath = ""
        if self._parent is not None:
            ppath = self._parent.get_prefpath()
            if len(ppath) > 0 and ppath[-1] != "-":
                ppath += "-"
        if self.name is not None:
            ppath += self.name
        return ppath + self._subid

    def __getattr__(self, item):
        cm = object.__getattribute__(self, "_confmap")
        if item in cm:
            return cm[item].get_value()
        raise AttributeError

    def remove(self, _):
        for c in self._confmap.values():
            c.remove()

        for s in self._subconfigs:
            s.remove(_)

        if self._remove_btn is not None:
            self._remove_btn.destroy()
        if self._expander is not None:
            self._expander.destroy()

    def add_to_grid(self, grid, row):
        for c in self._confmap.values():
            c.setup_preference(self.get_prefpath())

        outgrid = grid
        outrow = row
        if self.label is not None:
            self._expander = Gtk.Expander(label=self.label)
            self._expander.set_expanded(self.expanded)
            outgrid = Gtk.Grid()
            self._expander.add(outgrid)
            grid.attach(self._expander, 1, row, 1, 1)
            outrow = 0
            row += 1

        if self.removable:
            self._remove_btn = Gtk.Button(label="Remove")
            self._remove_btn.connect("clicked", self.remove)
            outgrid.attach(self._remove_btn, 0, outrow, 2, 1)
            outrow += 1

        for c in self._confmap.values():
            outrow = c.add_to_grid(outgrid, outrow)

        for sc in self._subconfigs:
            outrow = sc.add_to_grid(outgrid, outrow)

        if self.label is not None:
            return row
        return outrow
