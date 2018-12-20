'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.service('geometry', function() {

    var svc = this;

    this.basis = ['x', 'y', 'z'];

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
                return this.dimension() == p2.dimension() &&
                    this.x === p2.x && this.y === p2.y && this.z === p2.z;
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
            containsPoint: function (p) {
                if(this.slope() === Infinity) {
                    return p.x === point1.x;
                }
                return p.y === this.slope() * p.x + this.intercept();
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
            points: function () {
                return [point1, point2];
            },
            slope: function() {
                return point2.x === point1.x ? Infinity : (point2.y - point1.y) / (point2.x - point1.x);
            },
            str: function () {
                return this.points().map(function (p) {
                    return p.str();
                });
            }
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
                //srdbg('intx l1', this.str(), 'l2', ls2.str());
                var p = this.line().intersection(ls2.line());
                return p ? (this.containsPoint(p) && ls2.containsPoint(p) ? p : null) : null;
            },
            length: function () {
                return point1.dist(point2);
            },
            line: function() {
                return svc.line(point1, point2);
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
            }
        };
    };
    this.lineSegmentFromArr = function (arr) {
        return this.lineSegment(arr[0], arr[1]);
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
                //srdbg('contais', l);
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

    // Find where the "scene" (bounds of the rendered objects) intersects the screen (viewport)
    // Returns the properties of the first set of corners that fit - order them by desired location.
    // Could be none fit, in which case no properties are defined
    // maybe return a line segment instead
    // should corners beome a selection function for the edge?
    this.bestLineSegment = function (vpEdges, cornersArr, boundingRect, dim, reverse) {
        //var props = {};
        for(var corners in cornersArr) {
            //srdbg('gm checknig corner', cornersArr[corners]);
            // first check whether any of the supplied edges contain the corners
            var edge = this.firstEdgeWithCorners(vpEdges, cornersArr[corners]);
            if(! edge) {
                continue;  // try next corners
            }
            //srdbg('using edge', edge);
            // these are the coordinates of the ends of the selected edge
            var sceneEnds = edge.points().filter(function (p) {
                        return boundingRect.containsPoint(p);
                    });
            //sceneEnds = this.sortInDimension(boundingRect.boundaryIntersectionsWithSeg(edge), dim, reverse);
            //srdbg('gm sorted pts', sceneEnds);
            //var edgeLen = edge.length();  //sceneEnds[0].dist(sceneEnds[1]);
            // screenEnds are the 4 points where the boundary rectangle intersects the
            // *line* defined by the selected edge
            var screenEnds = boundingRect.boundaryIntersectionsWithSeg(edge);
            srdbg('gm intx with bounds', screenEnds);

            // if the bound edge does not intersect the boundary rectangle in 2 places, it
            // means one or both ends are off screen; so, reject it
            if(screenEnds.length == 0) {
                continue;
            }
            // projectedEnds are just the screenEnds, sorted
            //var projectedEnds = this.sortInDimension(screenEnds, dim, reverse);
            var allPoints = sceneEnds.concat(screenEnds)
                .filter(function (p) {
                return edge.containsPoint(p);
            });
            var uap = unique(
                this.sortInDimension(allPoints, dim, reverse),
                function (p1, p2) {
                return p1.equals(p2);
            });
            //if(projectedEnds && projectedEnds.length == 2) {
                // clippedLen is the length of the line segment defined by the clipped ends
                //var clippedLen = projectedEnds[0].dist(projectedEnds[1]);
                // if the clipped edge length is too small (here half the length of the actual edge),
                // do not bind to this edge (not enough will be visible to be effective)
                //if(clippedLen / edgeLen > 0.5) {
            var seg = this.lineSegmentFromArr(uap);
                if(seg.length() / edge.length() > 0.5) {
                    /*
                    props.boundEdge = edge;
                    props.sceneEnds = sceneEnds;
                    props.screenEnds = screenEnds;
                    props.sceneLen = edgeLen;
                    props.projectedEnds = projectedEnds;
                    */
                    // if both ends of the edge are offscreen, use the clipped ends
                    // if both are on screen, use the edge
                    // if one is on, use the seg made by connecting the
                    // clipped end that is on the visible edge (it must exist if we got here)

                    /*
                    switch (sceneEnds.length) {
                        case 0:
                            srdbg('no scene');
                            props.seg = this.lineSegmentFromArr(projectedEnds);
                            break;
                        case 1:
                            srdbg('1 scene');
                            var p1 = sceneEnds[0];
                            var p2 = edge.containsPoint(projectedEnds[0]) ? projectedEnds[0] : projectedEnds[1];
                            srdbg('sorting seg');
                            var arr = this.sortInDimension([p1, p2], dim, reverse);
                            props.seg = this.lineSegmentFromArr(arr);
                            break;
                        default:
                            srdbg('2 scene');
                            props.seg = this.lineSegmentFromArr(sceneEnds);
                     }
                            */
                    //props.seg = this.lineSegmentFromArr(uap);  // always 0 or 2?
                    return seg;  // this.lineSegmentFromArr(uap);  // always 0 or 2?
                    //return props;
                }
            //}
        }  // end loop over corners
        return null;  //props;
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
            //srdbg('checking seg', l.str());
            return l.points().some(function (c) {
                //srdbg('checking pt', c);
                return points.some(function (p) {
                    return p.equals(c);
                });
            });
        });
    };
    this.firstEdgeWithCorners = function(lines, points) {
        //srdbg('1st edgs', this.edgesWithCorners(lines, points)[0].str());
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
    };

    // returns an array containing the unique elements of the input,
    // according to a two-input equality function (null means use ===)
    function unique(arr, equals) {
        var uniqueArr = [];
        arr.forEach(function (a) {
            var found = false;
            uniqueArr.forEach(function (b) {
                found = equals ? equals(a, b) : a === b;
            });
            if(! found) {
                uniqueArr.push(a);
            }
        });
        return uniqueArr;
    }

});