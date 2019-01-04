'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.service('geometry', function(utilities) {

    var svc = this;

    this.basis = ['x', 'y', 'z'];
    this.basisVectors = {
        x: [1, 0, 0],
        y: [0, 1, 0],
        z: [0, 0, 1]
    };

    this.dotProduct = function (vector1, vector2) {
        if(vector1.length !== vector2.length) {
            throw 'Vectors have different dimensions: ' + vector1.length + ' != ' + vector2.length;
        }
        var prod = 0;
        vector1.forEach(function (e, i) {
            prod += (e * vector2[i]);
        });
        return prod;
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
            equals: function (p2) {
                var t = 0.0001;
                return this.dimension() == p2.dimension() &&
                    Math.abs(this.x - p2.x) <= t && Math.abs(this.y - p2.y) <= t && Math.abs(this.z - p2.z) <= t;
            },
            isInRect: function (r) {
                return r.containsPoint(this);
            },
            str: function () {
                return this.coords();  // + ' dimension ' + this.dimension();
            }
        };
    };
    this.pointFromArr = function (arr) {
        return this.point(arr[0], arr[1], arr[2]);
    };

    // 2d only
    this.line = function(point1, point2) {
        return {
            containsPoint: function (p, tolerance) {
                // since we do math to see if the point satisfies the line's equation,
                // we need to specify how close we can get to account for rounding errors
                var t = tolerance || 0.0001;
                if(this.slope() === Infinity) {
                    return Math.abs(p.x - point1.x) <= t;
                }
                var y = this.slope() * p.x + this.intercept();
                return Math.abs(p.y - y) <= t;
            },
            equals: function (l2) {
                if(this.slope() === Infinity && l2.slope() === Infinity) {
                    return this.points()[0].x === l2.points()[0].x;
                }
                return this.slope() === l2.slope() && this.intercept() === l2.intercept();
            },
            intercept: function() {
                return point1.y - point1.x * this.slope();
            },
            intersection: function (l2) {
                //srdbg('finding int', this.points(), l2.points());
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
            comparePoint: function(p) {
                // for our purposes, "below" means having a y value less than the
                // line at the same x; or, for vertical lines, having an x value less than
                // that of the line
                if(this.containsPoint(p)) {
                    return 0;
                }
                if(this.slope() === Infinity) {
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
        return {
            containsPoint: function (p) {
                var ext = this.extents();
                return this.line().containsPoint(p) &&
                    (p.x >= ext[0][0] && p.x <= ext[0][1]) &&
                    (p.y >= ext[1][0] && p.y <= ext[1][1]);
            },
            equals: function (ls2) {
                var ps1 = this.points();
                var ps2 = ls2.points();
                return (ps1[0].equals(ps2[0]) && ps1[1].equals(ps2[1])) ||
                    (ps1[0].equals(ps2[1]) && ps1[1].equals(ps2[0]));
            },
            extents: function() {
                var pts = this.points();
                return [
                    [Math.min(pts[0].x, pts[1].x), Math.max(pts[0].x, pts[1].x)],
                    [Math.min(pts[0].y, pts[1].y), Math.max(pts[0].y, pts[1].y)]
                ];
            },
            intercept: function() {
                return this.line().intercept();
            },
            intersection: function (ls2) {
                var p = this.line().intersection(ls2.line());
                return p ? (this.containsPoint(p) && ls2.containsPoint(p) ? p : null) : null;
            },
            length: function () {
                return point1.dist(point2);
            },
            line: function() {
                return svc.line(point1, point2);
            },
            pointFilter: function() {
                var ls = this;
                return function (point) {
                    return ls.containsPoint(point);
                };
            },
            points: function () {
                return [point1, point2];
            },
            slope: function() {
                return this.line().slope();
            },
            str: function () {
                return this.points().map(function (p) {
                    return p.str();
                });
            },
            vector: function () {
                return [point1.x - point2.x, point1.y - point2.y];
            },
        };
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
                    if(! this.containsPoint(crn[i])) {
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
            intersectsRect: function (r) {
                var rs = r.sides();
                var ts = this.sides();
                for(var i in rs) {
                    var rside = rs[i];
                    for(var j in ts) {
                        var tside = ts[j];
                        if(rside.intersection(tside)) {
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
            }
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

        xform.compose = function (otherXForm) {
            if(otherXForm.matrix.length !== l) {
                throw errMsg('Matrices must be same size (' + l + ' != ' + otherXForm.matrix.length);
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

    this.transpose = function (matrix) {
        var m = [];
        var l = matrix.length;
        if(! l ) {
            return m;
        }
        // convert 1 x l into l x 1
        var ll = matrix[0].length;
        if(ll == 0) {
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

    // returns a line segment matching the portion of an edge inside the given rectangle
    // The edge is selected from those provided by picking the first one that
    // contains the given corners
    // should corners beome a selection function for the edge?  could filter before calling also
    // move to plotting vtk?  It's not basic enough for geometry
    // may not need dimension or sort direction?
    // we need both the clipped and unclipped segments
    this.bestLineSegment = function (edges, cornersArr, boundingRect, dim, reverse) {
        var edge;
        var seg;
        if(! cornersArr || cornersArr.length === 0) {
            edge = edges[0];
            seg = bestLineSegmentForEdge(edge, boundingRect, dim, reverse);
        }
        for(var corners in cornersArr) {
            // first check whether any of the supplied edges contain the corners
            edge = this.firstEdgeWithCorners(edges, cornersArr[corners]);
            if(! edge) {
                continue;
            }
            seg = bestLineSegmentForEdge(edge, boundingRect, dim, reverse);
            if(seg) {
                break;
            }
        }  // end loop over corners
        if(edge && seg) {
            return {
                full: edge,
                clipped: seg
            };
        }
        return null;
    };

    this.bestLineSegmentForEdges = function (edges, boundingRect, dim, reverse) {
        var edge;
        var seg;
        for(var i in edges) {
            edge = edges[i];
            seg = bestLineSegmentForEdge(edge, boundingRect, dim, reverse);
            if(seg) {
                return {
                    full: edge,
                    clipped: seg
                };
            }
        }
        return null;
    };

    function bestLineSegmentForEdge(edge, boundingRect, dim, reverse) {

        //srdbg(dim, 'getting best seg for', edge.str());
        // edgeEndsInBounds are the coordinates of the ends of the selected edge are on or inside the
        // boundary rectangle
        var edgeEndsInBounds = edge.points().filter(boundingRect.pointFilter());
        //srdbg(dim, 'edgeEndsInBounds', edgeEndsInBounds);

        // projectedEnds are the 4 points where the boundary rectangle intersects the
        // *line* defined by the selected edge
        var projectedEnds = boundingRect.boundaryIntersectionsWithSeg(edge);
        //srdbg('gm intx with bounds', projectedEnds);

        // if the selected edge does not intersect the boundary, it
        // means both ends are off screen; so, reject it
        if(projectedEnds.length == 0) {
            //srdbg(dim, 'all offscreen', projectedEnds);
            return null;
        }

        // now we have any edge endpoint that is in or on the boundary, plus
        // the points projected to the boundary
        // get all of those points that also lie on the selected edge

        var ap = edgeEndsInBounds.concat(projectedEnds);
        //srdbg(dim, 'all points', ap);
        var allPoints = ap.filter(edge.pointFilter());
        //srdbg(dim, 'all points on edge', allPoints);
        var uap = utilities.unique(allPoints, function (p1, p2) {
            return p1.equals(p2);
        });
        if(uap.length < 2) {  // need 2 points to define the line segment
            //srdbg(dim, 'not enough points', uap);
            return null;
        }
        //srdbg(dim, 'uniques', uap);
        var seg = svc.lineSegmentFromArr(svc.sortInDimension(uap, dim, reverse));

        if(edgeEndsInBounds.length === 0) {
            return seg;
        }

        // if the edge is showing and the line segment is too short (here half the length of the actual edge),
        // do not use it
        //srdbg(dim, 'checking seg', seg.points());
        if(seg.length() / edge.length() > 0.5) {
            return seg;
        }
        //srdbg(dim, 'points', allPoints, 'uniques', uap);
        //srdbg(dim, 'seg too short:', seg.str(), seg.length(), edge.length(), seg.length() / edge.length());
        return null;
    }

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
        return '[' +
            arr.map(function (p) {
            return p.str();
        }) +
            ']';
    };

    // Sort (with optional reversal) the point array by the values in the given dimension;
    // Array is cloned first so the original is unchanged
    this.sortInDimension = function (points, dim, doReverse) {
        if(! points || ! points.length) {
            throw svc.parrstr(points) + ': Invalid points';
        }
        return points.slice(0).sort(function (p1, p2) {
            // throws an exception if the points have different dimensions
            p1.dist(p2);
            return (doReverse ? -1 : 1) * (p1[dim] - p2[dim]) / Math.abs(p1[dim] - p2[dim]);
        });
    };

    // returns an array containing the unique elements of the input,
    // according to a two-input equality function (null means use ===)
    function unique(arr, equals) {
        var uniqueArr = [];
        arr.forEach(function (a, i) {
            var found = false;
            //srdbg('checking uniques', uniqueArr);
            for(var j = 0; j < uniqueArr.length; ++j) {
                var b = arr[j];
                found = equals ? equals(a, b) : a === b;
                if(found) {
                    break;
                }
            }
            if(! found) {
                uniqueArr.push(a);
            }
        });
        return uniqueArr;
    }

});