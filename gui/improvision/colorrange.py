# coding=utf-8
# Copyright (C) 2021 by Marco Melletti <mellotanica@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from lib import color


def map_to_percent(minv, maxv, val):
    return (val - minv) / (maxv - minv)


class ThreeValueColorRange(dict):
    def __init__(self, type: str, references: {str: id}, refval: str, targetval: float, xref: str, xrange: (float, float), yrange: (float, float), targetdelta: float = 0.01):
        self.type = type
        self.references = references
        self.refval = refval
        self.refid = self.references[refval]
        self.target = targetval
        self.targetdelta = targetdelta
        self.xref = xref
        self.xid = self.references[xref]
        self.xmin = xrange[0]
        self.xmax = xrange[1]
        self.yid = 3 - self.refid - self.xid
        self.yref = self.__rv_from_index(self.yid)
        self.ymin = yrange[0]
        self.ymax = yrange[1]
        super().__init__(self, type=self.type, refval=self.refval, target=self.target, targetdelta=self.targetdelta, xref=self.xref, xmin=self.xmin, xmax=self.xmax, yref=self.yref, ymin=self.ymin, ymax=self.ymax)

    def __rv_from_index(self, index):
        for rn, rv in self.references.items():
            if rv == index:
                return rn
        raise AttributeError("unknown parameter index: {}".format(index))

    @staticmethod
    def from_dict(dict):
        for t in threevaluecolorrangetypes:
            if dict['type'] == t.type:
                return t(
                    refval=dict['refval'],
                    targetval=dict['target'],
                    xref=dict['xref'],
                    xrange=(dict['xmin'], dict['xmax']),
                    yrange=(dict['ymin'], dict['ymax']),
                    targetdelta=dict['targetdelta'])
        raise AttributeError("unknown type '{}'".format(dict[type]))

    def in_range(self, color: (float, float, float)) -> (bool, float, float):
        """
        :param color: input color as a three value tuple
        :return (in_range, x_percent, y_percent)
        """
        x = color[self.xid]
        y = color[self.yid]
        if abs(color[self.refid] - self.target) < self.targetdelta \
                and self.xmin <= x <= self.xmax \
                and self.ymin <= y <= self.ymax:
            return True, map_to_percent(self.xmin, self.xmax, x), map_to_percent(self.ymin, self.ymax, y)
        return False, 0, 0

    def __str__(self):
        return "{}: {} (D: {}), {}: {}~{}, {}: {}~{}".format(self.refval, self.target, self.targetdelta,
                                                             self.xref, self.xmin, self.xmax,
                                                             self.yref, self.ymin, self.ymax)

    def __repr__(self):
        return str(self)


class HSVColorRange(ThreeValueColorRange):
    type = 'HSV'
    references = {
        'hue': 0,
        'saturation': 1,
        'value': 2,
    }

    def __init__(self, refval: str, targetval: float, xref: str, xrange: (float, float), yrange: (float, float), targetdelta: float = 0.01):
        super().__init__(self.type, self.references, refval, targetval, xref, xrange, yrange, targetdelta)

    def in_range(self, color: color.UIColor) -> (bool, float, float):
        return super().in_range(color.get_hsv())


class RGBColorRange(ThreeValueColorRange):
    type = 'RGB'
    references = {
        'red': 0,
        'green': 1,
        'blue': 2,
    }

    def __init__(self, refval: str, targetval: float, xref: str, xrange: (float, float), yrange: (float, float), targetdelta: float = 0.01):
        super().__init__(self.type, self.references, refval, targetval, xref, xrange, yrange, targetdelta)

    def in_range(self, color: color.UIColor) -> (bool, float, float):
        return super().in_range(color.get_rgb())


threevaluecolorrangetypes = [
    HSVColorRange,
    RGBColorRange,
]
