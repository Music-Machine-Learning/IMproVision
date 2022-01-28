# coding=utf-8
# Copyright (C) 2021 by Marco Melletti <mellotanica@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from lib.gibindings import Gtk
from lib import color
from .configurable import Configuration


def map_to_percent(minv, maxv, val):
    return (val - minv) / (maxv - minv)


class ThreeValueColorRange(dict):
    def __init__(
        self,
        refval: str,
        targetval: float,
        xref: str,
        xrange: (float, float),
        yrange: (float, float),
        targetdelta: float = 0.01,
    ):
        self.refval = refval
        self.target = targetval
        self.targetdelta = targetdelta
        self.xref = xref
        self.xrange = xrange
        self.yrange = yrange
        super().__init__(self, type=self.type)

    def __rv_from_index(self, index):
        for rn, rv in self.references.items():
            if rv == index:
                return rn
        raise AttributeError("unknown parameter index: {}".format(index))

    @property
    def type(self):
        return self["type"]

    @property
    def references(self):
        return self["references"]

    @property
    def refval(self):
        return self["refval"]

    @refval.setter
    def refval(self, val):
        self["refval"] = val
        self.refid = self.references[val]

    @property
    def target(self):
        return self["target"]

    @target.setter
    def target(self, val):
        self["target"] = val

    @property
    def targetdelta(self):
        return self["targetdelta"]

    @targetdelta.setter
    def targetdelta(self, val):
        self["targetdelta"] = val

    @property
    def xref(self):
        return self["xref"]

    @xref.setter
    def xref(self, val):
        self["xref"] = val
        self.xid = self.references[val]
        yval = self.__rv_from_index(3 - self.refid - self.xid)
        self["yref"] = yval
        self.yid = self.references[yval]

    @property
    def xmin(self):
        return self["xmin"]

    @xmin.setter
    def xmin(self, val):
        self["xmin"] = val

    @property
    def xmax(self):
        return self["xmax"]

    @xmax.setter
    def xmax(self, val):
        self["xmax"] = val

    @property
    def xrange(self):
        return self.xmin, self.xmax

    @xrange.setter
    def xrange(self, val):
        self["xmin"] = val[0]
        self["xmax"] = val[1]

    @property
    def yref(self):
        return self["yref"]

    @property
    def ymin(self):
        return self["ymin"]

    @ymin.setter
    def ymin(self, val):
        self["ymin"] = val

    @property
    def ymax(self):
        return self["ymax"]

    @ymax.setter
    def ymax(self, val):
        self["ymax"] = val

    @property
    def yrange(self):
        return self.ymin, self.ymax

    @yrange.setter
    def yrange(self, val):
        self["ymin"] = val[0]
        self["ymax"] = val[1]

    @staticmethod
    def from_dict(dict):
        for t in threevaluecolorrangetypes:
            if dict["type"] == t.type:
                return t(
                    refval=dict["refval"],
                    targetval=dict["target"],
                    xref=dict["xref"],
                    xrange=(dict["xmin"], dict["xmax"]),
                    yrange=(dict["ymin"], dict["ymax"]),
                    targetdelta=dict["targetdelta"],
                )
        raise AttributeError("unknown type '{}'".format(dict[type]))

    def in_range(self, color: (float, float, float)) -> (bool, float, float):
        """
        :param color: input color as a three value tuple
        :return (in_range, x_percent, y_percent)
        """
        x = color[self.xid]
        y = color[self.yid]
        if (
            abs(color[self.refid] - self.target) < self.targetdelta
            and self.xmin <= x <= self.xmax
            and self.ymin <= y <= self.ymax
        ):
            return (
                True,
                map_to_percent(self.xmin, self.xmax, x),
                map_to_percent(self.ymin, self.ymax, y),
            )
        return False, 0, 0

    def __str__(self):
        return "{}: {} (D: {}), {}: {}~{}, {}: {}~{}".format(
            self.refval,
            self.target,
            self.targetdelta,
            self.xref,
            self.xmin,
            self.xmax,
            self.yref,
            self.ymin,
            self.ymax,
        )

    def __repr__(self):
        return str(self)

    def center_color(self) -> color.UIColor:
        raise NotImplementedError

    def _get_val_mean(self, vid):
        if vid == self.refid:
            return self.target
        elif vid == self.xid:
            return self.xmin + (self.xmax - self.xmin) / 2
        elif vid == self.yid:
            return self.ymin + (self.ymax - self.ymin) / 2
        raise AttributeError("unknown parameter index '{}'".format(vid))


class HSVColorRange(ThreeValueColorRange):
    type = "HSV"
    references = {
        "hue": 0,
        "saturation": 1,
        "value": 2,
    }

    def in_range(self, color: color.UIColor) -> (bool, float, float):
        return super().in_range(color.get_hsv())

    @property
    def h(self):
        return self._get_val_mean(0)

    @property
    def s(self):
        return self._get_val_mean(1)

    @property
    def v(self):
        return self._get_val_mean(2)

    def center_color(self) -> color.UIColor:
        return color.HSVColor(self.h, self.s, self.v)


