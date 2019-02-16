'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;
SIREPO.DEFAULT_COLOR_MAP = 'viridis';

SIREPO.app.factory('vtkPlotting', function(appState, errorService, plotting, panelState, utilities, geometry, $location, $rootScope, $timeout, $window) {

    var self = {};

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

    self.loadSTL = function(fileName) {
        var url = 'static/' + fileName;
        srdbg('LOADING',  url);
        var r = vtk.IO.Geometry.vtkSTLReader.newInstance();
        return r.setUrl(url)
            .then(function() {
                srdbg('PARSED STL');
                return r;
        }, function (err) {
            srdbg('BAD STL', err);
            //var errTxt =  fileName + ': Invalid or missing .stl file: ';
            //var errTxt2 = err.xhr ? err.xhr.status + ' (' + err.xhr.statusText + ')' : err;
            // format errors from the XMLHttpRequest
            //if(err.xhr) {
            //    errTxt = errTxt + err.xhr.status + ' (' + err.xhr.statusText + ')';
           // }
           // else {
           //     errTxt = errTxt + err;
            //}
            throw fileName + ': Invalid or missing .stl file: ' +
            (err.xhr ? err.xhr.status + ' (' + err.xhr.statusText + ')' : err);
        })
            .catch(function (e) {
                srdbg('CAUGHT', e);
                $rootScope.$apply(function () {
                    errorService.alertText(e);
                });
            });
    };

    self.parseSTL = function(file) {
        srdbg('PARSING', file);
        var ok = false;
        $timeout(function () {
            ok = ! ! self.loadSTL(file);
        });
        return ok;
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


    // "Superclass" for representation of vtk source objects in ViewPort coordinates
    // Note this means that vpObjects are implicitly two-dimensional
    // A vpObject is assumed to have corners and edges connecting them, but no other
    // intrinsic properties
    self.vpObject = function(vtkSource, renderer) {

        var svc = self;
        var vpObj = {};

        var worldCoord = vtk.Rendering.Core.vtkCoordinate.newInstance({
            renderer: renderer
        });
        worldCoord.setCoordinateSystemToWorld();

        vpObj.worldReady = false;

        vpObj.source = vtkSource;
        vpObj.wCoord = worldCoord;
        vpObj.worldCorners = [];
        vpObj.worldEdges = {};

        vpObj.viewportCorners = [];
        vpObj.viewportEdges = {};

        // Override in subclass
        // world geometry does not change so they can be set once

        vpObj.wEdgesForDimension = function(dim) {
            return vpObj.worldEdges[dim];
        };

        vpObj.boundingRect = function() {
            var vpe = vpObj.vpExtrema();
            var extrema = vpe.x.concat(vpe.y);
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

        // an external edge has all other corners on the same side of the line it defines
        vpObj.externalVpEdgesForDimension = function (dim) {
            var ext = [];
            vpObj.vpEdgesForDimension(dim).forEach(function (edge) {
                var numCorners = 0;
                var compCount = 0;
                for(var i in geometry.basis) {
                    var otherDim = geometry.basis[i];
                    if(otherDim === dim) {
                        continue;
                    }
                    var otherEdges = vpObj.vpEdgesForDimension(otherDim);
                    for(var j = 0; j < otherEdges.length; ++j) {
                        var otherEdgeCorners = otherEdges[j].points();
                        for(var k = 0; k <= 1; ++k) {
                            var n = edge.line().comparePoint(otherEdgeCorners[k]);
                            compCount += n;
                            if(n !== 0) {
                                numCorners++;
                            }
                        }
                    }
                }
                ext.push(Math.abs(compCount) === numCorners ? edge : null);
            });
            return ext;
        };

        vpObj.initializeWorld = function() {
            if(! vpObj.worldReady) {
                vpObj.worldReady = true;
            }
        };

        vpObj.localCoordFromWorld = function (point) {
            return svc.localCoordFromWorld(vpObj.wCoord, point);
        };

        vpObj.localCoordArrayFromWorld = function (arr) {
            return arr.map(function (p) {
                return vpObj.localCoordFromWorld(p);
            });
        };

        vpObj.vpCorners = function() {
            return vpObj.localCoordArrayFromWorld(vpObj.worldCorners);
        };

        vpObj.vpEdges = function() {
            var ee = {};
            var es = vpObj.worldEdges;
            for(var e in es) {
                var edges = es[e];
                var lEdges = [];
                for(var i = 0; i < edges.length; ++i) {
                    var ls = edges[i];
                    var wpts = ls.points();
                    var lpts = [];
                    for(var j = 0; j < wpts.length; ++j) {
                        lpts.push(vpObj.localCoordFromWorld(wpts[j]));
                    }
                    var lEdge = geometry.lineSegment(lpts[0], lpts[1]);
                    lEdges.push(lEdge);
                }
                ee[e] = lEdges;
            }
            return ee;
        };

        vpObj.vpEdgesForDimension = function (dim) {
            return vpObj.vpEdges()[dim];
        };

        // points on the screen that have the largest and smallest values in each dimension
        vpObj.vpExtrema = function() {
            var ex = {};
            // just x and y
            var dims = geometry.basis.slice(0, 2);
            var rev = [false, true];
            dims.forEach(function (dim) {
                ex[dim] = [];
                for( var j in rev ) {
                    ex[dim].push(geometry.extrema(vpObj.vpCorners(), dim, rev[j]));
                }
            });
            return ex;
        };

        return vpObj;
    };


    // Takes a vtk cube source and renderer and returns a box in viewport coordinates with a bunch of useful
    // geometric properties and methods
    self.vpBox = function(vtkCubeSource, renderer) {

        var box = self.vpObject(vtkCubeSource, renderer);

        var initWorldFn = box.initializeWorld;
        box.initializeWorld = function () {
            if(! box.worldReady) {
                box.worldCorners = wCorners();
                box.worldEdges = wEdges();
            }
            initWorldFn();
        };

        function wCenter() {
            return geometry.pointFromArr(box.source.getCenter());
        }

        // Convenience for indexed looping
        function wLength() {
            return [
                box.source.getXLength(),
                box.source.getYLength(),
                box.source.getZLength()
            ];
        }

        // Convenience for basis looping
        function wl() {
            var l = wLength();
            return {
                x: l[0],
                y: l[1],
                z: l[2]
            };
        }

        function wCorners() {
            var ctr = wCenter();
            var corners = [];

            var sides = [-0.5, 0.5];
            var len = wLength();
            for(var i in sides) {
                for (var j in sides) {
                    for (var k in sides) {
                        var s = [sides[k], sides[j], sides[i]];
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

        // box corners are defined thus:
        //
        //   2------X2------3    6------X3------7
        //   |              |    |              |
        //   |              |    |              |
        //   Y0   Front    Y1    Y2   Back     Y3
        //   |              |    |              |
        //   |              |    |              |
        //   0------X0------1    4------X1------5
        //
        //TODO(mvk): Order is important only for axis direction and should be supplied externally
        var edgeCornerPairs = {
            x: [[0, 1], [4, 5], [2, 3], [6, 7]],
            y: [[0, 2], [1, 3], [4, 6], [5, 7]],
            z: [[4, 0], [5, 1], [6, 2], [7, 3]]
        };

        function wEdges() {
            var c = box.worldCorners;
            var e = {};
            for (var dim in edgeCornerPairs) {
                var lines = [];
                for (var j in  edgeCornerPairs[dim]) {
                    var p = edgeCornerPairs[dim][j];
                    var l = geometry.lineSegment(c[p[0]], c[p[1]]);
                    lines.push(l);
                }
                e[dim] = lines;
            }
            return e;
        }

        box.vpCenterLineForDimension = function (dim) {
            return vpCenterLines()[dim];
        };

        function vpCenterLines() {
            var ctr = wCenter().coords();
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

        return box;
    };

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
        var pixels = window.devicePixelRatio;
        vtkCoord.setCoordinateSystemToWorld();
        vtkCoord.setValue(point.coords());
        var lCoord = vtkCoord.getComputedLocalDisplayValue();
        return geometry.point(lCoord[0] / pixels, lCoord[1] / pixels);
    };

    self.worldCoordFromLocal = function (coord, point, view) {
        var pixels = window.devicePixelRatio;
        var newPoint = [pixels * point.coords()[0], pixels * point.coords()[1]];
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
SIREPO.app.directive('vtkDisplay', function(appState, panelState, requestSender, frameCache, geometry, plotting, vtkManager, vtkPlotting, layoutService, plotToPNG, utilities) {

    return {
        restrict: 'A',
        //transclude: {
        //    visabilityControlSlot: '?visabilityControl',
        //},
        scope: {
            modelName: '@',
            reportId: '<',
        },
        templateUrl: '/static/html/vtk-display.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope, $element) {
            //TODO (mvk): fill in with common vtk stuff
            var bundles;  // probably scope
            var cam;
            var camPos;
            var camViewUp;
            var canvas3d;
            var d3self;
            var didPan = false;
            var fsRenderer;
            var orientationMarker;
            var lastCamPos;
            var lastCamViewUp;
            var lastCamFP;
            var mainView;
            var malSized = false;
            var renderer;
            var renderWindow;
            var snapshotCanvas;
            var snapshotCtx;
            var zoomUnits = 0;

            $scope.addOrientationMarker = false;

            $scope.init = function() {

                d3self = d3.selectAll($element);

                var rw = angular.element($($element).find('.sr-plot-particle-3d .vtk-canvas-holder'))[0];
                fsRenderer = vtk.Rendering.Misc.vtkFullScreenRenderWindow.newInstance({
                    background: [1, 1, 1, 1],
                    container: rw,
                    listenWindowResize: false,
                });
                renderer = fsRenderer.getRenderer();
                renderer.getLights()[0].setLightTypeToSceneLight();
                renderWindow = fsRenderer.getRenderWindow();
                mainView = renderWindow.getViews()[0];

                cam = renderer.get().activeCamera;

                rw.addEventListener('dblclick', resetAndDigest);

                var worldCoord = vtk.Rendering.Core.vtkCoordinate.newInstance({
                    renderer: renderer
                });
                worldCoord.setCoordinateSystemToWorld();

                var isDragging = false;
                var isPointerUp = true;
                rw.onpointerdown = function(evt) {
                    isDragging = false;
                    isPointerUp = false;
                };
                rw.onpointermove = function(evt) {
                    if(isPointerUp) {
                        return;
                    }
                    isDragging = true;
                    didPan = didPan || evt.shiftKey;
                    $scope.side = null;
                    utilities.debounce(refresh, 100)();
                };
                rw.onpointerup = function(evt) {
                    if(! isDragging) {
                        // use picker to display info on objects
                    }
                    isDragging = false;
                    isPointerUp = true;
                    refresh(true);
                };
                rw.onwheel = function (evt) {
                    var camPos = cam.getPosition();

                    // If zoom needs to be halted or limited, it can be done here.  For now track the "zoom units"
                    // for managing refreshing and resetting
                    if(! malSized) {
                        zoomUnits += evt.deltaY;
                    }
                    utilities.debounce(
                        function() {
                            refresh(true);
                        },
                        100)();
                };

                // a little widget that mirrors the orientation (not the scale) of the scence
                if($scope.addOrientationMarker) {
                    var axesActor = vtk.Rendering.Core.vtkAxesActor.newInstance();
                    orientationMarker = vtk.Interaction.Widgets.vtkOrientationMarkerWidget.newInstance({
                        actor: axesActor,
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

                canvas3d = $($element).find('canvas')[0];

                // this canvas is used to store snapshots of the 3d canvas
                snapshotCanvas = document.createElement('canvas');
                snapshotCtx = snapshotCanvas.getContext('2d');
                plotToPNG.addCanvas(snapshotCanvas, $scope.reportId);
            };

            // override
            function sceneRect() {
                return geometry.rect(geometry.point(-0.5, -0.5), geometry.point(0.5, 0.5));
            }

            function refresh(doCacheCanvas) {

                var viewAspectRatio = 1.0;  // override
                var width = parseInt($($element).css('width')) - $scope.margin.left - $scope.margin.right;
                $scope.width = plotting.constrainFullscreenSize($scope, width, viewAspectRatio);
                $scope.height = viewAspectRatio * $scope.width;

                var vtkCanvasHolderSize = {
                    width: $('.vtk-canvas-holder').width(),
                    height: $('.vtk-canvas-holder').height()
                };

                var screenRect = geometry.rect(
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

                select('.vtk-canvas-holder svg')
                    .attr('width', vtkCanvasSize.width)
                    .attr('height', vtkCanvasSize.height);

                // Note that vtk does not re-add actors to the renderer if they already exist
                //vtkPlotting.addActors(renderer, actors);

                // reset camera will negate zoom and pan but *not* rotation
                if (zoomUnits == 0 && ! didPan) {
                    renderer.resetCamera();
                }
                renderWindow.render();

                var sceneRect =  sceneRect();
                var sceneArea;

                // initial area of scene
                if(! sceneArea) {
                    sceneArea = sceneRect.area();
                }

                var offscreen = ! (
                    sceneRect.intersectsRect(screenRect) ||
                    screenRect.containsRect(sceneRect) ||
                    sceneRect.containsRect(screenRect)
                );
                var a = sceneRect.area() / sceneArea;
                malSized = a < 0.1 || a > 7.5;
                $scope.canInteract = ! offscreen && ! malSized;
                if($scope.canInteract) {
                    lastCamPos = cam.getPosition();
                    lastCamViewUp = cam.getViewUp();
                    lastCamFP = cam.getFocalPoint();
                }
                else {
                    setCam(lastCamPos, lastCamFP ,lastCamViewUp);
                }

                if (SIREPO.APP_SCHEMA.feature_config.display_test_boxes) {
                    $scope.testBoxes = [
                        /*
                        {
                            x: x,
                            y: y,
                            color: "color"
                        },
                        */
                    ];

                }

                if(doCacheCanvas) {
                    cacheCanvas();
                }
            }

            function resetAndDigest() {
                $scope.$apply(reset);
            }

            function reset() {
                camPos = [0, 0, 1];
                camViewUp = [0, 1, 0];
                resetCam();
            }

            function resetCam() {
                setCam(camPos, [0,0,0], camViewUp);
                cam.zoom(1.3);
                renderer.resetCamera();
                zoomUnits = 0;
                didPan = false;
                if($scope.addOrientationMarker) {
                    orientationMarker.updateMarkerOrientation();
                }
                refresh(true);
            }

            function cacheCanvas() {
                if(! snapshotCtx) {
                    return;
                }
                var w = parseInt(canvas3d.getAttribute('width'));
                var h = parseInt(canvas3d.getAttribute('height'));
                snapshotCanvas.width = w;
                snapshotCanvas.height = h;
                // this call makes sure the buffer is fresh (it appears)
                fsRenderer.getOpenGLRenderWindow().traverseAllPasses();
                snapshotCtx.drawImage(canvas3d, 0, 0, w, h);
            }

            function select(selector) {
                var e = d3.select($scope.element);
                return selector ? e.select(selector) : e;
            }

            function setCam(pos, fp, vu) {
                cam.setPosition(pos[0], pos[1], pos[2]);
                cam.setFocalPoint(fp[0], fp[1], fp[2]);
                cam.setViewUp(vu[0], vu[1], vu[2]);
            }

       },

        link: function link(scope, element) {
            vtkPlotting.vtkPlot(scope, element);
        },
    };
});

SIREPO.app.directive('stlFileChooser', function(vtkPlotting) {
    return {
        restrict: 'A',
        scope: {
            description: '=',
            model: '=',
            require: '<',
            title: '@',
        },
        template: [
            '<div data-file-chooser="" data-validator="validate" data-title="title" data-file-formats=".stl" data-description="description" data-require="require">',
            '</div>',
        ].join(''),
        controller: function($scope, $element) {
            //srdbg('STL FILE CHOOSER CTL', $element);
            //srdbg('STL FILE CHOOSER CTL', $scope.description);
            $scope.validate = function (filename) {
                srdbg('VALIDAITNG STL', filename);
                return vtkPlotting.parseSTL(filename);
            };
            $scope.validationError = '';
        },
        link: function(scope, element, attrs) {

        },
    };
});

SIREPO.app.directive('stlImportDialog', function(appState, vtkPlotting) {
    return {
        restrict: 'A',
        scope: {
            title: '@',
            description: '@',
        },
        template: [
            '<div class="modal fade" id="simulation-import" tabindex="-1" role="dialog">',
              '<div class="modal-dialog modal-lg">',
                '<div class="modal-content">',
                  '<div class="modal-header bg-info">',
                    '<button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>',
                    '<div data-help-button="{{ title }}"></div>',
                    '<span class="lead modal-title text-info">{{ title }}</span>',
                  '</div>',
                  '<div class="modal-body">',
                    '<div class="container-fluid">',
                        '<form>',
                        '<div data-stl-file-chooser="" data-input-file="inputFile" data-title="title" data-description="description" data-require="true"></div>',
                          '<div class="col-sm-6 pull-right">',
                            '<button data-ng-click="importStlFile(inputFile)" class="btn btn-primary" data-ng-class="{\'disabled\': isMissingImportFile() }">Import File</button>',
                            ' <button data-dismiss="modal" class="btn btn-default">Cancel</button>',
                          '</div>',
                        '</form>',
                    '</div>',
                  '</div>',
                '</div>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.inputFile = null;
            srdbg('desc', $scope.description);
            $scope.isMissingImportFile = function() {
                return ! $scope.inputFile;
            };

            $scope.fileUploadError = '';
            $scope.isUploading = false;
            $scope.title = $scope.title || 'Import STL File';
            $scope.description = $scope.description || 'Select File';
            $scope.newSim = function(inputFile) {
                if (! inputFile) {
                    return;
                }
                $scope.isUploading = true;
                appState.newSimulation(
                    appState.models.simulation,
                    function (data) {
                        
                    }
                );

                fileUpload.uploadFileToUrl(
                    inputFile,
                    {
                        folder: fileManager.getActiveFolderPath(),
                    },
                    requestSender.formatUrl(
                        'importFile',
                        {
                            '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                        }),
                    function(data) {
                        $scope.isUploading = false;
                        if (data.error) {
                            $scope.fileUploadError = data.error;
                        }
                        else {
                            $('#simulation-import').modal('hide');
                            $scope.inputFile = null;
                            requestSender.localRedirectHome(data.models.simulation.simulationId);
                        }
                    });
            };
        },
        link: function(scope, element) {
            $(element).on('show.bs.modal', function() {
                $('#file-import').val(null);
                scope.fileUploadError = '';
                scope.isUploading = false;
            });
            scope.$on('$destroy', function() {
                $(element).off();
            });
        },
    };});


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
