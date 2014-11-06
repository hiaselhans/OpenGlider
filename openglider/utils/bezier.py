#! /usr/bin/python2
# -*- coding: utf-8; -*-
#
# (c) 2013 booya (http://booya.at)
#
# This file is part of the OpenGlider project.
#
# OpenGlider is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# OpenGlider is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OpenGlider.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import division


import numpy
import scipy.interpolate
from scipy.optimize import bisect as findroot

from openglider.utils.cache import cached_property, CachedObject
from openglider.vector import mirror2D_x, norm, HashedList

__ALL = ['BezierCurve']


class BezierCurve(HashedList):
    def __init__(self, controlpoints=None):
        """
        Bezier Curve represantative
        http://en.wikipedia.org/wiki/Bezier_curve#Generalization
        """
        #self._BezierBase = self._BezierFunction = self._controlpoints = None
        super(BezierCurve, self).__init__(controlpoints)

    def __json__(self):
        return {'controlpoints': [p.tolist() for p in self.controlpoints]}

    def __call__(self, value):
        i_end = len(self._data)
        j_end = len(self._data[0])
        out_arr = numpy.zeros([j_end])
        for i in range(i_end):
            fac = _bernsteinbase(i_end, i, value)
            for j in range(j_end):
                out_arr[j] += fac * self._data[i][j]
        return out_arr


    def call(self, value):
        num = len(self.controlpoints)
        dim = len(self.controlpoints[0])
        if 0 <= value <= 1:
            val = numpy.zeros(dim)
            for i, point in enumerate(self.controlpoints):
                fakt = choose(i - 1, num) * (value ** num) * ((1 - value) ** (i - 1 - num))
                #fakt = base[i](value)
                try:
                    val += point * fakt
                except:
                    raise Exception("fehler: {}, {}, {}".format(val.__class__, point.__class__, fakt.__class__))
            return val
        else:
            ValueError("value must be in the range (0,1) for xvalues use xpoint-function")

    @property
    def numpoints(self):
        try:
            return len(self.controlpoints)
        except TypeError:
            return 0

    @numpoints.setter
    def numpoints(self, num_ctrl, num_points=50):
        if not num_ctrl == self.numpoints:
            base = bernsteinbase(num_ctrl)
            self._controlpoints = fitbezier([self(i) for i in numpy.linspace(0, 1, num_points)], base)

    #@cached_property('self')
    @property
    def _bezierbase(self):
        return bernsteinbase(len(self.controlpoints))

    @property
    def controlpoints(self):
           return self._data

    @controlpoints.setter
    def controlpoints(self, points):
       self.data = points

    def xpoint(self, x):
        root = findroot(lambda x2: self.__call__(x2)[0] - x, 0, 1)
        return self.__call__(root)

    def ypoint(self, y):
        root = findroot(lambda y2: self.__call__(y2)[1] - y, 0, 1)
        return self.__call__(root)

    @classmethod
    def fit(cls, data, numpoints=3):
        bezier = cls([[0,0] for __ in range(numpoints)])
        bezier.controlpoints = numpy.array(fitbezier(data, bezier._bezierbase))
        return bezier

    def interpolation(self, num=100):
        x, y = self.get_sequence(num).T
        return scipy.interpolate.interp1d(x, y)

    def interpolate_3d(self, num=100, which=0, bounds_error=False):
        """
        Return scipy interpolation
        """
        data = self.get_sequence(num).T
        return scipy.interpolate.interp1d(data[which], data, bounds_error=bounds_error)

    def get_sequence(self, num=50):
        data = []
        for i in range(num):
            point = self(i / (num - 1))
            data.append(point)
        return numpy.array(data)

    def get_length(self, num):
        seq = self.get_sequence(num=num)
        out = 0.
        for i, s in enumerate(seq[1:]):
            out += norm(s - seq[i])
        return(out)