class RGBColorRange(ThreeValueColorRange):
    type = "RGB"
    references = {
        "red": 0,
        "green": 1,
        "blue": 2,
    }

    def in_range(self, color: color.UIColor) -> (bool, float, float):
        return super().in_range(color.get_rgb())

    @property
    def r(self):
        return self._get_val_mean(0)

    @property
    def g(self):
        return self._get_val_mean(1)

    @property
    def b(self):
        return self._get_val_mean(2)

    def center_color(self) -> color.UIColor:
        return color.RGBColor(self.r, self.g, self.b)


threevaluecolorrangetypes = [
    HSVColorRange,
    RGBColorRange,
]


class ColorRangeConfiguration(Configuration):
    def __init__(
        self,
        name: str,
        pref_path: str,
        dfl_val: ThreeValueColorRange,
        gui_setup_cb=None,
    ):
        super().__init__(name, pref_path, dfl_val, gui_setup_cb)
        self.__refs = {}
        for t in threevaluecolorrangetypes:
            for r in t.references.keys():
                self.__refs[r] = t

    def specific_setup(self, pref_path, value):
        pass

    def _get_gui_item(self):
        grid = Gtk.Grid()

        self.xref = Gtk.ComboBoxText()
        self.yref = Gtk.Label()

        def _update_xref(combo):
            xref = combo.get_active_text()
            v = self.get_value()
            if xref in v.references:
                v.xref = xref
                self._set_value(v)
                for r in self.get_value().references.keys():
                    if r == self.get_value().yref:
                        self.yref.set_text(r)

        def _update_refval(combo):
            ref = combo.get_active_text()
            if ref in self.__refs:
                oldv = self.get_value()
                newv = oldv
                if ref not in oldv.references:
                    for xr in self.__refs[ref].references.keys():
                        if xr != ref:
                            newv = self.__refs[ref](
                                ref,
                                oldv.target,
                                xr,
                                oldv.xrange,
                                oldv.yrange,
                                oldv.targetdelta,
                            )
                            break
                else:
                    newv.refval = ref
                    for xr in newv.references.keys():
                        if xr != ref:
                            newv.xref = xr
                            break
                self._set_value(newv)

                activeid = 0
                refs = list(self.get_value().references.keys())
                self.xref.remove_all()
                for r in range(len(refs)):
                    if refs[r] != self.get_value().refval:
                        self.xref.append_text(refs[r])
                        if refs[r] == self.get_value().xref:
                            activeid = r
                self.xref.set_active(activeid)

                _update_xref(self.xref)

        rvbox = Gtk.ComboBoxText()
        rvbox.connect("changed", _update_refval)
        activeid = 0
        refs = list(self.__refs.keys())
        for r in range(len(refs)):
            rvbox.append_text(refs[r])
            if refs[r] == self.get_value().refval:
                activeid = r
        rvbox.set_active(activeid)

        grid.attach(rvbox, 0, 0, 1, 1)

        def create_valspinner(cb, value):
            valspinner = Gtk.SpinButton()
            adj = Gtk.Adjustment(
                value=value,
                lower=0,
                upper=1,
                step_incr=0.01,
                page_incr=0.1,
            )

            adj.connect("value-changed", cb)
            valspinner.set_hexpand(True)
            valspinner.set_adjustment(adj)
            valspinner.set_digits(3)
            return valspinner

        def _target_changed(a):
            v = self.get_value()
            v.target = a.get_value()
            self._set_value(v)

        grid.attach(
            create_valspinner(_target_changed, self.get_value().target), 1, 0, 2, 1
        )

        self.xref.connect("changed", _update_xref)
        _update_refval(rvbox)

        grid.attach(self.xref, 0, 1, 1, 1)

        def _xmin_changed(a):
            v = self.get_value()
            v.xmin = a.get_value()
            self._set_value(v)

        def _xmax_changed(a):
            v = self.get_value()
            v.xmax = a.get_value()
            self._set_value(v)

        grid.attach(create_valspinner(_xmin_changed, self.get_value().xmin), 1, 1, 1, 1)
        grid.attach(create_valspinner(_xmax_changed, self.get_value().xmax), 2, 1, 1, 1)

        grid.attach(self.yref, 0, 2, 1, 1)

        def _ymin_changed(a):
            v = self.get_value()
            v.ymin = a.get_value()
            self._set_value(v)

        def _ymax_changed(a):
            v = self.get_value()
            v.ymax = a.get_value()
            self._set_value(v)

        grid.attach(create_valspinner(_ymin_changed, self.get_value().ymin), 1, 2, 1, 1)
        grid.attach(create_valspinner(_ymax_changed, self.get_value().ymax), 2, 2, 1, 1)

        return grid

    def get_value(self):
        return ThreeValueColorRange.from_dict(self._get_preference_value())
