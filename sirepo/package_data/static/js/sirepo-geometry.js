'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.service('geometry', function() {

    var svc = this;
    var basis = ['x', 'y', 'z'];


    // Used for both 2d and 3d
    this.pointFromArr = function (arr) {
        return this.point(arr[0], arr[1], arr[2]);
    };
    this.point = function(x, y, z) {
        return {
            x: x || 0,
            y: y || 0,
            z: z || 0,
            coords: function () {
                return [this.x, this.y, this.z];
            },
            dimension: function() {
                return 2 + (angular.isDefined(z) ? 1 : 0);
            },
            dist: function (p2) {
                if(this.dimension() != p2.dimension()) {
                    throw 'Points in array have different dimensions: ' + this.dimension() + ' != ' + p2.dimension();
                }
                return Math.sqrt(
                    (p2.x - this.x) * (p2.x - this.x) +
                    (p2.y - this.y) * (p2.y - this.y) +
                    (p2.z - this.z) * (p2.z - this.z)
                );
            },
            isInRect: function (r) {
                return r.containsPoint(this);
            },
            equals: function (p2) {
                return this.dimension() == p2.dimension() &&
                    this.x === p2.x && this.y === p2.y && this.z === p2.z;
            },
            str: function () {
                return this.coords() + ' dimension ' + this.dimension();
            }
        };
    };

    // 2d only
    this.line = function(point1, point2) {
        return {
            points: function () {
                return [point1, point2];
            },
            slope: function() {
                return point2.x === point1.x ? Infinity : (point2.y - point1.y) / (point2.x - point1.x);
            },
            intercept: function() {
                return point1.y - point1.x * this.slope();
            },
            intersection: function (l2) {
                if(this.slope() === l2.slope()) {
                    if(this.equals(l2)) {
                        return this.points()[0];
                    }
                    return null;
                }
                if(this.slope() === Infinity) {
                    return svc.point(point1.x, l2.slope() * point1.x + l2.intercept());
                }
                if(l2.slope() === Infinity) {
                    return svc.point(l2.points()[0].x, this.slope() * l2.points()[0].x + this.intercept());
                }
                return svc.point(
                    (this.intercept() - l2.intercept()) / (l2.slope() - this.slope()),
                    (l2.slope() * this.intercept() - this.slope() *l2.intercept()) / (l2.slope() - this.slope())
                );
            },
            equals: function (l2) {
                return this.slope() === l2.slope() && this.intercept() === l2.intercept();
            },
            containsPoint: function (p) {
                if(this.slope() === Infinity) {
                    return p.x === point1.x;
                }
                return p.y === this.slope() * p.x + this.intercept();
            },
        };
    };


    // 2d only
    this.lineSegment = function(point1, point2) {
        return {
            points: function () {
                return [point1, point2];
            },
            line: function() {
                return svc.line(point1, point2);
            },
            slope: function() {
                return this.line().slope();
            },
            intercept: function() {
                return this.line().intercept();
            },
            intersection: function (l2) {
                var p = this.line().intersection(l2);
                return this.line().containsPoint(p) ? p : null;
            },
            length: function () {
                return point1.dist(point2);
            },
            equals: function (l2) {
                var ps1 = this.points();
                var ps2 = l2.points();
                return (ps1[0].equals(ps2[0]) && ps1[1].equals(ps2[1])) ||
                    (ps1[0].equals(ps2[1]) && ps1[1].equals(ps2[0]));
            },
        };
    };

    // 2d only
    this.rect = function(diagPoint1, diagPoint2) {
        return {
            points: function () {
                return [diagPoint1, diagPoint2];
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
            boundaries: function() {
                var b = [];
                var c = this.corners();
                for(var i = 0; i < 4; ++i) {
                    b.push(svc.lineSegment(c[i], c[(i + 1) % 4]));
                }
                return b;
            },
            boundaryIntersectons: function (point1, point2) {
                var l1 = svc.line(point1, point2);
                return this.boundaries().map(function (l2) {
                    return l1.intersection(l2);
                });
            },
            segmentsInside: function(lines) {
                var r = this;
                return lines.filter(function (l) {
                    return r.containsLineSegment(l);
                });
            },
            containsLineSegment: function (l) {
                return this.containsPoint(l.points()[0]) && this.containsPoint(l.points()[1]);
            },
            containsPoint: function (p) {
                var c = this.corners();
                return p.x >= c[0].x && p.x <= c[2].x && p.y >= c[0].y && p.y <= c[2].y;
            },
        };
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
            var d = 0;
            var len = matrix.length;
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
        }

        function trans(matrix) {
            var m = [];
            for(var i in matrix) {
                var r = [];
                for(var j in matrix) {
                    r.push(matrix[j][i]);
                }
                m.push(r);
            }
            return m;
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
        if(l > 3 || l < 1) {
            throw errMsg('Matrix has bad size (' + l + ')');
        }
        if(! xform.matrix.reduce(function (ok, row) {
                return ok && row.length == l;
            }, true)
        ) {
            throw errMsg('Matrix is not square');
        }
        if(det(xform.matrix) === 0) {
            throw errMsg('Matrix is not invertable');
        }

        xform.det = function() {
            return det(xform.matrix);
        };

        xform.doTransform = function (point) {
            return vectorMult(xform.matrix, point);
        };
        xform.doTX = function (point) {
            return svc.pointFromArr(
                xform.doTransform(point.coords())
            );
        };
        xform.compose = function (otherXForm) {
            if(otherXForm.matrix.length !== l) {
                throw errMsg('Matrices must be same size (' + l + ' != ' + otherXForm.matrix.length);
            }
            return svc.transform(matrixMult(xform.matrix, otherXForm.matrix));
        };
        xform.composeFromMatrix = function (m) {
            return xform.compose(svc.transform(m));
        };
        xform.equals = function(otherXForm) {
            for(var i in xform.matrix) {
                for(var j in xform.matrix) {
                    if(xform.matrix[i][j] != otherXForm.matrix[i][j])  {
                        return false;
                    }
                }
            }
            return true;
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

    // Returns the point(s) that have the smallest (reverse == false) or largest value in the given dimension
    this.extrema = function(points, dim, doReverse) {
        var arr = svc.sortInDimension(points, dim, doReverse);
        return arr.filter(function (point) {
            return point[dim] == arr[0][dim];
        });
    };


    // Returns the members of an array of edges (point pairs) that
    // contain any of the points in another array
    this.edgesWithCorners = function(lines, points) {
        return lines.filter(function (l) {
            return l.points().some(function (c) {
                return points.some(function (p) {
                    return p.equals(c);
                });
            });
        });
    };
    this.firstEdgeWithCorners = function(lines, points) {
        return this.edgesWithCorners(lines, points)[0];
    };

    this.parrstr = function(arr) {
        return arr.map(function (p) {
            return p.str();
        });
    };

    // Sort (with optional reversal) the point array by the values in the given dimension;
    // Array is cloned first so the original is unchanged
    this.sortInDimension = function (points, dim, doReverse) {
        //srdbg('sorting', this.parrstr(points), 'in dim', dim, 'reverse?', doReverse, 'p0', points[0][dim]);
        if(! points || ! points.length) {
            throw svc.parrstr(points) + ': Invalid points';
        }
        return points.slice(0).sort(function (p1, p2) {
            // throws an exception if the points have different dimensions
            p1.dist(p2);
            //srdbg('p1[' + dim + ']:', p1[dim], 'p2[' + dim + ']:', p2[dim]);
            return (doReverse ? -1 : 1) * (p1[dim] - p2[dim]) / Math.abs(p1[dim] - p2[dim]);
        });
        //srdbg('sorted', parrstr(arr));
    };

});