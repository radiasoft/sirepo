'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;
SIREPO.DEFAULT_COLOR_MAP = 'viridis';

SIREPO.app.factory('vtkPlotting', function(appState, plotting, panelState, utilities, plotUtilities, $window) {

    var self = {};

    function identityTransform(lpoint) {
        return lpoint;
    }

    // Find where the "scene" (bounds of the rendered objects) intersects the screen (viewport)
    // Returns the properties of the first set of corners that fit - order them by desired location.
    // Could be none fit, in which case no properties are defined
    function edgeIntersections(vpEdges, cornersArr, bounds, dim, reverse) {
        var props = {};
        //srdbg('checking for edges that include corners', cornersArr);
        for(var corners in cornersArr) {
            var edges = plotUtilities.edgesWithCorners(vpEdges, cornersArr[corners])[0];
            //srdbg('edges that include corners', cornersArr[corners], edges);
            var sceneEnds = plotUtilities.sortInDimension(edges, dim);
            //srdbg('scene ends', sceneEnds);
            var screenEnds = plotUtilities.boundsIntersections(bounds, sceneEnds[0], sceneEnds[1]);
            //srdbg('screen ends', screenEnds);
            var sceneLen = plotUtilities.dist(sceneEnds[0], sceneEnds[1]);
            var clippedEnds = plotUtilities.sortInDimension(
                plotUtilities.edgesInsideBounds(screenEnds, bounds),
                dim, reverse);
            if(clippedEnds && clippedEnds.length == 2) {
             var clippedLen = plotUtilities.dist(clippedEnds[0], clippedEnds[1]);
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

        return {

            xform: transform || identityTransform,

            buildPlane: function(labOrigin, labP1, labP2) {
                var src = vtk.Filters.Sources.vtkPlaneSource.newInstance({ xResolution: 8, yResolution: 8 });
                this.setPlane(src, labOrigin, labP1, labP2);
                return src;
            },
            setPlane: function(planeSource, labOrigin, labP1, labP2) {
                var vo = this.xform(labOrigin);
                var vp1 = this.xform(labP1);
                var vp2 = this.xform(labP2);
                planeSource.setOrigin(vo[0], vo[1], vo[2]);
                planeSource.setPoint1(vp1[0], vp1[1], vp1[2]);
                planeSource.setPoint2(vp2[0], vp2[1], vp2[2]);
            },
            buildBox: function(labSize, labCenter) {
                var vsize = this.xform(labSize);
                var vcenter = this.xform(labCenter);
                return vtk.Filters.Sources.vtkCubeSource.newInstance({
                    xLength: vsize[0],
                    yLength: vsize[1],
                    zLength: vsize[2],
                    center: vcenter
                });
            },
            buildLine: function(labP1, labP2, colorArray) {
                var vp1 = this.xform(labP1);
                var vp2 = this.xform(labP2);
                var ls = vtk.Filters.Sources.vtkLineSource.newInstance({
                    point1: [vp1[0], vp1[1], vp1[2]],
                    point2: [vp2[0], vp2[1], vp2[2]],
                    resolution: 2
                });

                var lm = vtk.Rendering.Core.vtkMapper.newInstance();
                lm.setInputConnection(ls.getOutputPort());

                var la = vtk.Rendering.Core.vtkActor.newInstance();
                la.getProperty().setColor(colorArray[0], colorArray[1], colorArray[2]);
                la.setMapper(lm);
                return la;
            },
            buildSphere: function(lcenter, radius, colorArray) {
                var vcenter = this.xform(lcenter);
                var ps = vtk.Filters.Sources.vtkSphereSource.newInstance({
                    center: vcenter,
                    radius: radius,
                    thetaResolution: 16,
                    phiResolution: 16
                });

                var pm = vtk.Rendering.Core.vtkMapper.newInstance();
                pm.setInputConnection(ps.getOutputPort());

                var pa = vtk.Rendering.Core.vtkActor.newInstance();
                pa.getProperty().setColor(colorArray[0], colorArray[1], colorArray[2]);
                pa.getProperty().setLighting(false);
                pa.setMapper(pm);
                return pa;
            },
        };
    };

    self.orientations = {
        horizontal: 'h',
        vertical: 'v'
    };

    // "Superclass" for representation of vtk source objects in viewport coordinates
    self.vpObject = function(vtkSource, renderer) {

        var vpObj = {};

        var worldCoord = vtk.Rendering.Core.vtkCoordinate.newInstance({
            renderer: renderer
        });
        worldCoord.setCoordinateSystemToWorld();

        vpObj.source = vtkSource;
        vpObj.wCoord = worldCoord;

        // Override in subclass.  getEdges() should return a mapping
        // of names to pairs of points
        vpObj.getEdges = function() {
            return {};
        };
        vpObj.getEdge = function(name) {
            return vpObj.getEdges()[name];
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
    //
    self.vpBox = function(vtkCubeSource, renderer) {

        var box = self.vpObject(vtkCubeSource, renderer);

        // It's easiest to keep world coordinates in arrays rather than objects, since
        // we're mapping them a good deal and we will not refer to them directly
        function wCenter() {
            return box.source.getCenter();
        }

        // Convenience for looping
        function wLength() {
            return [
                box.source.getXLength(),
                box.source.getYLength(),
                box.source.getZLength()
            ];
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
            srdbg('corners', corners);
            return corners;

/*
            var cc = [
                [ctr[0] - 0.5 * box.source.getXLength(), ctr[1] - 0.5 * box.source.getYLength(), ctr[2] + 0.5 * box.source.getZLength()],  //leftBottomOut 0 -> 4
                [ctr[0] - 0.5 * box.source.getXLength(), ctr[1] + 0.5 * box.source.getYLength(), ctr[2] + 0.5 * box.source.getZLength()],  //leftTopOut 1 -> 6
                [ctr[0] + 0.5 * box.source.getXLength(), ctr[1] + 0.5 * box.source.getYLength(), ctr[2] + 0.5 * box.source.getZLength()],  //rightTopOut 2 -> 7
                [ctr[0] + 0.5 * box.source.getXLength(), ctr[1] - 0.5 * box.source.getYLength(), ctr[2] + 0.5 * box.source.getZLength()],  //rightBottomOut 3 -> 5
                [ctr[0] - 0.5 * box.source.getXLength(), ctr[1] - 0.5 * box.source.getYLength(), ctr[2] - 0.5 * box.source.getZLength()],  //leftBottomIn 4 -> 0
                [ctr[0] - 0.5 * box.source.getXLength(), ctr[1] + 0.5 * box.source.getYLength(), ctr[2] - 0.5 * box.source.getZLength()],  //leftTopIn 5 -> 2
                [ctr[0] + 0.5 * box.source.getXLength(), ctr[1] + 0.5 * box.source.getYLength(), ctr[2] - 0.5 * box.source.getZLength()],  //rightTopIn 6 -> 3
                [ctr[0] + 0.5 * box.source.getXLength(), ctr[1] - 0.5 * box.source.getYLength(), ctr[2] - 0.5 * box.source.getZLength()]   //rightBottomIn 7 -> 1
            ];
            return cc;
            */

        }
        function vpCorners() {
            return wCorners().map(function (p) {
                return self.localCoordFromWorld(box.wCoord, p);
            });
        }
        function wCenterLines() {
            var c = wCenter();
            var cls = [];
            var sides = [-0.5, 0.5];
            var src = box.source;
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
            /*
            return [
                [c[0] - 0.5 * box.source.getXLength(), c[1], c[2]],
                [c[0] + 0.5 * box.source.getXLength(), c[1], c[2]],
                [c[0], c[1] - 0.5 * box.source.getYLength(), c[2]],
                [c[0], c[1] + 0.5 * box.source.getYLength(), c[2]],
                [c[0], c[1], c[2] - 0.5 * box.source.getZLength()],
                [c[0], c[1], c[2] + 0.5 * box.source.getZLength()]
            ];
            */
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


    self.addActors = function(renderer, actorArr) {
        for(var aIndex = 0; aIndex < actorArr.length; ++aIndex) {
            renderer.addActor(actorArr[aIndex]);
        }
    };
    self.removeActors = function(renderer, actorArr) {
        for(var aIndex = 0; aIndex < actorArr.length; ++aIndex) {
            renderer.removeActor(actorArr[aIndex]);
        }
    };
    self.showActors = function(renderWindow, actorArray, doShow, visibleOpacity, hiddenOpacity) {
        for(var aIndex = 0; aIndex < actorArray.length; ++aIndex) {
            actorArray[aIndex].getProperty().setOpacity(doShow ? visibleOpacity || 1.0 : hiddenOpacity || 0.0);
        }
        renderWindow.render();
    };

    self.localCoordFromWorld = function (coord, point) {
        // this is required to do conversions for different displays/devices
        //srdbg('localCoordFromWorld point', point);
        var pixels = window.devicePixelRatio;
        coord.setCoordinateSystemToWorld();
        coord.setValue(point);
        var lCoord = coord.getComputedLocalDisplayValue();
        return [lCoord[0] / pixels, lCoord[1] / pixels];
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
