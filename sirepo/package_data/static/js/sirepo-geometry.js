'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.service('geometry', function() {

    var svc = this;

    // Used for both 2d and 3d
    this.pointFromArr = function (arr) {
        //srdbg('makig pt from', arr);
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
                if(this.slope() === 0) {
                    return p.y === point1.y;
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
            return p.coords() + ' dimension ' + p.dimension();
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