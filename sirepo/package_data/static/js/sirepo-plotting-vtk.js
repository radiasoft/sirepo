'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;
SIREPO.DEFAULT_COLOR_MAP = 'viridis';

SIREPO.app.factory('vtkPlotting', function(appState, plotting, panelState, utilities, plotUtilities, geometry, $window) {

    var self = {};

    // Find where the "scene" (bounds of the rendered objects) intersects the screen (viewport)
    // Returns the properties of the first set of corners that fit - order them by desired location.
    // Could be none fit, in which case no properties are defined
    function edgeIntersections(vpEdges, cornersArr, rect, dim, reverse) {
        var props = {};
        //srdbg('checking for edges that include corners', cornersArr);
        for(var corners in cornersArr) {
            var edges = geometry.edgesWithCorners(vpEdges, cornersArr[corners])[0];
            //srdbg('edges that include corners', cornersArr[corners], edges);
            var sceneEnds = geometry.sortInDimension(edges, dim);
            //srdbg('scene ends', sceneEnds);
            var screenEnds = rect.boundaryIntersectons(sceneEnds[0], sceneEnds[1]);
            //srdbg('screen ends', screenEnds);
            var sceneLen = sceneEnds[0].dist(sceneEnds[1]);
            var clippedEnds = geometry.sortInDimension(
                rect.segmentsInside(screenEnds),
                dim, reverse);
            if(clippedEnds && clippedEnds.length == 2) {
             var clippedLen = clippedEnds[0].dist(clippedEnds[1]);
                if(clippedLen / sceneLen > 0.5) {
                    props.edges = edges;
                    props.sceneEnds = sceneEnds;
                    props.screenEnds = screenEnds;
                    props.sceneLen = sceneLen;
                    props.clippedEnds = clippedEnds;
                    return props;
                }
            }
        }
        return props;
    }

    self.adjustContainerSize = function(container, rect, ctrAspectRatio, thresholdPct) {
        var fsAspectRatio = window.screen.availWidth / window.screen.availHeight;

        container.height(container.width() / (utilities.isFullscreen() ? fsAspectRatio : ctrAspectRatio));

        var w = container.width();
        var h = container.height();
        var wThresh = Math.max(thresholdPct * w, 1);
        var hThresh = Math.max(thresholdPct * h, 1);
        var wdiff = Math.abs(w - rect.width);
        var hdiff = Math.abs(h - rect.height);
        if (hdiff > hThresh || wdiff > wThresh) {
            return true;
        }
        return false;
    };

    self.vtkPlot = function(scope, element) {

        scope.element = element[0];
        var requestData = plotting.initAnimation(scope);

        scope.windowResize = utilities.debounce(function() {
            scope.resize();
        }, 250);

        scope.$on('$destroy', function() {
            scope.destroy();
            scope.element = null;
            $($window).off('resize', scope.windowResize);
        });

        scope.$on(
            scope.modelName + '.changed',
            function() {
                scope.prevFrameIndex = -1;
                if (scope.modelChanged) {
                    scope.modelChanged();
                }
                panelState.clear(scope.modelName);
                requestData();
            });
        scope.isLoading = function() {
            return panelState.isLoading(scope.modelName);
        };
        $($window).resize(scope.windowResize);

        scope.init();
        if (appState.isLoaded()) {
            requestData();
        }
    };

    self.coordMapper = function(transform) {

        // "Bundles" a source, mapper, and actor together
        function actorBundle(source) {
            var m = vtk.Rendering.Core.vtkMapper.newInstance();
            if(source) {
                m.setInputConnection(source.getOutputPort());
            }
            var a = vtk.Rendering.Core.vtkActor.newInstance();
            a.setMapper(m);

            return {
                actor: a,
                source: source,
                mapper: m,
                setActor: function (actor) {
                    actor.setMapper(this.m);
                    this.actor = actor;
                },
                setSource: function (source) {
                    this.mapper.setInputConnection(source.getOutputPort());
                    this.source = source;
                }
            };
        }

        return {

            xform: transform || geometry.transform(),

            buildActorBundle: function(source) {
                return actorBundle(source);
            },
            buildBox: function(labSize, labCenter) {
                var vsize = labSize ? this.xform.doTransform(labSize) :  [1, 1, 1];
                var cs = vtk.Filters.Sources.vtkCubeSource.newInstance({
                    xLength: vsize[0],
                    yLength: vsize[1],
                    zLength: vsize[2],
                    center: labCenter ? this.xform.doTransform(labCenter) :  [0, 0, 0]
                });
                var ab = actorBundle(cs);

                ab.setCenter = function (arr) {
                    ab.source.setCenter(arr);
                };
                ab.setLength = function (arr) {
                    ab.source.setXLength(arr[0]);
                    ab.source.setYLength(arr[1]);
                    ab.source.setZLength(arr[2]);
                };

                return ab;
            },
            buildLine: function(labP1, labP2, colorArray) {
                var vp1 = this.xform.doTransform(labP1);
                var vp2 = this.xform.doTransform(labP2);
                var ls = vtk.Filters.Sources.vtkLineSource.newInstance({
                    point1: [vp1[0], vp1[1], vp1[2]],
                    point2: [vp2[0], vp2[1], vp2[2]],
                    resolution: 2
                });

                var ab = actorBundle(ls);
                ab.actor.getProperty().setColor(colorArray[0], colorArray[1], colorArray[2]);
                return ab;
            },
            buildPlane: function(labOrigin, labP1, labP2) {
                var src = vtk.Filters.Sources.vtkPlaneSource.newInstance();
                if(labOrigin && labP1 && labP2) {
                    this.setPlane(src, labOrigin, labP1, labP2);
                }
                return actorBundle(src);
            },
            buildSphere: function(lcenter, radius, colorArray) {
                var ps = vtk.Filters.Sources.vtkSphereSource.newInstance({
                    center: lcenter ? this.xform.doTransform(lcenter) : [0, 0, 0],
                    radius: radius || 1,
                    thetaResolution: 16,
                    phiResolution: 16
                });

                var ab = actorBundle(ps);
                ab.actor.getProperty().setColor(colorArray[0], colorArray[1], colorArray[2]);
                ab.actor.getProperty().setLighting(false);
                return ab;
            },
            setPlane: function(planeBundle, labOrigin, labP1, labP2) {
                var vo = labOrigin ? this.xform.doTransform(labOrigin) : [0, 0, 0];
                var vp1 = labP1 ? this.xform.doTransform(labP1) : [0, 0, 1];
                var vp2 = labP2 ? this.xform.doTransform(labP2) : [1, 0, 0];
                planeBundle.source.setOrigin(vo[0], vo[1], vo[2]);
                planeBundle.source.setPoint1(vp1[0], vp1[1], vp1[2]);
                planeBundle.source.setPoint2(vp2[0], vp2[1], vp2[2]);
            },
        };
    };

    self.orientations = {
        horizontal: 'h',
        vertical: 'v'
    };

    // "Superclass" for representation of vtk source objects in viewport coordinates
    // Note this means that vpObjects are implicitly two-dimensional
    self.vpObject = function(vtkSource, renderer) {

        var vpObj = {};

        var worldCoord = vtk.Rendering.Core.vtkCoordinate.newInstance({
            renderer: renderer
        });
        worldCoord.setCoordinateSystemToWorld();

        vpObj.source = vtkSource;
        vpObj.wCoord = worldCoord;
        vpObj.initialVPEdges = {};

        // Override in subclass
        vpObj.edgesForDimension = function(dim) {
            return [];
        };

        vpObj.getEdges = function() {
            return {};
        };

        vpObj.getEdge = function(name) {
            return vpObj.getEdges()[name];
        };

        vpObj.initializeEdges = function(dim) {
            if(! this.initialVPEdges[dim]) {
                this.initialVPEdges[dim] = vpObj.vpEdgesForDimension(dim);
            }
        };

        vpObj.isReversed = function() {
            var revObj = {};
            geometry.basis.forEach(function (dim) {
                revObj[dim] = false;
            });
            return revObj;
        };

        vpObj.senseForEdgeAtIndex = function(dim, index, orientation) {
            if(orientation === self.orientations.vertical) {
                return -1;
            }
            var edge = this.initialVPEdges[dim][index];
            return edge.points()[0].x < edge.points()[1].x ? 1 : -1;
        };

        vpObj.localCoordFromWorld = function (point) {
            //srdbg('localCoordFromWorld point', point);
            // this is required to do conversions for different displays/devices
            var pixels = window.devicePixelRatio;
            vpObj.wCoord.setCoordinateSystemToWorld();
            vpObj.wCoord.setValue(point.coords());
            var lCoord = vpObj.wCoord.getComputedLocalDisplayValue();
            return geometry.point(lCoord[0] / pixels, lCoord[1] / pixels);
        };

        // Attaches a plotAxis to any of the named edges (an edge being a pair of points) -- when updated the axis will
        // shift and rotate along that edge.  The orientation indicates where for example
        // a z-axis starts (h[orizontal] or v[ertical]) before it is rotated into position.  This is
        // used for sorting and angle calculation.
        // edgeSelector is what determines which edge to use when updating
        //vpObj.bindAxis = function(axis, orientation, edgeNames, edgeSelector) {
        vpObj.bindAxis = function(axis, orientation, edgeNames, dynamicCorners) {
            function validateEdge(name) {
                if(! vpObj.getEdge(name)) {
                    throw 'No such edge ' + name;
                }
            }
            for(var nIndex = 0; nIndex < edgeNames.length; ++nIndex) {
                validateEdge(edgeNames[nIndex]);
            }

            var boundAxis = {};
            boundAxis.axis = axis;
            boundAxis.edges = edgeNames;
            boundAxis.orientation = orientation;
            boundAxis.minVal = axis.values[0];
            boundAxis.maxVal = axis.values[axis.values.length - 1];

            boundAxis.getEdge = function(name) {
                return vpObj.getEdge(name);
            };
            boundAxis.update = function(bounds, dynamicCorners, edgeSelector) {
                self.updateAxis(this, bounds, dynamicCorners, edgeSelector);
            };
            //boundAxis.update = function(bounds, edgeSelector) {
            //    self.updateAxis(this, bounds, edgeSelector);
            //};

            return boundAxis;
        };

        return vpObj;
    };

    // Takes a vtk cube source and renderer and returns a box in viewport coordinates with a bunch of useful
    // geometric properties and methods
    self.vpBox = function(vtkCubeSource, renderer) {

        var box = self.vpObject(vtkCubeSource, renderer);

        function wCenter() {
            return box.source.getCenter();
        }
        function wc() {
            return geometry.pointFromArr(box.source.getCenter());
        }

        // Convenience for looping
        function wLength() {
            return [
                box.source.getXLength(),
                box.source.getYLength(),
                box.source.getZLength()
            ];
        }
        function wl() {
            return {
                x: box.source.getXLength(),
                y: box.source.getYLength(),
                z: box.source.getZLength()
            };
        }

        function wCorners() {
            var ctr = wCenter();
            var corners = [];

            var sides = [-0.5, 0.5];
            var src = box.source;
            var len = wLength();
            for(var i in sides) {
                for (var j in sides) {
                    for (var k in sides) {
                        var s = [sides[k], sides[j], sides[i]];
                        var c = [];
                        for(var l = 0; l < 3; ++l) {
                            c.push(ctr[l] + s[l] * len[l]);
                        }
                        corners.push(c);
                    }
                }
            }
            //srdbg('wCorners', corners);
            return corners;
        }
        function wcrn() {
            var ctr = wc();
            var corners = [];

            var sides = [-0.5, 0.5];
            var src = box.source;
            var len = wLength();
            for(var i in sides) {
                for (var j in sides) {
                    for (var k in sides) {
                        var s = [sides[k], sides[j], sides[i]];
                        //srdbg('sides', s);
                        var c = [];
                        for(var l = 0; l < 3; ++l) {
                            c.push(ctr.coords()[l] + s[l] * len[l]);
                        }
                        corners.push(geometry.pointFromArr(c));
                    }
                }
            }
            return corners;
        }

        // a rectangle enclosing the screen representation of the box
        box.boundingRect = function() {
            var extrema = box.extr().x.concat(box.extr().y);
            var xCoords = [];
            var yCoords = [];
            extrema.forEach(function (arr) {
                arr.forEach(function (p) {
                    xCoords.push(p.x);
                    yCoords.push(p.y);
                });
            });
            return geometry.rect(
                geometry.point(Math.min.apply(null, xCoords), Math.min.apply(null, yCoords)),
                geometry.point(Math.max.apply(null, xCoords), Math.max.apply(null, yCoords))
            );
        };

        box.crns = function() {
            return wcrn();
        };


        var edgeCornerPairs = {
            x: [[0, 1], [5, 4], [2, 3], [7, 6]],
            y: [[0, 2], [1, 3], [4, 6], [5, 7]],
            z: [[0, 4], [5, 1], [2, 6], [7, 3]]
        };
        box.edgs = function () {
            var c = box.crns();
            var e = {};
            for(var dim in edgeCornerPairs ) {
                var lines = [];
                for(var j in  edgeCornerPairs[dim]) {
                    var p = edgeCornerPairs[dim][j];
                    var l = geometry.lineSegment(c[p[0]], c[p[1]]);
                    lines.push(l);
                }
                e[dim] = lines;
            }
            return e;
        };
        box.edgesForDimension = function (dim) {
            return box.edgs()[dim];
        };

        var revFn = box.isReversed;
        box.isReversed = function() {
            var revObj = revFn();
            geometry.basis.forEach(function (dim, i) {
                // only need one edge (?)
                // no, need to specify the edge
                var currentVector = box.vpEdgesForDimension(dim)[0].vector();
                var initVector = box.initialVPEdges[dim][0].vector();
                revObj[dim] = geometry.dotProduct(currentVector, initVector) < 0;
            });
            return revObj;
        };
        box.isEdgeReversed = function(dim, index) {
            var edge = box.vpEdgesForDimension(dim)[index];
            var currentVector = edge.vector();
            var initVector = geometry.vectsFromEdges(box.initialVPEdges[dim])[index];
            //srdbg(dim, index, 'edge rev', 'init', initVector, initEdge.slope(), 'curr', currentVector, edge.slope(), 'dot prod', geometry.dotProduct(currentVector, initVector));
            return geometry.dotProduct(currentVector, initVector) < 0;
        };

        box.vpEdgesForDimension = function (dim) {
            return vpEgds()[dim];
        };

        // an external edge has all other corners on the same side of the line it defines
        box.externalVpEdgesForDimension = function (dim) {
            var ext = [];
            box.vpEdgesForDimension(dim).forEach(function (edge, edgeIndex) {
                var numCorners = 0;
                var compCount = 0;
                for(var i in geometry.basis) {
                    var otherDim = geometry.basis[i];
                    if(otherDim === dim) {
                        continue;
                    }
                    var otherEdges = box.vpEdgesForDimension(otherDim);
                    for(var j = 0; j < otherEdges.length; ++j) {
                        var otherEdgeCorners = otherEdges[j].points();
                        for(var k = 0; k <= 1; ++k) {
                            var n = edge.line.comparePoint(otherEdgeCorners[k]);
                            compCount += n;
                            if(n !== 0) {
                                numCorners++;
                            }
                        }
                    }
                }
                if(Math.abs(compCount) === numCorners) {
                    ext.push(edge);
                }
                else {
                    ext.push(null);
                }
            });
            return ext;
        };
        box.vpCenterLineForDimension = function (dim) {
            return vpcls()[dim];
        };

        function vpCorners() {
            return wCorners().map(function (p) {
                return self.localCoordFromWorld(box.wCoord, p);
            });
        }
        function vpcrns() {
            return wcrn().map(function (p) {
                return box.localCoordFromWorld(p);
            });
        }
        function vpEgds() {
            var ee = {};
            var es = box.edgs();
            for(var e in es) {
                var wEdges = es[e];
                var lEdges = [];
                for(var i = 0; i < wEdges.length; ++i) {
                    var ls = wEdges[i];
                    var wpts = ls.points();
                    var lpts = [];
                    for(var j = 0; j < wpts.length; ++j) {
                        lpts.push(box.localCoordFromWorld(wpts[j]));
                    }
                    var lEdge = geometry.lineSegment(lpts[0], lpts[1]);
                    lEdges.push(lEdge);
                }
                ee[e] = lEdges;
            }
            return ee;
        }

        function wCenterLines() {
            var c = wCenter();
            var cls = [];
            var sides = [-0.5, 0.5];
            var l = wLength();
            for(var dim = 0; dim < 3; ++dim) {
                for(var i in sides) {
                    cls.push(
                        [
                            c[0] + (dim == 0 ? sides[i] : 0) * l[0],
                            c[1] + (dim == 1 ? sides[i] : 0) * l[1],
                            c[2] + (dim == 2 ? sides[i] : 0) * l[2]
                        ]
                    );
                }
            }
            return cls;
        }
        function vpcls() {
            var ctr = wc().coords();
            var cls = {};
            var lens = wl();
            var m = [
                [lens.x / 2, 0, 0],
                [0, lens.y / 2, 0],
                [0, 0, lens.z / 2]
            ];
            var tx = geometry.transform(m);
            for(var dim in geometry.basisVectors) {
                var txp = tx.doTransform(geometry.basisVectors[dim]);
                var p1 = box.localCoordFromWorld(geometry.pointFromArr(
                    geometry.vectorSubtract(ctr, txp)
                ));
                var p2 = box.localCoordFromWorld(geometry.pointFromArr(
                    geometry.vectorAdd(ctr, txp)
                ));
                cls[dim] = geometry.lineSegment(p1, p2);
            }
            return cls;
        }

        function vpCenterLines() {
            return wCenterLines().map(function (p) {
                return self.localCoordFromWorld(box.wCoord, p);
            });
        }

        // These member functions use descriptive names for the geometry,
        // to simplify usage

        // A list of the keys used by getCorners(), for convenience in specifying edge names
        box.corners = {
                leftBottomOut: 'leftBottomOut',
                leftTopOut: 'leftTopOut',
                rightTopOut: 'rightTopOut',
                rightBottomOut: 'rightBottomOut',
                leftBottomIn: 'leftBottomIn',
                leftTopIn: 'leftTopIn',
                rightTopIn: 'rightTopIn',
                rightBottomIn: 'rightBottomIn'
        };
        box.getCorners = function() {
            var cArr = vpCorners();
            var c = {};
            /*
            c[box.corners.leftBottomOut] = cArr[0];
            c[box.corners.leftTopOut] = cArr[1];
            c[box.corners.rightTopOut] = cArr[2];
            c[box.corners.rightBottomOut] = cArr[3];
            c[box.corners.leftBottomIn] = cArr[4];
            c[box.corners.leftTopIn] = cArr[5];
            c[box.corners.rightTopIn] = cArr[6];
            c[box.corners.rightBottomIn] = cArr[7];
            */

            c[box.corners.leftBottomOut] = cArr[4];
            c[box.corners.leftTopOut] = cArr[6];
            c[box.corners.rightTopOut] = cArr[7];
            c[box.corners.rightBottomOut] = cArr[5];
            c[box.corners.leftBottomIn] = cArr[0];
            c[box.corners.leftTopIn] = cArr[3];
            c[box.corners.rightTopIn] = cArr[2];
            c[box.corners.rightBottomIn] = cArr[1];
            return c;
            /*
            return {
                leftBottomOut: cArr[0],
                leftTopOut: cArr[1],
                rightTopOut: cArr[2],
                rightBottomOut: cArr[3],
                leftBottomIn: cArr[4],
                leftTopIn: cArr[5],
                rightTopIn: cArr[6],
                rightBottomIn: cArr[7]
            };
            */
        };

        box.extrema = {
                lowestCorners: 'lowestCorners',
                leftmostCorners: 'leftmostCorners',
                highestCorners: 'highestCorners',
                rightmostCorners: 'rightmostCorners'
        };
        box.getExtrema = function() {
            var corners = vpCorners();
            /*
            var e = {};
            e[box.extrema.lowestCorners] =  plotUtilities.extrema(corners, 1, true);
            e[box.extrema.leftmostCorners] =  plotUtilities.extrema(corners, 0, false);
            e[box.extrema.highestCorners] =  plotUtilities.extrema(corners, 1, false);
            e[box.extrema.rightmostCorners] =  plotUtilities.extrema(corners, 0, true);
            return e;
            */

            return {
                //lowestCorners: self.pointArrToObj(plotUtilities.extrema(corners, 1, true)),
                //leftmostCorners: self.pointArrToObj(plotUtilities.extrema(corners, 0, false)),
                //highestCorners: self.pointArrToObj(plotUtilities.extrema(corners, 1, false)),
                //rightmostCorners: self.pointArrToObj(plotUtilities.extrema(corners, 0, true))
                lowestCorners: plotUtilities.extrema(corners, 1, true),
                leftmostCorners: plotUtilities.extrema(corners, 0, false),
                highestCorners: plotUtilities.extrema(corners, 1, false),
                rightmostCorners: plotUtilities.extrema(corners, 0, true)
            };

        };
        // points on the screen that have the largest and smallest values in each dimension
        box.extr = function() {
            var ex = {};
            // just x and y
            var dims = geometry.basis.slice(0, 2);
            var rev = [false, true];
            dims.forEach(function (dim) {
                ex[dim] = [];
                for( var j in rev ) {
                    ex[dim].push(geometry.extrema(vpcrns(), dim, rev[j]));
                }
            });
            return ex;
        };

        // A list of the keys used by getEdges(), for convenience in specifying edge names
        box.edges = {
                bottomOut: 'bottomOut',
                bottomIn: 'bottomIn',
                topOut: 'topOut',
                topIn: 'topIn',
                leftBottom: 'leftBottom',
                rightBottom: 'rightBottom',
                leftTop: 'leftTop',
                rightTop: 'rightTop',
                leftOut: 'leftOut',
                leftIn: 'leftIn',
                rightOut: 'rightOut',
                rightIn: 'rightIn'
        };
        box.getEdges = function() {
            var corners = box.getCorners();
            var e = {};
            e[box.edges.bottomOut] = [corners.leftBottomOut, corners.rightBottomOut];
            e[box.edges.bottomIn] = [corners.leftBottomIn, corners.rightBottomIn];
            e[box.edges.topOut] = [corners.leftTopOut, corners.rightTopOut];
            e[box.edges.topIn] = [corners.leftTopIn, corners.rightTopIn];
            e[box.edges.leftBottom] = [corners.leftBottomOut, corners.leftBottomIn];
            e[box.edges.rightBottom] = [corners.rightBottomOut, corners.rightBottomIn];
            e[box.edges.leftTop] = [corners.leftTopOut, corners.leftTopIn];
            e[box.edges.rightTop] = [corners.rightTopOut, corners.rightTopIn];
            e[box.edges.leftOut] = [corners.leftBottomOut, corners.leftTopOut];
            e[box.edges.leftIn] = [corners.leftBottomIn, corners.leftTopIn];
            e[box.edges.rightOut] = [corners.rightBottomOut, corners.rightTopOut];
            e[box.edges.rightIn] = [corners.rightBottomIn, corners.rightTopIn];
            return e;
        };


        /*
        geometry.basis.forEach(function (dim) {
            initialVPEdges[dim] = box.vpEdgesForDimension(dim);
            initialVPVects[dim] = initialVPEdges[dim].map(function (e) {
                return e.vector();
            });
            srdbg(dim, 'initial edges', initialVPEdges[dim], 'vects', initialVPVects[dim]);
        });
        */
        return box;
    };

    // Attaches a plotAxis to any of the edges of the given viewport object -- when updated the axis will
    // shift and rotate along that edge.  The direction indicates where for example
    // a z-axis starts (h[orizontal] or v[ertical]) before it is rotated into position.  This is
    // used for sorting and angle calculation
    self.bindAxis = function(axis, vpObj, edgeNames, orientation) {
        function validateEdge(name) {
            if(! vpObj.getEdge(name)) {
                throw 'No such edge ' + name;
            }
        }
        for(var nIndex = 0; nIndex < edgeNames.length; ++nIndex) {
            validateEdge(edgeNames[nIndex]);
        }

        var boundAxis = {};
        boundAxis.axis = axis;
        boundAxis.obj = vpObj;
        boundAxis.edges = edgeNames;
        boundAxis.orientation = orientation;
        boundAxis.minVal = axis.values[0];
        boundAxis.maxVal = axis.values[axis.values.length - 1];

        // invoke these to get "live" values of the edges
        boundAxis.getEdge = function(name) {
            return vpObj.getEdge(name);
        };
        boundAxis.getEdges = function() {
            return boundAxis.edges.map(function (name) {
                return boundAxis.getEdge(name);
            });
        };

        return boundAxis;
    };

    // Attaches a plotAxis to any of the edges of the given viewport object -- when updated the axis will
    // shift and rotate along that edge.  The direction indicates where for example
    // a z-axis starts (h[orizontal] or v[ertical]) before it is rotated into position.  This is
    // used for sorting and angle calculation
    self.ba = function(d3axis, vpObj, dimension, orientation) {

        var e = vpObj.edgesForDimension(dimension);
        if(! e || e.length === 0) {
            throw dimension + ': Object has no edges associated with that dimension';
        }
        var boundAxis = {};
        boundAxis.axis = d3axis;
        boundAxis.obj = vpObj;
        boundAxis.edges = e;
        boundAxis.dimension = dimension;
        boundAxis.orientation = orientation;
        boundAxis.minVal = d3axis.values[0];
        boundAxis.maxVal = d3axis.values[d3axis.values.length - 1];

        // invoke these to get "live" values of the edges
        boundAxis.getEdges = function() {
            return vpObj.edgesForDimension(dimension);
        };

        return boundAxis;
    };

    // Updates the axis position within the given bounds.  The
    // dynamic corners are those, in order of preference, that currently
    // determine which edge (provided above) is selected
    //self.updateAxis  = function(boundAxis, bounds, dynamicCorners, edgeSelector, selectorData) {
    //self.updateAxis  = function(boundAxis, bounds, edgeSelector, selectorData) {
    self.updateAxis  = function(boundAxis, edgeSelector, edgeSorter) {

        var projLen = 0;
        var axisGeom = {};
        var isReversed = false;
        var sceneEnds = [[0, 0], [0, 0]];
        var screenEnds = sceneEnds;
        var clippedEnds = sceneEnds;
        var sceneLen = 0;
        var showAxisEnds = false;

        // this needs to be done just-in-time so that the values of the points
        // are current
        var boundEdges = boundAxis.getEdges();

        // If any of the bound edges now has the original left (top) point now right of (below)
        // the original right (bottom) point, the image is reversed on the screen
        if(boundAxis.orientation == self.orientations.horizontal) {
            isReversed = boundEdges[0][0][0] >  boundEdges[0][0][1];
        }
        if(boundAxis.orientation == self.orientations.vertical) {
            isReversed = boundEdges[0][0][1] < boundEdges[0][1][1];
        }

        var edgeProps = edgeSelector.select(boundEdges, edgeSorter);

        if(! edgeProps) {
            return false;
        }

        // all the edges that we want to bind to are offscreen, so we will show little markers in the
        // middle to indicate the range of values without clutter
            /*
        else {
            showAxisEnds = true;
            //sceneEnds = plotUtilities.sortInDimension(vpLeftRight, 0);
            screenEnds = plotUtilities.boundsIntersections(bounds, sceneEnds[0], sceneEnds[1]);
            clippedEnds = plotUtilities.sortInDimension(
                plotUtilities.edgesInsideBounds(screenEnds, bounds),
                0, false);
            axisGeom.left = Math.max(sceneEnds[0][0], clippedEnds[0][0]);
            axisGeom.top = axisGeom.left == sceneEnds[0][0] ? sceneEnds[0][1] : clippedEnds[0][1];
            axisGeom.right = Math.min(sceneEnds[1][0], clippedEnds[1][0]);
            axisGeom.bottom = axisGeom.right == sceneEnds[1][0] ? sceneEnds[1][1] : clippedEnds[1][1];
            projLen = plotUtilities.dist([axisGeom.left, axisGeom.top], [axisGeom.right, axisGeom.bottom]);
            sceneLen = plotUtilities.dist(sceneEnds[0], sceneEnds[1]);
            var tanPsi = (sceneEnds[0][1] - sceneEnds[1][1]) / (sceneEnds[0][0] - sceneEnds[1][0]);
            axisGeom.angle = 180 * Math.atan(tanPsi) / Math.PI;
        }
        */

            ///srdbg('selected', edgeProps);
            axisGeom = axisGeometery(boundAxis, edgeProps);
        //srdbg('axis', axisGeom);

        // TODO(mvk): plotAxis should handle arbitrary rotated axes instead of doing it here
        var range = Math.min(axisGeom.length, plotUtilities.dist(edgeProps.sceneEnds[0], edgeProps.sceneEnds[1]));

        // Change the domain if axis ends go offscreen

        var newMin = boundAxis.minVal;
        var newMax = boundAxis.maxVal;
        var domainPct = 0.0;
        var domainPart = 0.0;
        /*
        if(! plotUtilities.isPointWithinBounds(edgeProps.sceneEnds[0], bounds)) {
            //srdbg('projected pct', domainPct);
            domainPct = plotUtilities.dist(edgeProps.sceneEnds[0], edgeProps.clippedEnds[0]) / edgeProps.sceneLen;
            domainPart = (boundAxis.maxVal - boundAxis.minVal) * domainPct;
            if(isReversed) {
                newMax = boundAxis.maxVal - domainPart;
            }
            else {
                newMin = boundAxis.minVal + domainPart;
            }
        }
        if(! plotUtilities.isPointWithinBounds(edgeProps.sceneEnds[1], bounds)) {
            domainPct = plotUtilities.dist(edgeProps.sceneEnds[1], edgeProps.clippedEnds[1]) / edgeProps.sceneLen;
            domainPart = (boundAxis.maxVal - boundAxis.minVal) * domainPct;
            if(isReversed) {
                newMin = boundAxis.minVal + domainPart;
            }
            else {
               newMax = boundAxis.maxVal - domainPart;
            }
        }
*/
        /*
        axis.scale.domain([newMin, newMax]).nice();
        axis.scale.range([isXReversed ? xrange : 0, isXReversed ? 0 :xrange]);
        // we use the axis for calculations but show no ticks if both ends are off-screen
        if(showXAxisEnds) {
            axis.svgAxis.ticks(0);
            select('.x.axis').call(axis.svgAxis);
        }
        else {
            axes.x.updateLabelAndTicks({
                width: xrange,
                height: 0
            }, select);
        }

        // adjust axis position to account for tick labels
        var xlabels = d3self.selectAll('.x.axis text');
        var xxform = 'translate(' +
            Math.min(xAxisLeft, xAxisRight) + ',' +
            xAxisTop +') ' +
            'rotate(' + xAxisAngle + ')';
        //srdbg('show ends?', showXAxisEnds);
        select('.x.axis').attr('transform', xxform);

*/
        return true;
    };

   self.ua  = function(boundAxis, edgeSelector, edgeSorter) {

        var projLen = 0;
        var axisGeom = {};
        var isReversed = false;
        var sceneEnds = [geometry.point(0, 0), geometry.point(0, 0)];
        var screenEnds = sceneEnds;
        var clippedEnds = sceneEnds;
        var sceneLen = 0;
        var showAxisEnds = false;

        // this needs to be done just-in-time so that the values of the points
        // are current
        var boundEdges = boundAxis.getEdges();

        // If any of the bound edges now has the original left (top) point now right of (below)
        // the original right (bottom) point, the image is reversed on the screen
        if(boundAxis.orientation == self.orientations.horizontal) {
            isReversed = boundEdges.x[0][0] >  boundEdges.x[0][1];
        }
        if(boundAxis.orientation == self.orientations.vertical) {
            isReversed = boundEdges.y[0][1] < boundEdges.y[1][1];
        }

        var edgeProps = edgeSelector.select(boundEdges, edgeSorter);

        if(! edgeProps) {
            return false;
        }

        // all the edges that we want to bind to are offscreen, so we will show little markers in the
        // middle to indicate the range of values without clutter
            /*
        else {
            showAxisEnds = true;
            //sceneEnds = plotUtilities.sortInDimension(vpLeftRight, 0);
            screenEnds = plotUtilities.boundsIntersections(bounds, sceneEnds[0], sceneEnds[1]);
            clippedEnds = plotUtilities.sortInDimension(
                plotUtilities.edgesInsideBounds(screenEnds, bounds),
                0, false);
            axisGeom.left = Math.max(sceneEnds[0][0], clippedEnds[0][0]);
            axisGeom.top = axisGeom.left == sceneEnds[0][0] ? sceneEnds[0][1] : clippedEnds[0][1];
            axisGeom.right = Math.min(sceneEnds[1][0], clippedEnds[1][0]);
            axisGeom.bottom = axisGeom.right == sceneEnds[1][0] ? sceneEnds[1][1] : clippedEnds[1][1];
            projLen = plotUtilities.dist([axisGeom.left, axisGeom.top], [axisGeom.right, axisGeom.bottom]);
            sceneLen = plotUtilities.dist(sceneEnds[0], sceneEnds[1]);
            var tanPsi = (sceneEnds[0][1] - sceneEnds[1][1]) / (sceneEnds[0][0] - sceneEnds[1][0]);
            axisGeom.angle = 180 * Math.atan(tanPsi) / Math.PI;
        }
        */

            ///srdbg('selected', edgeProps);
            axisGeom = axisGeometery(boundAxis, edgeProps);
        //srdbg('axis', axisGeom);

        // TODO(mvk): plotAxis should handle arbitrary rotated axes instead of doing it here
        var range = Math.min(axisGeom.length, plotUtilities.dist(edgeProps.sceneEnds[0], edgeProps.sceneEnds[1]));

        // Change the domain if axis ends go offscreen

        var newMin = boundAxis.minVal;
        var newMax = boundAxis.maxVal;
        var domainPct = 0.0;
        var domainPart = 0.0;
        /*
        if(! plotUtilities.isPointWithinBounds(edgeProps.sceneEnds[0], bounds)) {
            //srdbg('projected pct', domainPct);
            domainPct = plotUtilities.dist(edgeProps.sceneEnds[0], edgeProps.clippedEnds[0]) / edgeProps.sceneLen;
            domainPart = (boundAxis.maxVal - boundAxis.minVal) * domainPct;
            if(isReversed) {
                newMax = boundAxis.maxVal - domainPart;
            }
            else {
                newMin = boundAxis.minVal + domainPart;
            }
        }
        if(! plotUtilities.isPointWithinBounds(edgeProps.sceneEnds[1], bounds)) {
            domainPct = plotUtilities.dist(edgeProps.sceneEnds[1], edgeProps.clippedEnds[1]) / edgeProps.sceneLen;
            domainPart = (boundAxis.maxVal - boundAxis.minVal) * domainPct;
            if(isReversed) {
                newMin = boundAxis.minVal + domainPart;
            }
            else {
               newMax = boundAxis.maxVal - domainPart;
            }
        }
*/
        /*
        axis.scale.domain([newMin, newMax]).nice();
        axis.scale.range([isXReversed ? xrange : 0, isXReversed ? 0 :xrange]);
        // we use the axis for calculations but show no ticks if both ends are off-screen
        if(showXAxisEnds) {
            axis.svgAxis.ticks(0);
            select('.x.axis').call(axis.svgAxis);
        }
        else {
            axes.x.updateLabelAndTicks({
                width: xrange,
                height: 0
            }, select);
        }

        // adjust axis position to account for tick labels
        var xlabels = d3self.selectAll('.x.axis text');
        var xxform = 'translate(' +
            Math.min(xAxisLeft, xAxisRight) + ',' +
            xAxisTop +') ' +
            'rotate(' + xAxisAngle + ')';
        //srdbg('show ends?', showXAxisEnds);
        select('.x.axis').attr('transform', xxform);

*/
        return true;
   };

    function axisGeometery(boundAxis, edgeProps) {
        var left = 0;  var top = 0;
        var right = 0;  var bottom = 0;
        var length = 0;  var angle = 0;

        var tanAngle = (edgeProps.sceneEnds[0][1] - edgeProps.sceneEnds[1][1]) / (edgeProps.sceneEnds[0][0] - edgeProps.sceneEnds[1][0]);
        if(boundAxis.orientation == self.orientations.horizontal) {
            if(edgeProps.sceneEnds[0][0] > edgeProps.clippedEnds[0][0]) {
                left = edgeProps.sceneEnds[0][0];
                top = edgeProps.sceneEnds[0][1];
            }
            else {
                left = edgeProps.clippedEnds[0][0];
                top = edgeProps.clippedEnds[0][1];
            }
            if(edgeProps.sceneEnds[1][0] < edgeProps.clippedEnds[1][0]) {
                right = edgeProps.sceneEnds[1][0];
                bottom = edgeProps.sceneEnds[1][1];
            }
            else {
                right = edgeProps.clippedEnds[1][0];
                bottom = edgeProps.clippedEnds[1][1];
            }
            angle = 180 * Math.atan(tanAngle) / Math.PI;
        }
        if(boundAxis.orientation == self.orientations.vertical) {
            if(edgeProps.sceneEnds[0][1] > edgeProps.clippedEnds[0][1]) {
                left = edgeProps.sceneEnds[0][0];
                top = edgeProps.sceneEnds[0][1];
            }
            else {
                left = edgeProps.clippedEnds[0][0];
                top = edgeProps.clippedEnds[0][1];
            }
            if(edgeProps.sceneEnds[1][1] < edgeProps.clippedEnds[1][1]) {
                right = edgeProps.sceneEnds[1][0];
                bottom = edgeProps.sceneEnds[1][1];
            }
            else {
                right = edgeProps.clippedEnds[1][0];
                bottom = edgeProps.clippedEnds[1][1];
            }
            angle = 180 * Math.atan(tanAngle) / Math.PI - 90;
            if(angle < -90 ) {
                angle += 180;
            }
        }
        length = plotUtilities.dist([left, top], [right, bottom]);

        return {
            left: left,
            top: top,
            right: right,
            bottom: bottom,
            length: length,
            angle: angle,

        };
    }

    function ag(boundAxis, edgeProps) {
        var left = 0;  var top = 0;
        var right = 0;  var bottom = 0;
        var length = 0;  var angle = 0;

        var tanAngle = (edgeProps.sceneEnds[0][1] - edgeProps.sceneEnds[1][1]) / (edgeProps.sceneEnds[0][0] - edgeProps.sceneEnds[1][0]);
        if(boundAxis.orientation == self.orientations.horizontal) {
            if(edgeProps.sceneEnds[0][0] > edgeProps.clippedEnds[0][0]) {
                left = edgeProps.sceneEnds[0][0];
                top = edgeProps.sceneEnds[0][1];
            }
            else {
                left = edgeProps.clippedEnds[0][0];
                top = edgeProps.clippedEnds[0][1];
            }
            if(edgeProps.sceneEnds[1][0] < edgeProps.clippedEnds[1][0]) {
                right = edgeProps.sceneEnds[1][0];
                bottom = edgeProps.sceneEnds[1][1];
            }
            else {
                right = edgeProps.clippedEnds[1][0];
                bottom = edgeProps.clippedEnds[1][1];
            }
            angle = 180 * Math.atan(tanAngle) / Math.PI;
        }
        if(boundAxis.orientation == self.orientations.vertical) {
            if(edgeProps.sceneEnds[0][1] > edgeProps.clippedEnds[0][1]) {
                left = edgeProps.sceneEnds[0][0];
                top = edgeProps.sceneEnds[0][1];
            }
            else {
                left = edgeProps.clippedEnds[0][0];
                top = edgeProps.clippedEnds[0][1];
            }
            if(edgeProps.sceneEnds[1][1] < edgeProps.clippedEnds[1][1]) {
                right = edgeProps.sceneEnds[1][0];
                bottom = edgeProps.sceneEnds[1][1];
            }
            else {
                right = edgeProps.clippedEnds[1][0];
                bottom = edgeProps.clippedEnds[1][1];
            }
            angle = 180 * Math.atan(tanAngle) / Math.PI - 90;
            if(angle < -90 ) {
                angle += 180;
            }
        }
        length = plotUtilities.dist([left, top], [right, bottom]);

        return {
            left: left,
            top: top,
            right: right,
            bottom: bottom,
            length: length,
            angle: angle,
        };
    }

    self.addActors = function(renderer, actorArr) {
        actorArr.forEach(function(actor) {
            self.addActor(renderer, actor);
        });
    };

    self.addActor = function(renderer, actor) {
        if(! actor) {
            return;
        }
        renderer.addActor(actor);
    };

    self.removeActors = function(renderer, actorArr) {
        if(! actorArr ) {
            return;
        }
        actorArr.forEach(function(actor) {
            self.removeActor(renderer, actor);
        });
        actorArr.length = 0;
    };

    self.removeActor = function(renderer, actor) {
        if(! actor ) {
            return;
        }
        renderer.removeActor(actor);
    };

    self.showActors = function(renderWindow, arr, doShow, visibleOpacity, hiddenOpacity) {
        arr.forEach(function (a) {
            self.showActor(renderWindow, a, doShow, visibleOpacity, hiddenOpacity, true);
        });
        renderWindow.render();
    };

    self.showActor = function(renderWindow, a, doShow, visibleOpacity, hiddenOpacity, waitToRender) {
        a.getProperty().setOpacity(doShow ? visibleOpacity || 1.0 : hiddenOpacity || 0.0);
        if(! waitToRender) {
            renderWindow.render();
        }
    };

    self.localCoordFromWorld = function (vtkCoord, point) {
        // this is required to do conversions for different displays/devices
        //srdbg('localCoordFromWorld point', point);
        var pixels = window.devicePixelRatio;
        vtkCoord.setCoordinateSystemToWorld();
        vtkCoord.setValue(point);
        var lCoord = vtkCoord.getComputedLocalDisplayValue();
        return [lCoord[0] / pixels, lCoord[1] / pixels];
    };
    self.lcfw = function (vtkCoord, point) {
        //srdbg('localCoordFromWorld point', point);
        // this is required to do conversions for different displays/devices
        var pixels = window.devicePixelRatio;
        vtkCoord.setCoordinateSystemToWorld();
        vtkCoord.setValue(point.coords());
        var lCoord = vtkCoord.getComputedLocalDisplayValue();
        return geometry.point(lCoord[0] / pixels, lCoord[1] / pixels);
    };

    self.worldCoordFromLocal = function (coord, point, view) {
        var pixels = window.devicePixelRatio;
        var newPoint = [pixels * point[0], pixels * point[1]];
        // must first convert from "localDisplay" to "display"  - this is the inverse of
        // what is done by vtk to get from display to localDisplay
        var newPointView = [newPoint[0], view.getFramebufferSize()[1] - newPoint[1] - 1];
        coord.setCoordinateSystemToDisplay();
        coord.setValue(newPointView);
        return coord.getComputedWorldValue();
    };

    return self;
});

