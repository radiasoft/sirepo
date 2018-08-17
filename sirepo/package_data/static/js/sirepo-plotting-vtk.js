'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;
SIREPO.DEFAULT_COLOR_MAP = 'viridis';

SIREPO.app.factory('vtkPlotting', function(appState, plotting, vtkService, panelState, utilities, plotUtilities, $window) {

    var self = {};
    var isPlottingReady = false;

    vtkService.vtk().then(function() {
        isPlottingReady = true;
    });

    function identityTransform(lpoint) {
        return lpoint;
    }

    function testTansformInverse(xform, invXform, lpoint) {
        var lpoint2 = invXform(xform(lpoint));
        if(lpoint2[0] != lpoint[0] || lpoint2[1] != lpoint[1] || lpoint2[2] != lpoint[2]) {
            throw 'transform(inverse) != identity:' + lpoint + '->' + lpoint2;
        }
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

            // These functions take an optional transformation to go from "lab"
            // coordinates to vtk screen coordinates
            setPlane: function(planeSource, lo, lp1, lp2) {
                var vo = this.xform(lo);
                var vp1 = this.xform(lp1);
                var vp2 = this.xform(lp2);
                planeSource.setOrigin(vo[0], vo[1], vo[2]);
                planeSource.setPoint1(vp1[0], vp1[1], vp1[2]);
                planeSource.setPoint2(vp2[0], vp2[1], vp2[2]);
            },
            buildBox: function(lsize, lcenter) {
                var vsize = this.xform(lsize);
                var vcenter = this.xform(lcenter);
                return vtk.Filters.Sources.vtkCubeSource.newInstance({
                    xLength: vsize[0],
                    yLength: vsize[1],
                    zLength: vsize[2],
                    center: vcenter
                });
            },
            buildLine: function(lp1, lp2, colorArray) {
                var vp1 = this.xform(lp1);
                var vp2 = this.xform(lp2);
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
            buildSphere: function(lcenter, radius, colorArray, transform) {
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

    self.pointToPObj = function(p) {
        return {
            x: p[0] || 0,
            y: p[1] || 0,
            z: p[2] || 0
        };
    };
    self.pObjToPoint = function(pObj) {
        return [
            pObj.x || 0,
            pObj.y || 0,
            pObj.z || 0
        ];
    };
    self.pointArrToObj = function(pArr) {
        return self.pObjArrToObj(pArr.map(function (p) {
            return self.pointToPObj(p);
        }));
    };
    self.pObjArrToObj = function(pObjArr) {
        var ppObj = {};
        for(var pIndex = 0; pIndex < pObjArr.length; ++pIndex) {
            ppObj['p' + (pIndex + 1)] = pObjArr[pIndex];
        }
        return ppObj;
    };


    // "Superclass" for representation of vtk source objects in viewport coordinates
    self.vpObject = function(vtkSource, renderer) {
        var worldCoord = vtk.Rendering.Core.vtkCoordinate.newInstance({
            renderer: renderer
        });
        worldCoord.setCoordinateSystemToWorld();
        return {
            source: vtkSource,
            wCoord: worldCoord
        };
    };

    // Takes a vtk cube source and renderer and returns a box in viewport coordinates with a bunch of useful
    // geometric properties and methods
    self.vpBox = function(vtkCubeSource, renderer) {

        var box = self.vpObject(vtkCubeSource, renderer);

        // It's easiest to keep world coordinates in arrays rather than objects, since
        // we're mapping them a good deal and we will not refer to them directly
        function wCenter() {
            return box.source.getCenter();
        }
        function wCorners() {
            return [
                [wCenter()[0] - 0.5 * box.source.getXLength(), wCenter()[1] - 0.5 * box.source.getYLength(), wCenter()[2] + 0.5 * box.source.getZLength()],
                [wCenter()[0] - 0.5 * box.source.getXLength(), wCenter()[1] + 0.5 * box.source.getYLength(), wCenter()[2] + 0.5 * box.source.getZLength()],
                [wCenter()[0] + 0.5 * box.source.getXLength(), wCenter()[1] + 0.5 * box.source.getYLength(), wCenter()[2] + 0.5 * box.source.getZLength()],
                [wCenter()[0] + 0.5 * box.source.getXLength(), wCenter()[1] - 0.5 * box.source.getYLength(), wCenter()[2] + 0.5 * box.source.getZLength()],
                [wCenter()[0] - 0.5 * box.source.getXLength(), wCenter()[1] - 0.5 * box.source.getYLength(), wCenter()[2] - 0.5 * box.source.getZLength()],
                [wCenter()[0] - 0.5 * box.source.getXLength(), wCenter()[1] + 0.5 * box.source.getYLength(), wCenter()[2] - 0.5 * box.source.getZLength()],
                [wCenter()[0] + 0.5 * box.source.getXLength(), wCenter()[1] + 0.5 * box.source.getYLength(), wCenter()[2] - 0.5 * box.source.getZLength()],
                [wCenter()[0] + 0.5 * box.source.getXLength(), wCenter()[1] - 0.5 * box.source.getYLength(), wCenter()[2] - 0.5 * box.source.getZLength()]
            ];
        }
        function vpCorners() {
            return wCorners().map(function (corner) {
                return self.localCoordFromWorld(box.wCoord, corner);
            });
        }

        // center lines
        var wLeftCenterCenter = [wCenter()[0] - 0.5 * box.source.getXLength(), wCenter()[1], wCenter()[2]];
        var wRightCenterCenter = [wCenter()[0] + 0.5 * box.source.getXLength(), wCenter()[1], wCenter()[2]];
        var wCenterBottomCenter = [wCenter()[0], wCenter()[1] - 0.5 * box.source.getYLength(), wCenter()[2]];
        var wCenterTopCenter = [wCenter()[0], wCenter()[1] + 0.5 * box.source.getYLength(), wCenter()[2]];
        var wCenterCenterIn = [wCenter()[0], wCenter()[1], wCenter()[2] - 0.5 * box.source.getZLength()];
        var wCenterCenterOut = [wCenter()[0], wCenter()[1], wCenter()[2] + 0.5 * box.source.getZLength()];

        // outline corners - axes will adhere to the proper sides

        var wLeftBottomOut = [wCenter()[0] - 0.5 * box.source.getXLength(), wCenter()[1] - 0.5 * box.source.getYLength(), wCenter()[2] + 0.5 * box.source.getZLength()];
        var wLeftTopOut = [wCenter()[0] - 0.5 * box.source.getXLength(), wCenter()[1] + 0.5 * box.source.getYLength(), wCenter()[2] + 0.5 * box.source.getZLength()];
        var wRightTopOut = [wCenter()[0] + 0.5 * box.source.getXLength(), wCenter()[1] + 0.5 * box.source.getYLength(), wCenter()[2] + 0.5 * box.source.getZLength()];
        var wRightBottomOut = [wCenter()[0] + 0.5 * box.source.getXLength(), wCenter()[1] - 0.5 * box.source.getYLength(), wCenter()[2] + 0.5 * box.source.getZLength()];
        var wLeftBottomIn = [wCenter()[0] - 0.5 * box.source.getXLength(), wCenter()[1] - 0.5 * box.source.getYLength(), wCenter()[2] - 0.5 * box.source.getZLength()];
        var wLeftTopIn = [wCenter()[0] - 0.5 * box.source.getXLength(), wCenter()[1] + 0.5 * box.source.getYLength(), wCenter()[2] - 0.5 * box.source.getZLength()];
        var wRightTopIn = [wCenter()[0] + 0.5 * box.source.getXLength(), wCenter()[1] + 0.5 * box.source.getYLength(), wCenter()[2] - 0.5 * box.source.getZLength()];
        var wRightBottomIn = [wCenter()[0] + 0.5 * box.source.getXLength(), wCenter()[1] - 0.5 * box.source.getYLength(), wCenter()[2] - 0.5 * box.source.getZLength()];

        // put in arrays for ease of transformation
        //var wCornersarr = [
        //    wLeftBottomOut, wLeftTopOut, wRightTopOut, wRightBottomOut,
        //    wLeftBottomIn, wLeftTopIn, wRightTopIn, wRightBottomIn
        //];
        var wCenters = [
            wLeftCenterCenter, wRightCenterCenter,
            wCenterBottomCenter, wCenterTopCenter,
            wCenterCenterIn, wCenterCenterOut
        ];


        // "vp" for "viewPort"
        var vpCornersarr = wCorners().map(function (corner) {
            return self.localCoordFromWorld(box.wCoord, corner);
        });
        var vpCenters = wCenters.map(function (corner) {
            return self.localCoordFromWorld(box.wCoord, corner);
        });

        // names are easier to think about
        var vpLeftBottomOut = vpCornersarr[0];
        var vpLeftBottomIn = vpCornersarr[4];
        var vpLeftTopOut = vpCornersarr[1];
        var vpLeftTopIn = vpCornersarr[5];

        var vpRightBottomOut = vpCornersarr[3];
        var vpRightBottomIn = vpCornersarr[7];
        var vpRightTopOut = vpCornersarr[2];
        var vpRightTopIn = vpCornersarr[6];

        var vpLeftCenterCenter = vpCenters[0];
        var vpRightCenterCenter = vpCenters[1];
        var vpCenterBottomCenter = vpCenters[2];
        var vpCenterTopCenter = vpCenters[3];
        var vpCenterCenterIn = vpCenters[4];
        var vpCenterCenterOut = vpCenters[5];

        // edges
        var vpBottomOut = [vpLeftBottomOut, vpRightBottomOut];
        var vpBottomIn = [vpLeftBottomIn, vpRightBottomIn];
        var vpTopOut = [vpLeftTopOut, vpRightTopOut];
        var vpTopIn = [vpLeftTopIn, vpRightTopIn];

        var vpLeftBottom = [vpLeftBottomOut, vpLeftBottomIn];
        var vpRightBottom = [vpRightBottomOut, vpRightBottomIn];
        var vpLeftTop = [vpLeftTopOut, vpLeftTopIn];
        var vpRightTop = [vpRightTopOut, vpRightTopIn];

        var vpLeftOut = [vpLeftBottomOut, vpLeftTopOut];
        var vpLeftIn = [vpLeftBottomIn, vpLeftTopIn];
        var vpRightOut = [vpRightBottomOut, vpRightTopOut];
        var vpRightIn = [vpRightBottomIn, vpRightTopIn];

        var vpLeftRight = [vpLeftCenterCenter, vpRightCenterCenter];
        var vpBottomTop = [vpCenterBottomCenter, vpCenterTopCenter];
        var vpInOut = [vpCenterCenterIn, vpCenterCenterOut];

        // arrays for axis handling
        /*
        var vpXEdges = [
            vpBottomOut, vpBottomIn, vpTopOut, vpTopIn
        ];
        var vpYEdges = [
            vpLeftOut, vpLeftIn, vpRightOut, vpRightIn
        ];
        var vpZEdges = [
            vpLeftBottom, vpRightBottom, vpLeftTop, vpRightTop
        ];
*/
        //var lowestCorners = plotUtilities.extrema(vpCorners, 1, true);
        //var leftmostCorners = plotUtilities.extrema(vpCorners, 0, false);
        //var highestCorners = plotUtilities.extrema(vpCorners, 1, false);
        //var rightmostCorners = plotUtilities.extrema(vpCorners, 0, true);

        // for the z (out-in) axis,
        var bottomofleftmost = plotUtilities.extrema(leftmostCorners, 1, true);
        var leftofbottommost = plotUtilities.extrema(lowestCorners, 0, false);
        var bottomofrightmost = plotUtilities.extrema(rightmostCorners, 1, true);
        var rightofbottommost = plotUtilities.extrema(lowestCorners, 0, true);
        var zLeft = [];  var zRight = [];  var index = 0;
        for(index in bottomofleftmost) {
            zLeft.push(bottomofleftmost[index]);
        }
        for(index in leftofbottommost) {
            zLeft.push(leftofbottommost[index]);
        }
        for(index in bottomofrightmost) {
            zRight.push(bottomofrightmost[index]);
        }
        for(index in rightofbottommost) {
            zRight.push(rightofbottommost[index]);
        }

        box.getCorners = function() {
            var cArr = vpCorners().map(function (p) {
                return self.pointToPObj(p);
            });
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
        };
        box.getExtrema = function() {
            var corners = vpCorners();
            return {
                lowestCorners: self.pointArrToObj(plotUtilities.extrema(corners, 1, true)),
                leftmostCorners: self.pointArrToObj(plotUtilities.extrema(corners, 0, false)),
                highestCorners: self.pointArrToObj(plotUtilities.extrema(corners, 1, false)),
                rightmostCorners: self.pointArrToObj(plotUtilities.extrema(corners, 0, true))
            };
        };
        box.getEdges = function() {
            var corners = box.getCorners();
            return {
                bottomOut: self.pObjArrToObj([corners.leftBottomOut, corners.rightBottomOut]),
                bottomIn: self.pObjArrToObj([corners.leftBottomIn, corners.rightBottomIn]),
                topOut: self.pObjArrToObj([corners.leftTopOut, corners.rightTopOut]),
                topIn: self.pObjArrToObj([corners.leftTopIn, corners.rightTopIn]),
                leftBottom: self.pObjArrToObj([corners.leftBottomOut, corners.leftBottomIn]),
                rightBottom: self.pObjArrToObj([corners.rightBottomOut, corners.rightBottomIn]),
                leftTop: self.pObjArrToObj([corners.leftTopOut, corners.leftTopIn]),
                rightTop: self.pObjArrToObj([corners.rightTopOut, corners.rightTopIn]),
                leftOut: self.pObjArrToObj([corners.leftBottomOut, corners.leftTopOut]),
                leftIn: self.pObjArrToObj([corners.leftBottomIn, corners.leftTopIn]),
                rightOut: self.pObjArrToObj([corners.rightBottomOut, corners.rightTopOut]),
                rightIn: self.pObjArrToObj([corners.rightBottomIn, corners.rightTopIn])
            };
        };
        return box;
    };

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

    // display values seem to be double, not sure why
    self.localCoordFromWorld = function (coord, point) {
        coord.setCoordinateSystemToWorld();
        coord.setValue(point);
        var lCoord = coord.getComputedLocalDisplayValue();
        return [lCoord[0] / 2.0, lCoord[1] / 2.0];
    };
    self.worldCoordFromLocal = function (coord, point, view) {
        var newPoint = [2.0 * point[0], 2.0 * point[1]];
        // must first convert from "localDisplay" to "display"  - this is the inverse of
        // what is done by vtk to get from display to localDisplay
        var newPointView = [newPoint[0], view.getFramebufferSize()[1] - newPoint[1] - 1];
        coord.setCoordinateSystemToDisplay();
        coord.setValue(newPointView);
        return coord.getComputedWorldValue();
    };
    /*
    return {

        vtkPlot: function(scope, element) {

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
        },

        coordMapper: function(transform) {

            return {

                xform: transform || identityTransform,

                // These functions take an optional transformation to go from "lab"
                // coordinates to vtk screen coordinates
                setPlane: function(planeSource, lo, lp1, lp2) {
                    var vo = this.xform(lo);
                    var vp1 = this.xform(lp1);
                    var vp2 = this.xform(lp2);
                    planeSource.setOrigin(vo[0], vo[1], vo[2]);
                    planeSource.setPoint1(vp1[0], vp1[1], vp1[2]);
                    planeSource.setPoint2(vp2[0], vp2[1], vp2[2]);
                },
                buildBox: function(lsize, lcenter) {
                    var vsize = this.xform(lsize);
                    var vcenter = this.xform(lcenter);
                    return vtk.Filters.Sources.vtkCubeSource.newInstance({
                        xLength: vsize[0],
                        yLength: vsize[1],
                        zLength: vsize[2],
                        center: vcenter
                    });
                },
                buildLine: function(lp1, lp2, colorArray) {
                    var vp1 = this.xform(lp1);
                    var vp2 = this.xform(lp2);
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
                buildSphere: function(lcenter, radius, colorArray, transform) {
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
        },

        pointArrToObj: function(pArr) {
            return {
                x: pArr[0] || 0,
                y: pArr[1] || 0,
                z: pArr[2] || 0
            };
        },

        // "Superclass" for representation of vtk source objects in viewport coordinates
        vpObject: function(vtkSource, renderer) {
            var worldCoord = vtk.Rendering.Core.vtkCoordinate.newInstance({
                renderer: renderer
            });
            worldCoord.setCoordinateSystemToWorld();
            return {
                source: vtkSource,
                wCoord: worldCoord
            };
        },

        // Takes a vtk cube source and renderer and returns a box in viewport coordinates with a bunch of useful
        // geometric properties and methods
        vpBox: function(vtkCubeSource, renderer) {

            var box = self.vpObject(vtkCubeSource, renderer);

            function wCenter() {
                return box.source.getCenter();
            }

                // center lines
                var osLeftCenterCenter = [wCenter()[0] - 0.5 * box.source.getXLength(), wCenter()[1], wCenter()[2]];
                var osRightCenterCenter = [wCenter()[0] + 0.5 * box.source.getXLength(), wCenter()[1], wCenter()[2]];
                var wCenterBottomCenter = [wCenter()[0], wCenter()[1] - 0.5 * box.source.getYLength(), wCenter()[2]];
                var wCenterTopCenter = [wCenter()[0], wCenter()[1] + 0.5 * box.source.getYLength(), wCenter()[2]];
                var wCenterCenterIn = [wCenter()[0], wCenter()[1], wCenter()[2] - 0.5 * box.source.getZLength()];
                var wCenterCenterOut = [wCenter()[0], wCenter()[1], wCenter()[2] + 0.5 * box.source.getZLength()];

                // outline corners - axes will adhere to the proper sides
                var osLeftBottomOut = [wCenter()[0] - 0.5 * box.source.getXLength(), wCenter()[1] - 0.5 * box.source.getYLength(), wCenter()[2] + 0.5 * box.source.getZLength()];
                var osLeftTopOut = [wCenter()[0] - 0.5 * box.source.getXLength(), wCenter()[1] + 0.5 * box.source.getYLength(), wCenter()[2] + 0.5 * box.source.getZLength()];
                var osRightTopOut = [wCenter()[0] + 0.5 * box.source.getXLength(), wCenter()[1] + 0.5 * box.source.getYLength(), wCenter()[2] + 0.5 * box.source.getZLength()];
                var osRightBottomOut = [wCenter()[0] + 0.5 * box.source.getXLength(), wCenter()[1] - 0.5 * box.source.getYLength(), wCenter()[2] + 0.5 * box.source.getZLength()];
                var osLeftBottomIn = [wCenter()[0] - 0.5 * box.source.getXLength(), wCenter()[1] - 0.5 * box.source.getYLength(), wCenter()[2] - 0.5 * box.source.getZLength()];
                var osLeftTopIn = [wCenter()[0] - 0.5 * box.source.getXLength(), wCenter()[1] + 0.5 * box.source.getYLength(), wCenter()[2] - 0.5 * box.source.getZLength()];
                var osRightTopIn = [wCenter()[0] + 0.5 * box.source.getXLength(), wCenter()[1] + 0.5 * box.source.getYLength(), wCenter()[2] - 0.5 * box.source.getZLength()];
                var osRightBottomIn = [wCenter()[0] + 0.5 * box.source.getXLength(), wCenter()[1] - 0.5 * box.source.getYLength(), wCenter()[2] - 0.5 * box.source.getZLength()];

                // put in arrays for ease of transformation
                var osCorners = [
                    osLeftBottomOut, osLeftTopOut, osRightTopOut, osRightBottomOut,
                    osLeftBottomIn, osLeftTopIn, osRightTopIn, osRightBottomIn
                ];
                var wCenters = [
                    osLeftCenterCenter, osRightCenterCenter,
                    wCenterBottomCenter, wCenterTopCenter,
                    wCenterCenterIn, wCenterCenterOut
                ];


                // "vp" for "viewPort"
                var vpCorners = osCorners.map(function (corner) {
                    return self.localCoordFromWorld(box.wCoord, corner);
                });
                var vpCenters = wCenters.map(function (corner) {
                    return self.localCoordFromWorld(box.wCoord, corner);
                });

                // names are easier to think about
                var vpLeftBottomOut = vpCorners[0];
                var vpLeftBottomIn = vpCorners[4];
                var vpLeftTopOut = vpCorners[1];
                var vpLeftTopIn = vpCorners[5];

                var vpRightBottomOut = vpCorners[3];
                var vpRightBottomIn = vpCorners[7];
                var vpRightTopOut = vpCorners[2];
                var vpRightTopIn = vpCorners[6];

                var vpLeftCenterCenter = vpCenters[0];
                var vpRightCenterCenter = vpCenters[1];
                var vpCenterBottomCenter = vpCenters[2];
                var vpCenterTopCenter = vpCenters[3];
                var vpCenterCenterIn = vpCenters[4];
                var vpCenterCenterOut = vpCenters[5];

                // edges
                var vpBottomOut = [vpLeftBottomOut, vpRightBottomOut];
                var vpBottomIn = [vpLeftBottomIn, vpRightBottomIn];
                var vpTopOut = [vpLeftTopOut, vpRightTopOut];
                var vpTopIn = [vpLeftTopIn, vpRightTopIn];

                var vpLeftBottom = [vpLeftBottomOut, vpLeftBottomIn];
                var vpRightBottom = [vpRightBottomOut, vpRightBottomIn];
                var vpLeftTop = [vpLeftTopOut, vpLeftTopIn];
                var vpRightTop = [vpRightTopOut, vpRightTopIn];

                var vpLeftOut = [vpLeftBottomOut, vpLeftTopOut];
                var vpLeftIn = [vpLeftBottomIn, vpLeftTopIn];
                var vpRightOut = [vpRightBottomOut, vpRightTopOut];
                var vpRightIn = [vpRightBottomIn, vpRightTopIn];

                var vpLeftRight = [vpLeftCenterCenter, vpRightCenterCenter];
                var vpBottomTop = [vpCenterBottomCenter, vpCenterTopCenter];
                var vpInOut = [vpCenterCenterIn, vpCenterCenterOut];

                // arrays for axis handling
                var vpXEdges = [
                    vpBottomOut, vpBottomIn, vpTopOut, vpTopIn
                ];
                var vpYEdges = [
                    vpLeftOut, vpLeftIn, vpRightOut, vpRightIn
                ];
                var vpZEdges = [
                    vpLeftBottom, vpRightBottom, vpLeftTop, vpRightTop
                ];

                var lowestCorners = plotUtilities.extrema(vpCorners, 1, true);
                var leftmostCorners = plotUtilities.extrema(vpCorners, 0, false);
                var highestCorners = plotUtilities.extrema(vpCorners, 1, false);
                var rightmostCorners = plotUtilities.extrema(vpCorners, 0, true);

                // for the z (out-in) axis,
                var bottomofleftmost = plotUtilities.extrema(leftmostCorners, 1, true);
                var leftofbottommost = plotUtilities.extrema(lowestCorners, 0, false);
                var bottomofrightmost = plotUtilities.extrema(rightmostCorners, 1, true);
                var rightofbottommost = plotUtilities.extrema(lowestCorners, 0, true);
                var zLeft = [];  var zRight = [];  var index = 0;
                for(index in bottomofleftmost) {
                    zLeft.push(bottomofleftmost[index]);
                }
                for(index in leftofbottommost) {
                    zLeft.push(leftofbottommost[index]);
                }
                for(index in bottomofrightmost) {
                    zRight.push(bottomofrightmost[index]);
                }
                for(index in rightofbottommost) {
                    zRight.push(rightofbottommost[index]);
                }

                box.getCorners = function() {
                    return {
                        leftBottomOut: self.pointArrToObj([wCenter()[0] - 0.5 * box.source.getXLength(), wCenter()[1] - 0.5 * box.source.getYLength(), wCenter()[2] + 0.5 * box.source.getZLength()]),
                        leftTopOut: self.pointArrToObj([wCenter()[0] - 0.5 * box.source.getXLength(), wCenter()[1] + 0.5 * box.source.getYLength(), wCenter()[2] + 0.5 * box.source.getZLength()]),
                        rightTopOut: self.pointArrToObj([wCenter()[0] + 0.5 * box.source.getXLength(), wCenter()[1] + 0.5 * box.source.getYLength(), wCenter()[2] + 0.5 * box.source.getZLength()]),
                        rightBottomOut: self.pointArrToObj([wCenter()[0] + 0.5 * box.source.getXLength(), wCenter()[1] - 0.5 * box.source.getYLength(), wCenter()[2] + 0.5 * box.source.getZLength()]),
                        leftBottomIn: self.pointArrToObj([wCenter()[0] - 0.5 * box.source.getXLength(), wCenter()[1] - 0.5 * box.source.getYLength(), wCenter()[2] - 0.5 * box.source.getZLength()]),
                        leftTopIn: self.pointArrToObj([wCenter()[0] - 0.5 * box.source.getXLength(), wCenter()[1] + 0.5 * box.source.getYLength(), wCenter()[2] - 0.5 * box.source.getZLength()]),
                        rightTopIn: self.pointArrToObj([wCenter()[0] + 0.5 * box.source.getXLength(), wCenter()[1] + 0.5 * box.source.getYLength(), wCenter()[2] - 0.5 * box.source.getZLength()]),
                        rightBottomIn: self.pointArrToObj([wCenter()[0] + 0.5 * box.source.getXLength(), wCenter()[1] - 0.5 * box.source.getYLength(), wCenter()[2] - 0.5 * box.source.getZLength()])
                    };
                };
                return box;
        },

        addActors: function(renderer, actorArr) {
            for(var aIndex = 0; aIndex < actorArr.length; ++aIndex) {
                renderer.addActor(actorArr[aIndex]);
            }
        },
        removeActors: function(renderer, actorArr) {
            for(var aIndex = 0; aIndex < actorArr.length; ++aIndex) {
                renderer.removeActor(actorArr[aIndex]);
            }
        },
        showActors: function(renderWindow, actorArray, doShow, visibleOpacity, hiddenOpacity) {
            for(var aIndex = 0; aIndex < actorArray.length; ++aIndex) {
                actorArray[aIndex].getProperty().setOpacity(doShow ? visibleOpacity || 1.0 : hiddenOpacity || 0.0);
            }
            renderWindow.render();
        },

        // display values seem to be double, not sure why
        localCoordFromWorld: function (coord, point) {
            coord.setCoordinateSystemToWorld();
            coord.setValue(point);
            var lCoord = coord.getComputedLocalDisplayValue();
            return [lCoord[0] / 2.0, lCoord[1] / 2.0];
        },
        worldCoordFromLocal: function (coord, point, view) {
            var newPoint = [2.0 * point[0], 2.0 * point[1]];
            // must first convert from "localDisplay" to "display"  - this is the inverse of
            // what is done by vtk to get from display to localDisplay
            var newPointView = [newPoint[0], view.getFramebufferSize()[1] - newPoint[1] - 1];
            coord.setCoordinateSystemToDisplay();
            coord.setValue(newPointView);
            return coord.getComputedWorldValue();
        },

    };
    */
    return self;
});
