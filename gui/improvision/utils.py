# coding=utf-8
# Copyright (C) 2022 by Marco Melletti <mellotanica@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


def map_to_percent(minv, maxv, val):
    """
    map a value inside a range and return the percentual representatio
    :param minv: range limit (better if lower)
    :param maxv: range limit (better if higher)
    :param val: value in range
    :return percentage representing position of val in range (0~1)
    """
    if minv > maxv:
        return (val - maxv) / (minv - maxv)
    elif minv == maxv:
        return 0
    return (val - minv) / (maxv - minv)


def map_to_range(minv, maxv, pct):
    """
    get the scaled value from a specific range relative to the input percentage
    :param minv: range limit (better if lower)
    :param maxv: range limit (better if higher)
    :param pct: percentual value to be mapped in range
    :return value in range scale relative to the input percentage
    """
    if minv > maxv:
        return maxv + (pct * (minv - maxv))
    elif minv == maxv:
        return minv
    return minv + (pct * (maxv - minv))