// General-purpose vtk display
SIREPO.app.directive('vtkDisplay', function(appState, panelState, requestSender, frameCache, plotting, vtkManager, vtkPlotting, layoutService, utilities, plotUtilities, geometry, appVTKService) {

    return {
        restrict: 'A',
        //transclude: {
        //    visabilityControlSlot: '?visabilityControl',
        //},
        scope: {
            modelName: '@',
        },
        templateUrl: '/static/html/vtk-display.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope, $element) {

            var svc = vtkManager.getService($scope.modelName) || appVTKService;

            var d3self;
            var X_Z_ASPECT_RATIO = 4.0 / 7.0;
            var yzAspectRatio = 1;
            $scope.margin = {top: 50, right: 23, bottom: 50, left: 75};
            $scope.width = $scope.height = 0;
            $scope.axesMargins = {
                x: { width: 16.0, height: 0.0 },
                y: { width: 0.0, height: 16.0 }
            };

            // little test boxes are useful for translating vtk space to screen space
            $scope.testBoxes = [];

            $scope.side = 'y';
            $scope.xdir = 1;  $scope.ydir = 1;  $scope.zdir = 1;

            // these become functions in app
            $scope.showAbsorbed = true;
            $scope.showReflected = true;
            $scope.showImpact = true;
            $scope.showConductors = true;

            // bundles or actors?
            $scope.showActors = function (actors, doShow) {

            };

            // to speed renders, only draw lines between every <joinEvery> data points
            //TODO(mvk): one actor with all the lines
            function getJoinEvery() {
                return appState.models.particle3d.joinEvery || 5;
            }

            // these are in screen/vtk coords, not lab coords
            //var axes = {
            //    x: layoutService.plotAxis($scope.margin, 'x', 'bottom', svc.refresh, utilities),
            //    y: layoutService.plotAxis($scope.margin, 'y', 'left', svc.refresh, utilities),
            //    z: layoutService.plotAxis($scope.margin, 'z', 'bottom', svc.refresh, utilities)
            //};

            // supplied by service
            var boundAxes = svc.getBoundAxes();

            // rendering
            var fsRenderer = null;
            var renderWindow = null;
            var mainView = null;
            var renderer = null;
            var cam = null;
            var camPos = [0, 0, 1];
            var camViewUp = [0, 1, 0];
            var actors = [];
            var bundles = [];  // defined by service

            // geometry
            var coordMapper = vtkPlotting.coordMapper();

            var zoomUnits = 0;
            var didPan = false;
            var minZoomUnits = -256;
            var maxZoomUnits = 256;

            document.addEventListener(utilities.fullscreenListenerEvent(), refresh);

            $scope.init = function() {
                d3self = d3.selectAll($element);

                var rw = angular.element($($element).find('.sr-plot-particle-3d .vtk-canvas-holder'))[0];
                fsRenderer = vtk.Rendering.Misc.vtkFullScreenRenderWindow.newInstance({
                    background: [1, 1, 1, 1],
                    container: rw
                });
                renderer = fsRenderer.getRenderer();
                vtkManager.setRenderer($scope.modelName, renderer);
                renderer.getLights()[0].setLightTypeToSceneLight();
                renderWindow = fsRenderer.getRenderWindow();
                mainView = renderWindow.getViews()[0];

                cam = renderer.get().activeCamera;

                rw.addEventListener('dblclick', reset);

                var worldCoord = vtk.Rendering.Core.vtkCoordinate.newInstance({
                    renderer: renderer
                });
                worldCoord.setCoordinateSystemToWorld();

                var isDragging = false;
                rw.onpointerdown = function (evt) {
                    isDragging = true;
                };
                rw.onpointermove = function (evt) {
                    if (!isDragging) {
                        return;
                    }
                    didPan = didPan || evt.shiftKey;
                    $scope.side = null;
                    utilities.debounce(refresh, 100)();
                };
                rw.onpointerup = function (evt) {
                    isDragging = false;
                    refresh();
                };
                rw.onwheel = function (evt) {
                    var camPos = cam.getPosition();

                    // If zoom needs to be halted or limited, it can be done here.  For now track the "zoom units"
                    // for managing refreshing and resetting
                    zoomUnits += evt.deltaY;

                    utilities.debounce(refresh, 100)();
                };

                if(svc.useOrientationMarker) {
                    var orientationMarker = vtk.Interaction.Widgets.vtkOrientationMarkerWidget.newInstance({
                        actor: vtk.Rendering.Core.vtkAxesActor.newInstance(),
                        interactor: renderWindow.getInteractor()
                    });
                    orientationMarker.setEnabled(true);
                    orientationMarker.setViewportCorner(
                        vtk.Interaction.Widgets.vtkOrientationMarkerWidget.Corners.TOP_RIGHT
                    );
                    orientationMarker.setViewportSize(0.08);
                    orientationMarker.setMinPixelSize(100);
                    orientationMarker.setMaxPixelSize(300);
                }
                svc.init($scope);
            };

            // move load to vtk svc
            $scope.load = svc.load;
            /*
            $scope.load = function() {

                //srdbg('display load');
                $scope.dataCleared = false;

                vtkPlotting.removeActors(renderer, actors);
                actors = [];

                // provided or build from input from app
                var axisInfo = svc.getAxisInfo();

                //svc.updateScene(coordMapper, axisInfo);
                var joinEvery = getJoinEvery();

                /STAR
                // do in app vtk svc
                for (var dim in axes) {
                    var info = axisInfo[dim];
                    axes[dim].init();
                    axes[dim].svgAxis.tickSize(0);
                    axes[dim].values = plotting.linearlySpacedArray(info.min, info.max, info.numPoints);
                    axes[dim].scale.domain([info.min, info.max]);
                    axes[dim].parseLabelAndUnits(info.label);

                    boundAxes[dim] = vtkPlotting.ba(
                        axes[dim],
                        null, //vpOutline,  // SUPPLY OBJECT TO BIND
                        dim,
                        axisInfo[dim].orientation
                    );
                }
                STAR/

            };
            */
            $scope.vtkCanvasGeometry = function () {
                var vtkCanvasHolder = $($element).find('.vtk-canvas-holder')[0];
                return {
                    pos: $(vtkCanvasHolder).position(),
                    size: {
                        width: $(vtkCanvasHolder).width(),
                        height: $(vtkCanvasHolder).height()
                    }
                };
            };
            function refresh() {
                var width = parseInt($($element).css('width')) - $scope.margin.left - $scope.margin.right;
                $scope.width = plotting.constrainFullscreenSize($scope, width, X_Z_ASPECT_RATIO);
                $scope.height = X_Z_ASPECT_RATIO * $scope.width;

                var vtkCanvasHolderSize = {
                    width: $('.vtk-canvas-holder').width(),
                    height: $('.vtk-canvas-holder').height()
                };
                var vtkCanvasHolderBounds = {
                    left: $scope.axesMargins.x.width,
                    top: $scope.axesMargins.y.height,
                    right: vtkCanvasHolderSize.width - $scope.axesMargins.x.width,
                    bottom: vtkCanvasHolderSize.height - $scope.axesMargins.y.height
                };
                var vchb = geometry.rect(
                    geometry.point(
                        $scope.axesMargins.x.width,
                        $scope.axesMargins.y.height
                    ),
                    geometry.point(
                        vtkCanvasHolderSize.width - $scope.axesMargins.x.width,
                        vtkCanvasHolderSize.height - $scope.axesMargins.y.height
                    )
                );

                var vtkCanvasSize = {
                    width: $scope.width + $scope.margin.left + $scope.margin.right,
                    height: $scope.height + $scope.margin.top + $scope.margin.bottom
                };
                var axisMax = {
                    x: vtkCanvasHolderSize.width - 2 * $scope.axesMargins.x.width,
                    y: vtkCanvasHolderSize.height - 2 * $scope.axesMargins.y.height,
                    z: 200,
                };

                // If an axis is shorter than this, don't display it -- the ticks will
                // be cramped and unreadable
                var minAxisDisplayLen = 50;

                select('.vtk-canvas-holder svg')
                    .attr('width', vtkCanvasSize.width)
                    .attr('height', vtkCanvasSize.height);

                // Note that vtk does not re-add actors to the renderer if they already exist
                vtkPlotting.addActors(renderer, actors);
                vtkPlotting.showActors(renderWindow, actors, $scope.showActors(actors, true));

                // reset camera will negate zoom and pan but *not* rotation
                if (zoomUnits == 0 && !didPan) {
                    renderer.resetCamera();
                }
                renderWindow.render();

                // selectors here or in app or predefined?
                //boundAxes.forEach(function (ba) {
                //    vtkPlotting.updateAxis(ba, null, null);
                //});


                // TODO (mvk): move axis stuff above to the refreshAxes function
                refreshAxes();

                // TODO: use feature_config to restrict this to dev
                if (SIREPO.APP_SCHEMA.feature_config.display_test_boxes) {
                    $scope.testBoxes = [
                        /*
                        {
                            x: xAxisLeft, //clippedXEnds[0][0],
                            y: xAxisTop, //clippedXEnds[0][1],
                            color: "red"
                        },
                        {
                            x: xAxisRight, //clippedXEnds[1][0],
                            y: xAxisBottom, //clippedXEnds[1][1],
                            color: "blue"
                        },
                        */
                    ];

                }
            }

            // Selects the first edge (if any) that has corners in common with those
            // in cornerArr and fits inside the bounds
            function crnsel(cornerArr, rect) {
                var selector = {};
                var selection = {};
                selector.select = function (edgeArr, sorter) {
                    cornerArr.forEach(function (corners) {
                        selection.edge = geometry.firstEdgeWithCorners(edgeArr, cornerArr[corners]);
                        selection.sceneEnds = sorter(selection.edge);
                        selection.sceneEndsInBounds = selection.sceneEnds.map(function (p) {
                            return p.isInRect(rect);
                        });
                        selection.sceneLen = selection.sceneEnds[0].dist(selection.sceneEnds[1]);
                        selection.screenEnds = rect.boundaryIntersectons(selection.sceneEnds[0], selection.sceneEnds[1]);
                        selection.clippedEnds = sorter(rect.segmentsInside(selection.screenEnds));
                        if (selection.clippedEnds && selection.clippedEnds.length == 2) {
                            return selection;
                        }

                    });
                };
                return selector;
            }

            //
            function centerSelector(bounds) {
                var selector = {};
                var selection = {};
                var boundsCtr = [(bounds.right - bounds.left) / 2.0, (bounds.bottom - bounds.top) / 2.0];
                selector.select = function (edgeArr, sorter) {
                    var firstEdge = edgeArr[0];
                    var dx = firstEdge[0][0] - firstEdge[1][0];
                    var dy = firstEdge[0][1] - firstEdge[1][1];
                    selection.edge = [
                        [boundsCtr[0] - dx / 2, boundsCtr[1] - dy / 2],
                        [boundsCtr[0] + dx / 2, boundsCtr[1] + dy / 2]
                    ];
                    selection.sceneEnds = sorter(selection.edge);
                    selection.screenEnds = plotUtilities.boundsIntersections(bounds, selection.sceneEnds[0], selection.sceneEnds[1]);
                    selection.clippedEnds = sorter(plotUtilities.edgesInsideBounds(selection.screenEnds, bounds));
                    return selection;
                };
                return selector;
            }

            function cornerSorter(sortDimension, reverse) {
                return function (pArr) {
                    return plotUtilities.sortInDimension(pArr, sortDimension, reverse || false);
                };
            }

            function crnsrt(sortDimension, doReverse) {
                return function (arr) {
                    return geometry.sortInDimension(arr, sortDimension, doReverse || false);
                };
            }

            // Find where the "scene" (bounds of the rendered objects) intersects the screen (viewport)
            // Returns the properties of the first set of corners that fit - order them by desired location.
            // Could be none fit, in which case no properties are defined
            function propertiesOfEdges(vpEdges, cornersArr, bounds, dim, reverse) {
                var props = {};
                for (var corners in cornersArr) {
                    var edges = plotUtilities.edgesWithCorners(vpEdges, cornersArr[corners])[0];
                    if (!edges) {
                        continue;
                    }
                    var sceneEnds = plotUtilities.sortInDimension(edges, dim);
                    var screenEnds = plotUtilities.boundsIntersections(bounds, sceneEnds[0], sceneEnds[1]);
                    var sceneLen = plotUtilities.dist(sceneEnds[0], sceneEnds[1]);
                    var clippedEnds = plotUtilities.sortInDimension(
                        plotUtilities.edgesInsideBounds(screenEnds, bounds),
                        dim, reverse);
                    if (clippedEnds && clippedEnds.length == 2) {
                        var clippedLen = plotUtilities.dist(clippedEnds[0], clippedEnds[1]);
                        if (clippedLen / sceneLen > 0.5) {
                            props.edges = edges;
                            props.sceneEnds = sceneEnds;
                            props.screenEnds = screenEnds;
                            props.sceneLen = sceneLen;
                            props.clippedEnds = clippedEnds;
                            return props;
                        }
                    }
                }
                return props;
            }

            function refreshAxes() {
            }

            // takes the result of a d3.selectAll
            function maxLabelLen(lSelect) {
                return Math.max.apply(null, lSelect[0].map(function (item) {
                    return item.textContent.length;
                }));
            }

            function reset() {
                camPos = [0, 0, 1];
                camViewUp = [0, 1, 0];
                $scope.side = 'y';
                $scope.xdir = 1;
                $scope.ydir = 1;
                $scope.zdir = 1;
                resetCam();
            }

            function resetCam() {
                cam.setPosition(camPos[0], camPos[1], camPos[2]);
                cam.setFocalPoint(0, 0, 0);
                cam.setViewUp(camViewUp[0], camViewUp[1], camViewUp[2]);
                cam.zoom(1.3);
                renderer.resetCamera();
                zoomUnits = 0;
                didPan = false;
                //orientationMarker.updateMarkerOrientation();
                refresh();
            }

            function resetZoom() {
            }

            $scope.clearData = function () {
            };

            $scope.destroy = function () {
                document.removeEventListener(utilities.fullscreenListenerEvent(), refresh);
                var rw = angular.element($($element).find('.sr-plot-particle-3d .vtk-canvas-holder'))[0];
                rw.removeEventListener('dblclick', reset);
                $element.off();
                vtkManager.removeRenderer($scope.modelName);
                fsRenderer.getInteractor().unbindEvents();
                fsRenderer.delete();
            };

            $scope.resize = function () {
                refresh();
            };

            $scope.toggleActors = function () {
                vtkPlotting.showActors(actors, true);
            };


            $scope.xdir = 1;
            $scope.ydir = 1;
            $scope.zdir = 1;
            $scope.side = 'y';
            $scope.showSide = function (side) {
                var dir = side === 'x' ? $scope.xdir : (side === 'y' ? $scope.ydir : $scope.zdir);
                if (side == $scope.side) {
                    dir *= -1;
                    if (side === 'x') {
                        $scope.xdir = dir;
                    }
                    if (side === 'y') {
                        $scope.ydir = dir;
                    }
                    if (side === 'z') {
                        $scope.zdir = dir;
                    }
                }
                $scope.side = side;

                camPos = side === 'x' ? [0, dir, 0] : (side === 'y' ? [0, 0, dir] : [dir, 0, 0]);
                camViewUp = side === 'x' ? [0, 0, 1] : [0, 1, 0];
                resetCam();
            };

            $scope.mode = 'move';
            $scope.selectMode = function (mode) {
                $scope.mode = mode;
            };

            function select(selector) {
                var e = d3.select($scope.element);
                return selector ? e.select(selector) : e;
            }

        },

        link: function link(scope, element) {
            vtkPlotting.vtkPlot(scope, element);
        },
    };
});

// will be axis display
SIREPO.app.directive('vtkAxes', function(appState, panelState, requestSender, frameCache, plotting, vtkManager, vtkPlotting, layoutService, utilities, plotUtilities, geometry) {

    return {
        restrict: 'A',
        scope: {
            width: '<',
            height: '<',
            vtkObj: '<',
        },
        template: [
            '<g data-ng-repeat="dim in geometry.basis" class="{{ dim }} axis"></g>',
            '<text class="{{ dim }}-axis-label"></text>',
            '<text class="{{ dim }} axis-end low"></text>',
            '<text class="{{ dim }} axis-end high"></text>',
        ].join(''),
        controller: function($scope, $element) {
        },

    };
});

// will be axis functions
SIREPO.app.service('vtkAxisService', function(appState, panelState, requestSender, frameCache, plotting, vtkManager, vtkPlotting, layoutService, utilities, plotUtilities, geometry) {
    var svc = {};
    return svc;
});
