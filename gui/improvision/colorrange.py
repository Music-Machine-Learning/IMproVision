# coding=utf-8
# Copyright (C) 2021 by Marco Melletti <mellotanica@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from lib.gibindings import Gtk
from lib import color
from lib.pycompat import xrange
import cairo
from .configurable import Configuration, SliderConfiguration
from gui.colors.sliders import (
    RGBRedSlider,
    RGBBlueSlider,
    RGBGreenSlider,
    HSVHueSlider,
    HSVSaturationSlider,
    HSVValueSlider,
)
from gui.colors import ColorManager
from gui.colors.adjbases import SliderColorAdjuster, ColorAdjusterWidget, ColorAdjuster
from gui.colors.uimisc import PRIMARY_ADJUSTERS_MIN_HEIGHT, PRIMARY_ADJUSTERS_MIN_WIDTH
from gui.colors.util import draw_marker_circle, clamp

from functools import partial
from lib.color import RGBColor, HSVColor


def map_to_percent(minv, maxv, val):
    if minv > maxv:
        return (val - maxv) / (minv - maxv)
    elif minv == maxv:
        return 0
    return (val - minv) / (maxv - minv)


def map_to_range(minv, maxv, pct):
    if minv > maxv:
        return maxv + (pct * (minv - maxv))
    elif minv == maxv:
        return minv
    return minv + (pct * (maxv - minv))


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
            if rv[0] == index:
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
        self.refid = self.references[val][0]

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
        self.xid = self.references[val][0]
        yval = self.__rv_from_index(3 - self.refid - self.xid)
        self["yref"] = yval
        self.yid = self.references[yval][0]

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
    base_color = HSVColor(0, 1, 1)
    references = {
        "hue": (0, HSVHueSlider),
        "saturation": (1, HSVSaturationSlider),
        "value": (2, HSVValueSlider),
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
    base_color = RGBColor(0, 0, 0)
    references = {
        "red": (0, RGBRedSlider),
        "green": (1, RGBGreenSlider),
        "blue": (2, RGBBlueSlider),
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


class ColorRangeManager(ColorManager):
    _DEFAULT_HIST = ["#000000"]

    def __init__(self, slider, ref, conf, prefs, datapath):
        super().__init__(prefs, datapath)
        self._children_mgrs = []
        self._slider = slider
        self._ref = ref
        self._conf = conf
        slider.set_color_manager(self)
        self.force_redraw = False

    def add_chld_mgr(self, chld_mgr):
        self._children_mgrs.append(chld_mgr)

    def set_color(self, color):
        super().set_color(color)
        v = self._conf.get_value()
        v[self._ref] = self._slider.get_bar_amount_for_color(color)
        self._conf._set_value(v)
        for ch in self._children_mgrs:
            pos = ch._slider.get_bar_amount_for_color(ch.color)
            ch.set_color(self.color)
            ch.set_color(ch._slider.get_color_for_bar_amount(pos))


class ColorRangeCube(ColorAdjusterWidget):
    """Planar slice through an HSV cube."""

    def __init__(self, conf):
        super().__init__()
        w = PRIMARY_ADJUSTERS_MIN_WIDTH
        h = PRIMARY_ADJUSTERS_MIN_HEIGHT
        self.set_size_request(w, h)
        self.set_hexpand(True)
        self._conf = conf

    def __get_faces(self):
        v = self._conf.get_value()
        x = v.xref[0]
        y = v.yref[0]
        return x, y

    def __get_central_color(self):
        return self._conf._color_mgrs["target"].get_color()

    def render_background_cb(self, cr, wd, ht, icon_border=None):
        v = self._conf.get_value()
        col = self.__get_central_color()
        b = icon_border
        if b is None:
            b = self.BORDER_WIDTH
        eff_wd = int(wd - 2 * b)
        eff_ht = int(ht - 2 * b)

        f1, f2 = self.__get_faces()

        step = max(1, int(eff_wd // 128))

        rect_x, rect_y = int(b) + 0.5, int(b) + 0.5
        rect_w, rect_h = int(eff_wd) - 1, int(eff_ht) - 1

        # Paint the central area offscreen
        cr.push_group()
        for x in xrange(0, eff_wd, step):
            # xmin <= amt <= xmax
            amt = x / eff_wd
            setattr(col, f1, map_to_range(v.xmin, v.xmax, amt))
            # ymin <= f2 <= ymax
            setattr(col, f2, v.ymax)
            lg = cairo.LinearGradient(b + x, b, b + x, b + eff_ht)
            lg.add_color_stop_rgb(*([0.0] + list(col.get_rgb())))
            setattr(col, f2, v.ymin)
            lg.add_color_stop_rgb(*([1.0] + list(col.get_rgb())))
            cr.rectangle(b + x, b, step, eff_ht)
            cr.set_source(lg)
            cr.fill()
        slice_patt = cr.pop_group()

        # Tango-like outline
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        cr.rectangle(rect_x, rect_y, rect_w, rect_h)
        cr.set_line_width(self.OUTLINE_WIDTH)
        cr.set_source_rgba(*self.OUTLINE_RGBA)
        cr.stroke()

        # The main area
        cr.set_source(slice_patt)
        cr.paint()

        # Tango-like highlight over the top
        cr.rectangle(rect_x, rect_y, rect_w, rect_h)
        cr.set_line_width(self.EDGE_HIGHLIGHT_WIDTH)
        cr.set_source_rgba(*self.EDGE_HIGHLIGHT_RGBA)
        cr.stroke()

    def get_background_validity(self):
        col = self.__get_central_color()
        ccol = self.get_managed_color()
        v = self._conf.get_value()
        val = (
            f"{repr(col)}{repr(ccol)}{v.refval[0]}{v.xref[0]}{v.yref[0]}",
            v.xmin,
            v.xmax,
            v.ymin,
            v.ymax,
        )
        return val

    def get_color_at_position(self, x, y):
        alloc = self.get_allocation()
        v = self._conf.get_value()
        b = self.BORDER_WIDTH
        wd = alloc.width
        ht = alloc.height
        eff_wd = wd - 2 * b
        eff_ht = ht - 2 * b
        f1_amt = clamp((x - b) / eff_wd, 0, 1)
        f2_amt = clamp((y - b) / eff_ht, 0, 1)
        col = self.__get_central_color()
        f1, f2 = self.__get_faces()
        f2_amt = 1.0 - f2_amt
        setattr(col, f1, map_to_range(v.xmin, v.xmax, f1_amt))
        setattr(col, f2, map_to_range(v.ymin, v.ymax, f2_amt))
        return col

    def get_position_for_color(self, col):
        v = self._conf.get_value()
        _, f1_amt, f2_amt = v.in_range(col)
        f2_amt = 1 - f2_amt
        alloc = self.get_allocation()
        b = self.BORDER_WIDTH
        wd = alloc.width
        ht = alloc.height
        eff_wd = wd - 2 * b
        eff_ht = ht - 2 * b
        x = b + f1_amt * eff_wd
        y = b + f2_amt * eff_ht
        return x, y

    def paint_foreground_cb(self, cr, wd, ht):
        inrange, _, _ = self._conf.get_value().in_range(self.get_managed_color())
        x, y = self.get_position_for_color(self.get_managed_color())
        print(f"paint foreground: x {x}, y {y}")
        if inrange:
            draw_marker_circle(cr, x, y)


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

        self._loc_prefs = {"target": {}, "xmin": {}, "xmax": {}, "ymin": {}, "ymax": {}}
        self._color_mgrs = {}
        self._color_sliders = {}

        from gui.application import get_app

        app = get_app()
        self._cube = ColorRangeCube(self)
        self._cube.color_manager = app.brush_color_manager

    def specific_setup(self, pref_path, value):
        v = self.get_value()
        self._color_sliders["target"] = v.references[v.refval][1]()
        self._color_sliders["xmin"] = v.references[v.xref][1]()
        self._color_sliders["xmax"] = v.references[v.xref][1]()
        self._color_sliders["ymin"] = v.references[v.yref][1]()
        self._color_sliders["ymax"] = v.references[v.yref][1]()

        for m in self._loc_prefs:
            self._color_mgrs[m] = ColorRangeManager(
                self._color_sliders[m], m, self, self._loc_prefs[m], ""
            )
            self._color_sliders[m].set_hexpand(True)
            self._color_mgrs[m].add_adjuster(self._cube)

        for m, mgr in self._color_mgrs.items():
            if m != "target":
                self._color_mgrs["target"].add_chld_mgr(mgr)
            self._color_sliders[m].set_managed_color(v.base_color)

        for m, slider in self._color_sliders.items():
            slider.set_managed_color(slider.get_color_for_bar_amount(value[m]))

    def _get_gui_item(self):

        grid = Gtk.Grid()

        self.xref = Gtk.ComboBoxText()
        self.yref = Gtk.Label()

        def _setup_slider(slider, settype: SliderColorAdjuster, reset_color=None):
            pos = slider.get_bar_amount_for_color(slider.managed_color)

            def forced_get_background_validity(slider):
                if slider.color_manager.force_redraw:
                    col = slider.get_managed_color()
                    if col.r > 0:
                        col = RGBColor(0, col.g, col.b)
                    else:
                        col = RGBColor(255, col.g, col.b)
                    slider.color_manager.force_redraw = False
                    return repr(col)
                return SliderColorAdjuster.get_background_validity(slider)

            setattr(
                slider,
                "get_background_validity",
                partial(forced_get_background_validity, slider),
            )
            setattr(
                slider,
                "get_color_for_bar_amount",
                partial(settype.get_color_for_bar_amount, slider),
            )
            setattr(
                slider,
                "get_bar_amount_for_color",
                partial(settype.get_bar_amount_for_color, slider),
            )
            setattr(slider, "samples", settype.samples)
            slider.color_manager.force_redraw = True

            if reset_color is not None:
                slider.color_manager.set_color(reset_color)
            newcol = slider.get_color_for_bar_amount(pos)
            slider.color_manager.set_color(newcol)

        def _update_xref(combo):
            xref = combo.get_active_text()
            v = self.get_value()
            if xref in v.references:
                v.xref = xref
                self._set_value(v)
                v = self.get_value()

                for r in v.references.keys():
                    if r == v.yref:
                        self.yref.set_text(r)

            _setup_slider(
                self._color_sliders["xmin"],
                v.references[v.xref][1],
                self._color_sliders["target"].managed_color,
            )
            _setup_slider(
                self._color_sliders["xmax"],
                v.references[v.xref][1],
                self._color_sliders["target"].managed_color,
            )
            _setup_slider(
                self._color_sliders["ymin"],
                v.references[v.yref][1],
                self._color_sliders["target"].managed_color,
            )
            _setup_slider(
                self._color_sliders["ymax"],
                v.references[v.yref][1],
                self._color_sliders["target"].managed_color,
            )

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
                v = self.get_value()

                activeid = 0
                refs = list(v.references.keys())
                self.xref.remove_all()
                for r in range(len(refs)):
                    if refs[r] != v.refval:
                        self.xref.append_text(refs[r])
                        if refs[r] == v.xref:
                            activeid = r
                self.xref.set_active(activeid)

                _setup_slider(
                    self._color_sliders["target"],
                    v.references[v.refval][1],
                    v.base_color,
                )

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

        grid.attach(self._color_sliders["target"], 1, 0, 2, 1)

        self.xref.connect("changed", _update_xref)
        _update_refval(rvbox)

        grid.attach(self.xref, 0, 1, 1, 1)

        grid.attach(self._color_sliders["xmin"], 1, 1, 1, 1)
        grid.attach(self._color_sliders["xmax"], 2, 1, 1, 1)

        grid.attach(self.yref, 0, 2, 1, 1)

        grid.attach(self._color_sliders["ymin"], 1, 2, 1, 1)
        grid.attach(self._color_sliders["ymax"], 2, 2, 1, 1)

        grid.attach(self._cube, 1, 3, 2, 3)

        return grid

    def get_value(self):
        return ThreeValueColorRange.from_dict(self._get_preference_value())