class SymmetricBezier(BezierCurve):
    def __init__(self, controlpoints=None, mirror=None):
        self._mirror = mirror or mirror2D_x
        super(SymmetricBezier, self).__init__(controlpoints=controlpoints)

    @property
    def controlpoints(self):
        return self._data[self.numpoints:]

    @controlpoints.setter
    def controlpoints(self, controlpoints):
        self._data = numpy.array(self._mirror(controlpoints)[::-1] + controlpoints)

    @property
    def numpoints(self):
        return len(self._data) // 2

    @numpoints.setter
    def numpoints(self, num_ctrl, num_points=50):
        if not num_ctrl == self.numpoints:
            num_ctrl *= 2
            base = bernsteinbase(num_ctrl)
            self._data = fitbezier([self(i) for i in numpy.linspace(0, 1, num_points)], base)


##############################FUNCTIONS

def _bernsteinbase(d, n, x):
    return choose(d - 1, n) * (x ** n) * ((1 - x) ** (d - 1 - n))

def bernsteinbase(d):
    def bsf(n):
        return lambda x: _bernsteinbase(d, n, x)

    return [bsf(i) for i in range(d)]

def choose(n, k):
    if 0 <= k <= n:
        ntok = 1
        ktok = 1
        for t in xrange(1, min(k, n - k) + 1):
            ntok *= n
            ktok *= t
            n -= 1
        return ntok // ktok
    else:
        return 0


def bezierfunction(points, base=None):
    """"""
    if not base:
        base = bernsteinbase(len(points))

    def func(x):
        val = numpy.zeros(len(points[0]))
        for i in range(len(points)):
            fakt = base[i](x)
            v = numpy.array(points[i]) * fakt
            val += v
        return val

    return func



def fitbezier(points, base=bernsteinbase(3), start=True, end=True):
    """Fit to a given set of points with a certain number of spline-points (default=3)
    if start (/ end) is True, the first (/ last) point of the Curve is included"""
    matrix = numpy.matrix(
        [[base[column](row * 1. / (len(points) - 1)) for column in range(len(base))] for row in range(len(points))])
    if not start and not end:
        matrix = numpy.linalg.pinv(matrix)
        out = numpy.array(matrix * points)
        return out
    else:
        A1=numpy.array(matrix)
        A2=[]
        points2=[]
        points1 = numpy.array(points)
        solution = []
        
        if start:
            # add first column to A2 and remove first column of A1
            A2.append(A1[:, 0])
            A1 = A1[:, 1:]
            points2.append(points[0])
            points1 = points1[1:]

        if end:
            # add last column to A2 and remove last column of A1
            A2.append(A1[:, -1])
            A1 = A1[:, :-1]
            points2.append(points[-1])
            points1 = points[:-1]
        A1_inv = numpy.linalg.inv(numpy.dot(A1.T, A1))
        A2 = numpy.array(A2).T
        points1 = numpy.array(points).T
        points2 = numpy.array(points2).T
        for dim, _ in enumerate(points1):
            rhs1 = numpy.array(A1.T.dot(points1[dim]))
            rhs2 = numpy.array((A1.T.dot(A2)).dot(points2[dim])).T
            solution.append(numpy.array(A1_inv.dot(rhs1 - rhs2)))
        solution = numpy.matrix(solution).T.tolist()
        if start:
            solution.insert(0, points[0])
        if end:
            solution.append(points[-1])
        return numpy.array(solution)

if __name__ == "__main__":
    #BezierCurve.fit([[0,0], [1,1], [2,0]])
    import time
    import random
    import cProfile

    a = BezierCurve([[-1,0], [10,10], [20,20]])

    count = 10000
    t1=time.time()
    for i in range(count):
        a(random.random())
    t2 = time.time()
    for i in range(count):
        a.call(random.random())
    t3 = time.time()
    print("faktor", (t3-t2)/(t2-t1))
    cProfile.run("a.call(random.random())")
    # a.numpoints = 4
    # print(a.controlpoints)
    # print(BezierCurve.fit([[0,0],[10,4],[20,0]]).controlpoints)
