'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

// Math.hypot polyfill for Internet Explorer and karma tests
if (!Math.hypot) {
    Math.hypot = function() {
        var y = 0, i = arguments.length;
        while (i--) {
            y += arguments[i] * arguments[i];
        }
        return Math.sqrt(y);
    };
}

SIREPO.app.service('geometry', function(utilities) {

    var svc = this;

    this.basis = ['x', 'y', 'z'];
    this.basisVectors = {
        x: [1, 0, 0],
        y: [0, 1, 0],
        z: [0, 0, 1]
    };

    this.bestEdgeAndSectionInBounds = function (edges, boundingRect, dim, reverse) {
        var edge;
        var section;
        for(var i in edges) {
            edge = edges[i];
            section = sectionOfEdgeInBounds(edge, boundingRect, dim, reverse);
            if (section) {
                return {
                    full: edge,
                    clipped: section,
                    index: i
                };
            }
        }
        return null;
    };

    // Returns the point(s) that have the smallest (reverse == false) or largest value in the given dimension
    this.extrema = function(points, dim, doReverse) {
        var arr = svc.sortInDimension(points, dim, doReverse);
        return arr.filter(function (point) {
            return point[dim] == arr[0][dim];
        });
    };

    this.geomObjArrStr = function(arr) {
        return '[' +
            arr.map(function (e) {
                var strFn = e.str;
                if (! strFn) {
                    return '<OBJ>';
                }
                return strFn();
        }) +
            ']';
    };

    // 2d only
    this.line = function(point1, point2) {
        return {
            containsPoint: function (p, tolerance) {
                // since we do math to see if the point satisfies the line's equation,
                // we need to specify how close we can get to account for rounding errors
                var t = tolerance || 0.0001;
                var s = this.slope();
                if (s === Infinity) {
                    return equalWithin(p.x, point1.x, t);
                }
                var y = s * p.x + this.intercept();

                return equalWithin(p.y, y, t);
            },
            equals: function (l2) {
                if (this.slope() === Infinity && l2.slope() === Infinity) {
                    return equalWithin(this.points()[0].x, l2.points()[0].x);
                }
                return this.slope() === l2.slope() && this.intercept() === l2.intercept();
            },
            intercept: function() {
                return point1.y - point1.x * this.slope();
            },
            intersection: function (l2) {
                if (this.slope() === l2.slope()) {
                    if (this.equals(l2)) {
                        return this.points()[0];
                    }
                    return null;
                }
                if (this.slope() === Infinity) {
                    return svc.point(point1.x, l2.slope() * point1.x + l2.intercept());
                }
                if (l2.slope() === Infinity) {
                    return svc.point(l2.points()[0].x, this.slope() * l2.points()[0].x + this.intercept());
                }
                return svc.point(
                    (this.intercept() - l2.intercept()) / (l2.slope() - this.slope()),
                    (l2.slope() * this.intercept() - this.slope() *l2.intercept()) / (l2.slope() - this.slope())
                );
            },
            comparePoint: function(p) {
                if (this.containsPoint(p)) {
                    return 0;
                }
                if (this.slope() === Infinity) {
                    return p.x > point1.x ? 1 : -1;
                }
                var y = this.slope() * p.x + this.intercept();
                return p.y > y ? 1 : -1;
            },
            points: function () {
                return [point1, point2];
            },
            slope: function() {
                return point2.x === point1.x ? Infinity : (point2.y - point1.y) / (point2.x - point1.x);
            },
            str: function () {
                return 'slope ' + this.slope() + ' intercept ' + this.intercept() + ' (' +
                    this.points().map(function (p) {
                    p.str();
                }) + ')';
            },
            vector: function () {
                return [point1.x - point2.x, point1.y - point2.y];
            },
        };
    };
    this.lineFromArr = function (arr) {
        return this.line(arr[0], arr[1]);
    };


    // 2d only
    this.lineSegment = function(point1, point2) {
        var ls = {
            ext: [
                [Math.min(point1.x, point2.x), Math.max(point1.x, point2.x)],
                [Math.min(point1.y, point2.y), Math.max(point1.y, point2.y)]
            ],
            p1: point1,
            p2: point2,
            l: svc.line(point1, point2)
        };

        ls.containsPoint = function (p) {
            var ext = this.extents();
            return this.line().containsPoint(p) &&
                (gtOrEqualWithin(p.x, ext[0][0]) && ltOrEqualWithin(p.x, ext[0][1])) &&
                (gtOrEqualWithin(p.y, ext[1][0]) && ltOrEqualWithin(p.y, ext[1][1]));
        };
        ls.equals = function (ls2) {
            var ps1 = this.points();
            var ps2 = ls2.points();
            return (equalWithin(ps1[0], ps2[0]) && equalWithin(ps1[1], ps2[1])) ||
                (equalWithin(ps1[0], ps2[1]) && equalWithin(ps1[1], ps2[0]));
        };
        ls.extents = function() {
            var pts = this.points();
            return [
                [Math.min(pts[0].x, pts[1].x), Math.max(pts[0].x, pts[1].x)],
                [Math.min(pts[0].y, pts[1].y), Math.max(pts[0].y, pts[1].y)]
            ];
        };
        ls.intercept = function() {
            return this.line().intercept();
        };
        ls.intersection = function (ls2) {
            var p = this.line().intersection(ls2.line());
            return p ? (this.containsPoint(p) && ls2.containsPoint(p) ? p : null) : null;
        };
        ls.length = function () {
            return point1.dist(point2);
        };
        ls.line = function() {
            return svc.line(this.p1, this.p2);
        };
        ls.pointFilter = function() {
            var ls = this;
            return function (point) {
                return ls.containsPoint(point);
            };
        };
        ls.points = function () {
            return [this.p1, this.p2];
        };
        ls.slope = function() {
            return this.line().slope();
        };
        ls.str = function () {
            return this.points().map(function (p) {
                return p.str();
            });
        };
        ls.update = function(newp1, newp2) {
            this.ext = [
                [Math.min(newp1.x, newp2.x), Math.max(newp1.x, newp2.x)],
                [Math.min(newp1.y, newp2.y), Math.max(newp1.y, newp2.y)]
            ];
            this.p1 = newp1;
            this.p2 = newp2;
            this.l = svc.line(newp1, newp2);
        };
        ls.vector = function () {
            return [this.p1.x - this.p2.x, this.p1.y - this.p2.y];
        };

        return ls;
    };
    this.lineSegmentFromArr = function (arr) {
        return this.lineSegment(arr[0], arr[1]);
    };

    this.matrixAdd = function (matrix1, matrix2) {
        var m = [];
        matrix1.forEach(function (row1, i) {
            m.push(this.vectorAdd(row1, matrix2[i]));
        });
    };

    this.matrixDet = function(matrix) {
        var d = 0;
        var len = matrix.length;
        if (len === 2) {
            d = matrix[0][0] * matrix[1][1] - matrix[1][0] * matrix[0][1];
            return d;
        }
        for(var i in matrix) {
            var t = 1;
            var s = 1;
            for(var j in matrix) {
                var k = (i + j) % len;
                var l = (i + len - j) % len;
                t *= matrix[j][k];
                s *= matrix[j][l];
            }
            d += (t - s);
        }
        return d;
    };

    this.matrixEquals = function(m1, m2) {
        if (m1.length !== m2.length) {
            return false;
        }
        for(var i in m1) {
            for(var j in m2) {
                if (! equalWithin(m1[i][j], m2[i][j])) {
                    return false;
                }
            }
        }
        return true;
    };

    this.matrixInvert = function(matrix) {
        var d = svc.matrixDet(matrix);
        if (! d) {
            return null;
        }
        var mx = svc.transpose(matrix);
        var inv = [];
        for (var i = 0; i < mx.length; ++i) {
            var row = mx[i];
            var invRow = [];
            var mult = 1;
            for(var j = 0; j < mx.length; ++j) {
                mult = Math.pow(-1,i + j);
                invRow.push((mult / d) * svc.matrixDet(svc.matrixMinor(mx, i, j)));
            }
            inv.push(invRow);
        }
        return inv;
    };

    this.matrixMinor = function(matrix, row, col) {
        var m = [];
        for(var i = 0; i < matrix.length; ++i) {
            var r = [];
            for(var j = 0; j < matrix.length; ++j) {
                if (i != row && j != col) {
                    r.push(matrix[i][j]);
                }
            }
            if (r.length > 0) {
                m.push(r);
            }
        }
        return m;
    };

    this.matrixMult = function(m1, m2) {
        var m = [];
        for(var i in m1) {
            var c = [];
            for(var j in m2) {
                c.push(m2[j][i]);
            }
            m.push(svc.vectorMult(m1, c));
        }
        return svc.transpose(m);
    };

    // Used for both 2d and 3d
    this.point = function(x, y, z) {
        return {
            x: x || 0,
            y: y || 0,
            z: z || 0,
            coords: function () {
                return [this.x, this.y, this.z];
            },
            dimension: function() {
                return 2 + (z === undefined ? 0 : 1);
            },
            dist: function (p2) {
                if (this.dimension() != p2.dimension()) {
                    throw new Error('Points in array have different dimensions: ' + this.dimension() + ' != ' + p2.dimension());
                }
                return Math.hypot(p2.x - this.x, p2.y - this.y, p2.z - this.z);
            },
            equals: function (p2) {
                var t = 0.0001;
                var d = 0.5 * (this.dist(this.zero()) + p2.dist(this.zero())) || 1.0;
                return this.dimension() == p2.dimension() && this.dist(p2) / d < t;
            },
            isInRect: function (r) {
                return r.containsPoint(this);
            },
            str: function () {
                return '(' + this.coords() + ')';  // + ' dimension ' + this.dimension();
            },
            zero: function () {
                if (this.dimension() === 2) {
                    return svc.point(0, 0);
                }
                return svc.point(0, 0, 0);
            }
        };
    };

    this.pointFromArr = function (arr) {
        return this.point(arr[0], arr[1], arr[2]);
    };

    // construct from array of points, assumed to be in "drawing order"
    this.polygon = function (pts) {

        if (pts.length < 3) {
            throw new Error('A polygon requires at least 3 points (' + pts.length + ' provided)');
        }

        /*
        var bounds = {};
        svc.basis.forEach(function (dim) {
            bounds[dim] = {};
            var d = pts.map(function (pt) {
                return pt[dim];
            });
            bounds[dim].min = Math.min.apply(null, d);
            bounds[dim].max = Math.max.apply(null, d);
        });
        */

        //var boundaryRect = svc.rect(svc.point(bounds.x.min, bounds.y.min), svc.point(bounds.x.max, bounds.y.max));

        var sides = Array(pts.length);
        pts.forEach(function (pt, ptIdx) {
            //sides[ptIdx] = svc.lineSegment(pts[(ptIdx + 1) % pts.length], pt);
            sides[ptIdx] = [pts[(ptIdx + 1) % pts.length], pt];
        });

        // static properties set at init
        var poly = {
            //bounds: bounds,
            points: pts,
            //boundaryRect: boundaryRect,
            sides: sides,
        };

        // "ray casting" simplified
        poly.containsPoint = function(pt) {
            // count sides whose endpoints are above/below the input point and have least one endpoint to the left
            // - implies a ray starting at -Infinity crosses that many sides
            return sides.filter(function (ls) {
                return (ls[0][1] > pt[1] !== ls[1][1] > pt[1]) &&
                    (ls[0][0] < pt[0] || ls[1][0] < pt[0]);
                //return (ls.p1.y > pt.y !== ls.p2.y > pt.y) &&
                //    (ls.p1.x < pt.x || ls.p2.x < pt.x);
            }).length  % 2 === 1;
        };

        // should start separating "dynamic" from "static" - if points are not expected to change there is
        // no reason to recalculate everything.  Maybe an argument?
        /*
        poly.getBoundaryRect = function() {
            var b = this.bounds();
            return svc.rect(svc.point(b.x.min, b.y.min), svc.point(b.x.max, b.y.max));
        };

        poly.getBounds = function() {
            var b = {};
            svc.basis.forEach(function (dim) {
                var d = pts.map(function (pt) {
                    return pt[dim];
                });
                b[dim] = {};
                b[dim].min = Math.min.apply(null, d);
                b[dim].max = Math.max.apply(null, d);
            });
            return b;
        };

        poly.getPoints = function () {
            return pts;
        };

        poly.getSides = function() {
            var ls = Array(pts.length);
            pts.forEach(function (pt, ptIdx) {
                ls[ptIdx] = svc.lineSegment(pts[(ptIdx + 1) % pts.length], pt);
            });
            return ls;
        };
        */
        return poly;
    };

    this.polyFromArr = function (arr) {
        return this.polygon(arr.map(function (c) {
            return svc.pointFromArr(c);
        }));
    };

    // 2d only
    this.rect = function(diagPoint1, diagPoint2) {
        return {
            area: function () {
                return Math.abs(diagPoint2.x - diagPoint1.x) * Math.abs(diagPoint2.y - diagPoint1.y);
            },
            boundaryIntersectionsWithLine: function (l1) {
                var r = this;
                return r.sides()
                    .map(function (l2) {
                    return l1.intersection(l2);
                })
                    .filter(function (p) {
                        return p && r.containsPoint(p);
                    });
            },
            boundaryIntersectionsWithPts: function (point1, point2) {
                return this.boundaryIntersectionsWithSeg(svc.lineSegment(point1, point2));
            },
            boundaryIntersectionsWithSeg: function (lseg) {
                return this.boundaryIntersectionsWithLine(lseg.line());
            },
            center: function () {
                svc.point(
                    diagPoint1.x + (diagPoint2.x - diagPoint1.x) / 2,
                    diagPoint1.y + (diagPoint2.y - diagPoint1.y) / 2
                );
            },
            containsLineSegment: function (l) {
                return this.containsPoint(l.points()[0]) && this.containsPoint(l.points()[1]);
            },
            containsPoint: function (p) {
                var c = this.corners();
                return p.x >= c[0].x && p.x <= c[2].x && p.y >= c[0].y && p.y <= c[2].y;
            },
            containsRect: function (r) {
                var crn = r.corners();
                for(var i in crn) {
                    if (! this.containsPoint(crn[i])) {
                        return false;
                    }
                }
                return true;
            },
            // corners are sorted to go clockwise from (minx, miny) assuming standard axes directions
            corners: function() {
                var c = [];
                for(var i = 0; i < 2; i++) {
                    var p = this.points()[i];
                    for(var j = 0; j < 2; j++) {
                        var q = this.points()[j];
                        c.push(svc.point(p.x, q.y));
                    }
                }
                c.sort(function (p1, p2) {
                    return p1.x > p2.x ? 1 :
                        (p2.x > p1.x ? -1 : p1.y >= p2.y);
                });
                var swap = c[2];
                c[2] = c[3];
                c[3] = swap;
                return c;
            },
            height: function () {
                return this.sides()[0].length();
            },
            intersectsRect: function (r) {
                var rs = r.sides();
                var ts = this.sides();
                for(var i in rs) {
                    var rside = rs[i];
                    for(var j in ts) {
                        var tside = ts[j];
                        if (rside.intersection(tside)) {
                            return true;
                        }
                    }
                }
                return false;
            },
            pointFilter: function() {
                var r = this;
                return function (point) {
                    return r.containsPoint(point);
                };
            },
            points: function () {
                return [diagPoint1, diagPoint2];
            },
            segmentsInside: function(lines) {
                var r = this;
                return lines.filter(function (l) {
                    return r.containsLineSegment(l);
                });
            },
            sides: function () {
                var s = [];
                var crn = this.corners();
                for(var i = 0; i < 4; ++i) {
                    s.push(svc.lineSegment(crn[i], crn[(i + 1) % 4]));
                }
                return s;
            },
            str: function () {
                return svc.geomObjArrStr(this.points());
            },
            width: function () {
                return this.sides()[1].length();
            }
        };
    };

    this.rectFromArr = function (arr) {
        return svc.rect(svc.pointFromArr(arr[0]), svc.pointFromArr(arr[1]));
    };

    // Sort (with optional reversal) the point array by the values in the given dimension;
    // Array is cloned first so the original is unchanged
    this.sortInDimension = function (points, dim, doReverse) {
        if (! points || ! points.length) {
            throw new Error(svc.geomObjArrStr(points) + ': Invalid points');
        }
        return points.slice(0).sort(function (p1, p2) {
            // throws an exception if the points have different dimensions
            p1.dist(p2);
            return (doReverse ? -1 : 1) * (p1[dim] - p2[dim]) / Math.abs(p1[dim] - p2[dim]);
        });
    };

    this.transform = function (matrix) {

        var identityMatrix = [
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1]
        ];
        var xform = {};

        // simple 3d operations, no need to import a whole matrix library
        function det(matrix) {
            return svc.matrixDet(matrix);
        }

        function trans(matrix) {
            return svc.transpose(matrix);
        }

        function vectorMult(m1, v) {
            var v2 = [];
            m1.forEach(function (row) {
                var c = 0;
                for(var i in row) {
                    c += row[i] * v[i];
                }
                v2.push(c);
            });
            return v2;
        }

        // multiplies in provided order ([M1] * [M2]), meaning M2 gets applied to vectors FIRST
        function matrixMult(m1, m2) {
            var m = [];
            for(var i in m1) {
                var c = [];
                for(var j in m2) {
                    c.push(m2[j][i]);
                }
                m.push(vectorMult(m1, c));
            }
            return trans(m);
        }

        function errMsg(s) {
            return matrix + ': ' + s;
        }

        xform.matrix = matrix || identityMatrix;

        var l = xform.matrix.length;
        if (l > 3 || l < 1) {
            throw new Error(errMsg('Matrix has bad size (' + l + ')'));
        }
        if (! xform.matrix.reduce(function (ok, row) {
                return ok && row.length == l;
            }, true)
        ) {
            throw new Error(errMsg('Matrix is not square'));
        }
        if (det(xform.matrix) === 0) {
            throw new Error(errMsg('Matrix is not invertable'));
        }

        xform.compose = function (otherXForm) {
            if (otherXForm.matrix.length !== l) {
                throw new Error(errMsg('Matrices must be same size (' + l + ' != ' + otherXForm.matrix.length));
            }
            return svc.transform(matrixMult(xform.matrix, otherXForm.matrix));
        };

        xform.composeFromMatrix = function (m) {
            return xform.compose(svc.transform(m));
        };

        xform.det = function() {
            return det(xform.matrix);
        };

        xform.doTransform = function (coords) {
            return vectorMult(xform.matrix, coords);
        };
        xform.doTX = function (point) {
            return svc.pointFromArr(
                xform.doTransform(point.coords())
            );
        };

        xform.equals = function(otherXForm) {
            return svc.matrixEquals(xform.matrix, otherXForm.matrix);
        };

        xform.inverse = function() {
            return svc.transform(svc.matrixInvert(xform.matrix));
        };

        xform.str = function () {
            var str = '[';
            for(var i in xform.matrix) {
                var rstr = '[';
                for(var j in xform.matrix[i]) {
                    rstr += xform.matrix[i][j];
                    rstr += (j < xform.matrix[i].length - 1 ? ', ' : ']');
                }
                str += rstr;
                str += (i < xform.matrix.length -1  ? ', ' : ']');
            }
            return str;
        };

        return xform;
    };

    this.transpose = function (matrix) {
        var m = [];
        var l = matrix.length;
        if (! l ) {
            return m;
        }
        // convert 1 x l into l x 1
        var ll = matrix[0].length;
        if (ll == 0) {
            matrix.forEach(function (entry) {
                m.push([entry]);
            });
            return m;
        }
        for(var j = 0; j < ll; ++j) {
            var r = [];
            for(var i = 0; i < l; ++i) {
                r.push(matrix[i][j]);
            }
            m.push(r);
        }
        return m;
    };

    // we will use "vector" to mean an array of numbers, and "point" to be an object
    // that wraps coordinates and defines methods to manipulated them
    this.vectorAdd = function (vector1, vector2) {
        return this.vectorLinearCombination(vector1, vector2, 1);
    };

    this.vectorLinearCombination = function (vector1, vector2, constant) {
        var v = [];
        vector1.forEach(function (el1, i) {
            v.push(el1 + constant * vector2[i]);
        });
        return v;
    };

    this.vectorMult = function (m1, v) {
        var v2 = [];
        m1.forEach(function (row) {
            var c = 0;
            for(var i in row) {
                c += row[i] * v[i];
            }
            v2.push(c);
        });
        return v2;
    };

    this.vectorSubtract = function (vector1, vector2) {
        return this.vectorLinearCombination(vector1, vector2, -1);
    };


    // numbers are to be considered equal if they differ by less than this
    function equalWithin(val1, val2, tolerance) {
        var tol = tolerance || 0.0001;
        return Math.abs(val2 - val1) < tol;
    }

    function gtOutside(val1, val2, tolerance) {
        var tol = tolerance || 0.0001;
        return val1 - val2 > tol;
    }

    function gtOrEqualWithin(val1, val2, tolerance) {
        return val1 > val2 || equalWithin(val1, val2, tolerance);
    }

    function ltOutside(val1, val2, tolerance) {
        var tol = tolerance || 0.0001;
        return val2 - val1 > tol;
    }

    function ltOrEqualWithin(val1, val2, tolerance) {
        return val1 < val2 || equalWithin(val1, val2, tolerance);
    }

    function sectionOfEdgeInBounds(edge, boundingRect, dim, reverse) {

        if (! edge) {
            return null;
        }

        // edgeEndsInBounds are the coordinates of the ends of the selected edge are on or inside the
        // boundary rectangle
        var edgeEndsInBounds = edge.points().filter(boundingRect.pointFilter());

        // projectedEnds are the 4 points where the boundary rectangle intersects the
        // *line* defined by the selected edge
        var projectedEnds = boundingRect.boundaryIntersectionsWithSeg(edge);

        // if the selected edge does not intersect the boundary, it
        // means both ends are off screen; so, reject it
        if (projectedEnds.length == 0) {
            return null;
        }

        // now we have any edge endpoint that is in or on the boundary, plus
        // the points projected to the boundary
        // get all of those points that also lie on the selected edge

        var ap = edgeEndsInBounds.concat(projectedEnds);
        var allPoints = ap.filter(edge.pointFilter());
        var uap = utilities.unique(allPoints, function (p1, p2) {
            return p1.equals(p2);
        });
        if (uap.length < 2) {  // need 2 points to define the line segment
            return null;
        }
        var section = svc.lineSegmentFromArr(svc.sortInDimension(uap, dim, reverse));

        if (edgeEndsInBounds.length === 0) {
            return section;
        }

        // if the edge is showing and the line segment is too short (here half the length of the actual edge),
        // do not use it
        if (section.length() / edge.length() > 0.5) {
            return section;
        }
        return null;
    }


});
