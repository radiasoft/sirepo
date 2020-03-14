'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;
SIREPO.DEFAULT_COLOR_MAP = 'viridis';

SIREPO.app.factory('vtkPlotting', function(appState, errorService, geometry, plotting, panelState, requestSender, utilities, $location, $rootScope, $timeout, $window) {

    var self = {};
    var stlReaders = {};

    self.addSTLReader = function(file, reader) {
        stlReaders[file] = reader;
    };

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

    self.coordMapper = function(transform) {

        // "Bundles" a source, mapper, and actor together
        function actorBundle(source) {
            var m = vtk.Rendering.Core.vtkMapper.newInstance();
            if (source) {
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
                setMapper: function (mapper) {
                    this.mapper = mapper;
                    this.actor.setMapper(mapper);
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

            // arbitrary vtk source, transformed
            buildFromSource: function(src) {
                // add transform
                return actorBundle(src);
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
                var b = actorBundle(src);
                if (labOrigin && labP1 && labP2) {
                    this.setPlane(b, labOrigin, labP1, labP2);
                }
                return b;
            },

            buildSphere: function(lcenter, radius, colorArray) {
                var ps = vtk.Filters.Sources.vtkSphereSource.newInstance({
                    center: lcenter ? this.xform.doTransform(lcenter) : [0, 0, 0],
                    radius: radius || 1,
                    thetaResolution: 16,
                    phiResolution: 16
                });

                var ab = actorBundle(ps);
                ab.actor.getProperty().setColor(...(colorArray || [1, 1, 1]));
                ab.actor.getProperty().setLighting(false);
                return ab;
            },

            buildSTL: function(file, callback) {
                var cm = this;
                var r = self.getSTLReader(file);

                if (r) {
                    setSTL(r);
                    return;
                }
                self.loadSTLFile(file).then(function (r) {
                    r.loadData()
                        .then(function (res) {
                            self.addSTLReader(file, r);
                            setSTL(r);
                        }, function (reason) {
                            throw new Error(file + ': Error loading data from .stl file: ' + reason);
                        }
                    ).catch(function (e) {
                        errorService.alertText(e);
                    });
                });

                function setSTL(r) {
                    var b = actorBundle(r);
                    var a = b.actor;
                    var userMatrix = [];
                    cm.xform.matrix.forEach(function (row) {
                        userMatrix = userMatrix.concat(row);
                        userMatrix.push(0);
                    });
                    userMatrix = userMatrix.concat([0, 0, 0, 1]);
                    a.setUserMatrix(userMatrix);
                    callback(b);
                }

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

    self.clearSTLReaders = function() {
        stlReaders = {};
    };

    self.getSTLReader = function(file) {
        return stlReaders[file];
    };

    self.isSTLFileValid = function(file) {
        return self.loadSTLFile(file).then(function (r) {
            return ! ! r;
        });
    };

    self.isSTLUrlValid = function(url) {
        return self.loadSTLURL(url).then(function (r) {
            return ! ! r;
        });
    };

    self.loadSTLFile = function(file) {
        var fileName = file.name || file;

        var url = requestSender.formatUrl('downloadFile', {
            '<simulation_id>': appState.models.simulation.simulationId,
            '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
            '<filename>': self.stlFileType + '.' + fileName,
        });
        return self.loadSTLURL(url).then(function (r) {
            return r;
        });
    };

    self.loadSTLURL = function(url) {
        var r = vtk.IO.Geometry.vtkSTLReader.newInstance();
        return r.setUrl(url)
            .then(function() {
                return r;
        }, function (err) {
            throw new Error(url + ': Invalid or missing .stl: ' +
            (err.xhr ? err.xhr.status + ' (' + err.xhr.statusText + ')' : err));
        })
            .catch(function (e) {
                $rootScope.$apply(function () {
                    errorService.alertText(e);
                });
            });
    };

    self.removeSTLReader = function(file) {
        if (stlReaders[file]) {
            delete stlReaders[file];
        }
    };

    self.cylinderSection = function(center, axis, radius, height, planes) {
        const startAxis = [0, 0, 1];
        const startOrigin = [0, 0, 0];
        const cylBounds = [-radius, radius, -radius, radius, -height/2.0, height/2.0];
        const cyl = vtk.Common.DataModel.vtkCylinder.newInstance({
            radius: radius,
            center: startOrigin,
            axis: startAxis
        });

        const pl = planes.map(function (p) {
            return vtk.Common.DataModel.vtkPlane.newInstance({
                normal: p.norm || startAxis,
                origin: p.origin || startOrigin
            });
        });

        // perform the sectioning
        const section = vtk.Common.DataModel.vtkImplicitBoolean.newInstance({
            operation: 'Intersection',
            functions: [cyl, ...pl]
        });

        const sectionSample = vtk.Imaging.Hybrid.vtkSampleFunction.newInstance({
            implicitFunction: section,
            modelBounds: cylBounds,
            sampleDimensions: [32, 32, 32]
        });

        const sectionSource = vtk.Filters.General.vtkImageMarchingCubes.newInstance();
        sectionSource.setInputConnection(sectionSample.getOutputPort());
        // this transformation adapted from VTK cylinder source - we don't "untranslate" because we want to
        // rotate in place, not around the global origin
        vtk.Common.Core.vtkMatrixBuilder
            .buildFromRadian()
            .translate(...center)
            .rotateFromDirections(startAxis, axis)
            .apply(sectionSource.getOutputData().getPoints().getData());
       return sectionSource;
    };

    self.setColorSclars = function(data, color) {
        const pts = data.getPoints();
        const n = color.length * (pts.getData().length / pts.getNumberOfComponents());
        const pd = data.getPointData();
        const s = pd.getScalars();
        const rgb = s ? s.getData() : new window.Uint8Array(n);
        for (let i = 0; i < n; i += color.length) {
            for (let j = 0; j < color.length; ++j) {
                rgb[i + j] = color[j];
            }
        }
        pd.setScalars(
            vtk.Common.Core.vtkDataArray.newInstance({
                name: 'color',
                numberOfComponents: color.length,
                values: rgb,
            })
        );

        data.modified();
    };

    self.stlFileType = 'stl-file';

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
        vpObj.worldCorners = wCorners();  //[];
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
                    if (otherDim === dim) {
                        continue;
                    }
                    var otherEdges = vpObj.vpEdgesForDimension(otherDim);
                    for(var j = 0; j < otherEdges.length; ++j) {
                        var otherEdgeCorners = otherEdges[j].points();
                        for(var k = 0; k <= 1; ++k) {
                            var n = edge.line().comparePoint(otherEdgeCorners[k]);
                            compCount += n;
                            if (n !== 0) {
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
            if (! vpObj.worldReady) {
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

        function wCorners() {
            // [x0, x1, y0, y1, z0, z1]
            var b = vpObj.source.getOutputData().getBounds();
            return [
                geometry.pointFromArr([b[0], b[2], b[4]]),
                geometry.pointFromArr([b[0], b[2], b[5]]),
                geometry.pointFromArr([b[0], b[3], b[4]]),
                geometry.pointFromArr([b[0], b[3], b[5]]),
                geometry.pointFromArr([b[1], b[2], b[4]]),
                geometry.pointFromArr([b[1], b[2], b[5]]),
                geometry.pointFromArr([b[1], b[3], b[4]]),
                geometry.pointFromArr([b[1], b[3], b[5]])
            ];
        }

        return vpObj;
    };


    // Takes a vtk cube source and renderer and returns a box in viewport coordinates with a bunch of useful
    // geometric properties and methods
    self.vpBox = function(vtkCubeSource, renderer) {

        var box = self.vpObject(vtkCubeSource, renderer);

        var initWorldFn = box.initializeWorld;
        box.initializeWorld = function () {
            if (! box.worldReady) {
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

    self.vpSTL = function(stlReader, renderer) {
        var stl = self.vpObject(stlReader, renderer);
        return stl;
    };

    self.addActors = function(renderer, actorArr) {
        actorArr.forEach(function(actor) {
            self.addActor(renderer, actor);
        });
    };

    self.addActor = function(renderer, actor) {
        if (! actor) {
            return;
        }
        renderer.addActor(actor);
    };

    self.removeActors = function(renderer, actorArr) {
        if (! actorArr) {
            renderer.getActors().forEach(function(actor) {
                renderer.removeActor(actor);
            });
            return;
        }
        actorArr.forEach(function(actor) {
            self.removeActor(renderer, actor);
        });
        actorArr.length = 0;
    };

    self.removeActor = function(renderer, actor) {
        if (! actor ) {
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
        if (! waitToRender) {
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

    self.vtkUserMatrixFromMatrix = function(matrix) {
        var um = [];
        matrix.forEach(function (row) {
            um = um.concat(row);
            um.push(0);
        });
        um = um.concat([0, 0, 0, 1]);
        return um;
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

SIREPO.app.directive('stlFileChooser', function(validationService, vtkPlotting) {
    return {
        restrict: 'A',
        scope: {
            description: '=',
            url: '=',
            inputFile: '=',
            model: '=',
            require: '<',
            title: '@',
        },
        template: [
            '<div data-file-chooser=""  data-url="url" data-input-file="inputFile" data-validator="validate" data-title="title" data-file-formats=".stl" data-description="description" data-require="require">',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.validate = function (file) {
                $scope.url = URL.createObjectURL(file);
                return vtkPlotting.isSTLUrlValid($scope.url).then(function (ok) {
                    return ok;
                });
            };
            $scope.validationError = '';
        },
        link: function(scope, element, attrs) {

        },
    };
});

SIREPO.app.directive('stlImportDialog', function(appState, fileManager, fileUpload, vtkPlotting, requestSender) {
    return {
        restrict: 'A',
        scope: {
            description: '@',
            title: '@',
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
                        '<div data-stl-file-chooser="" data-input-file="inputFile" data-url="fileURL" data-title="title" data-description="description" data-require="true"></div>',
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
            $scope.fileURL = null;
            $scope.isMissingImportFile = function() {
                return ! $scope.inputFile;
            };
            $scope.fileUploadError = '';
            $scope.isUploading = false;
            $scope.title = $scope.title || 'Import STL File';
            $scope.description = $scope.description || 'Select File';

            $scope.importStlFile = function(inputFile) {
                if (! inputFile) {
                    return;
                }
                newSimFromSTL(inputFile);
            };

            function upload(inputFile, data) {
                var simId = data.models.simulation.simulationId;
                fileUpload.uploadFileToUrl(
                    inputFile,
                    $scope.isConfirming
                        ? {
                            confirm: $scope.isConfirming,
                        }
                        : null,
                    requestSender.formatUrl(
                        'uploadFile',
                        {
                            '<simulation_id>': simId,
                            '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                            '<file_type>': vtkPlotting.stlFileType,
                        }),
                    function(d) {
                        $('#simulation-import').modal('hide');
                        $scope.inputFile = null;
                        URL.revokeObjectURL($scope.fileURL);
                        $scope.fileURL = null;
                        requestSender.localRedirectHome(simId);
                    }, function (err) {
                        throw new Error(inputFile + ': Error during upload ' + err);
                    });
            }

            function newSimFromSTL(inputFile) {
                var url = $scope.fileURL;
                var model = appState.setModelDefaults(appState.models.simulation, 'simulation');
                model.name = inputFile.name.substring(0, inputFile.name.indexOf('.'));
                model.folder = fileManager.getActiveFolderPath();
                model.conductorFile = inputFile.name;
                appState.newSimulation(
                    model,
                    function (data) {
                        $scope.isUploading = false;
                        upload(inputFile, data);
                    },
                    function (err) {
                        throw new Error(inputFile + ': Error creating simulation ' + err);
                    }
                );
            }

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
SIREPO.app.directive('vtkAxes', function(appState, frameCache, panelState, requestSender, plotting, vtkAxisService, vtkPlotting, layoutService, utilities, geometry) {
    return {
        restrict: 'A',
        scope: {
            width: '<',
            height: '<',
            vtkObj: '<',
        },
        template: [
            '<g class="vtk-axes">',
                '<g data-ng-repeat="dim in geometry.basis" class="{{ dim }} axis">',
                    '<text class="{{ dim }}-axis-label"></text>',
                    '<text class="{{ dim }} axis-end low"></text>',
                    '<text class="{{ dim }} axis-end high"></text>',
                '</g>',
            '</g>',
        ].join(''),
        controller: function($scope, $element) {
            //srdbg('LOAD AXES');
            $scope.geometry = geometry;
        },

    };
});

// will be axis functions
SIREPO.app.service('vtkAxisService', function(appState, panelState, requestSender, frameCache, plotting, vtkPlotting, layoutService, utilities, geometry) {
    var svc = {};

    function edgeSorter(dim, shouldReverse) {
        return function(e1, e2) {
            if (! e1) {
                if (! e2) {
                    return 0;
                }
                return 1;
            }
            if (! e2) {
                return -1;
            }
            var pt1 = geometry.sortInDimension(e1.points(), dim, shouldReverse)[0];
            var pt2 = geometry.sortInDimension(e2.points(), dim, shouldReverse)[0];
            return (shouldReverse ? -1 : 1) * (pt2[dim] - pt1[dim]);
        };
    }

    function shouldReverseOnScreen(dim, index, screenDim, vpObj) {
        var currentEdge = vpObj.vpEdgesForDimension(dim)[index];
        var currDiff = currentEdge.points()[1][screenDim] - currentEdge.points()[0][screenDim];
        return currDiff < 0;
    }

    function select(selector, element) {
        var e = d3.select(element);
        return selector ? e.select(selector) : e;
    }

    svc.refresh = function(axes, axisCfg, boundRect, vpObj)  {

        // If an axis is shorter than this, don't display it -- the ticks will
        // be cramped and unreadable
        var minAxisDisplayLen = 50;

        for (var i in geometry.basis) {

            var dim = geometry.basis[i];

            var screenDim = axisCfg[dim].screenDim;
            var isHorizontal = screenDim === 'x';
            var axisEnds = isHorizontal ? ['◄', '►'] : ['▼', '▲'];
            var perpScreenDim = isHorizontal ? 'y' : 'x';

            var showAxisEnds = false;
            var axisSelector = '.' + dim + '.axis';
            var axisLabelSelector = '.' + dim + '-axis-label';

            // sort the external edges so we'll preferentially pick the left and bottom
            var externalEdges = vpObj.externalVpEdgesForDimension(dim)
                .sort(edgeSorter(perpScreenDim, ! isHorizontal));
            var seg = geometry.bestEdgeAndSectionInBounds(externalEdges, boundRect, dim, false);

            if (! seg) {
                // all possible axis ends offscreen, so try a centerline
                var cl = vpObj.vpCenterLineForDimension(dim);
                seg = geometry.bestEdgeAndSectionInBounds([cl], boundRect, dim, false);
                if (! seg) {
                    // don't draw axes
                    select(axisSelector).style('opacity', 0.0);
                    select(axisLabelSelector).style('opacity', 0.0);
                    continue;
                }
                showAxisEnds = true;
            }
            select(axisSelector).style('opacity', 1.0);

            var fullSeg = seg.full;
            var clippedSeg = seg.clipped;
            var reverseOnScreen = shouldReverseOnScreen(dim, seg.index, screenDim);
            var sortedPts = geometry.sortInDimension(clippedSeg.points(), screenDim, false);
            var axisLeft = sortedPts[0].x;
            var axisTop = sortedPts[0].y;
            var axisRight = sortedPts[1].x;
            var axisBottom = sortedPts[1].y;

            var newRange = Math.min(fullSeg.length(), clippedSeg.length());
            var radAngle = Math.atan(clippedSeg.slope());
            if (! isHorizontal) {
                radAngle -= Math.PI / 2;
                if (radAngle < -Math.PI / 2) {
                    radAngle += Math.PI;
                }
            }
            var angle = (180 * radAngle / Math.PI);

            var allPts = geometry.sortInDimension(fullSeg.points().concat(clippedSeg.points()), screenDim, false);

            var limits = reverseOnScreen ? [axisCfg[dim].max, axisCfg[dim].min] : [axisCfg[dim].min, axisCfg[dim].max];
            var newDom = [axisCfg[dim].min, axisCfg[dim].max];
            // 1st 2, last 2 points
            for (var m = 0; m < allPts.length; m += 2) {
                // a point may coincide with its successor
                var d = allPts[m].dist(allPts[m+1]);
                if (d != 0) {
                    var j = Math.floor(m / 2);
                    var k = reverseOnScreen ? 1 - j : j;
                    var l1 = limits[j];
                    var l2 = limits[1 - j];
                    var part = (l1 - l2) * d / fullSeg.length();
                    var newLimit = l1 - part;
                    newDom[k] = newLimit;
                }
            }
            var xform = 'translate(' + axisLeft + ',' + axisTop + ') ' +
                'rotate(' + angle + ')';

            axes[dim].scale.domain(newDom).nice();
            axes[dim].scale.range([reverseOnScreen ? newRange : 0, reverseOnScreen ? 0 : newRange]);

            // this places the axis tick labels on the appropriate side of the axis
            var outsideCorner = geometry.sortInDimension(vpObj.vpCorners(), perpScreenDim, isHorizontal)[0];
            var bottomOrLeft = outsideCorner.equals(sortedPts[0]) || outsideCorner.equals(sortedPts[1]);
            if (isHorizontal) {
                axes[dim].svgAxis.orient(bottomOrLeft ? 'bottom' : 'top');
            }
            else {
                axes[dim].svgAxis.orient(bottomOrLeft ? 'left' : 'right');
            }


            if (showAxisEnds) {
                axes[dim].svgAxis.ticks(0);
                select(axisSelector).call(axes[dim].svgAxis);
            }
            else {
                axes[dim].updateLabelAndTicks({
                    width: newRange,
                    height: newRange
                }, select);
            }

            select(axisSelector).attr('transform', xform);

            var dimLabel = axisCfg[dim].dimLabel;
            //d3self.selectAll(axisSelector + '-end')
            select(axisSelector + '-end')
                .style('opacity', showAxisEnds ? 1 : 0);

            var tf = axes[dim].svgAxis.tickFormat();
            if (tf) {
                select(axisSelector + '-end.low')
                    .text(axisEnds[0] + ' ' + dimLabel + ' ' + tf(reverseOnScreen ? newDom[1] : newDom[0]) + axes[dim].unitSymbol + axes[dim].units)
                    .attr('x', axisLeft)
                    .attr('y', axisTop)
                    .attr('transform', 'rotate(' + (angle) + ', ' + axisLeft + ', ' + axisTop + ')');

                select(axisSelector + '-end.high')
                    .attr('text-anchor', 'end')
                    .text(tf(reverseOnScreen ? newDom[0] : newDom[1]) + axes[dim].unitSymbol + axes[dim].units + ' ' + dimLabel + ' ' + axisEnds[1])
                    .attr('x', axisRight)
                    .attr('y', axisBottom)
                    .attr('transform', 'rotate(' + (angle) + ', ' + axisRight + ', ' + axisBottom + ')');
            }

            // counter-rotate the tick labels
            //var labels = d3self.selectAll(axisSelector + ' text');
            var labels = select(axisSelector + ' text');
            labels.attr('transform', 'rotate(' + (-angle) + ')');
            select(axisSelector + ' .domain').style({'stroke': 'none'});
            select(axisSelector).style('opacity', newRange < minAxisDisplayLen ? 0 : 1);

            var labelSpace = 2 * plotting.tickFontSize(select(axisSelector + '-label'));
            var labelSpaceX = (isHorizontal ? Math.sin(radAngle) : Math.cos(radAngle)) * labelSpace;
            var labelSpaceY = (isHorizontal ? Math.cos(radAngle) : Math.sin(radAngle)) * labelSpace;
            var labelX = axisLeft + (bottomOrLeft ? -1 : 1) * labelSpaceX + (axisRight - axisLeft) / 2.0;
            var labelY = axisTop + (bottomOrLeft ? 1 : -1) * labelSpaceY + (axisBottom - axisTop) / 2.0;
            var labelXform = 'rotate(' + (isHorizontal ? 0 : -90) + ' ' + labelX + ' ' + labelY + ')';

            select('.' + dim + '-axis-label')
                .attr('x', labelX)
                .attr('y', labelY)
                .attr('transform', labelXform)
                .style('opacity', (showAxisEnds || newRange < minAxisDisplayLen) ? 0 : 1);
        }
    };

    return svc;
});

// General-purpose vtk display
SIREPO.app.directive('vtkDisplay', function(appState, geometry, panelState, plotting, plotToPNG, vtkPlotting, vtkService, vtkUtils, utilities) {

    return {
        restrict: 'A',
        //transclude: {
        //    visabilityControlSlot: '?visabilityControl',
        //},
        scope: {
            enableAxes: '@',
            eventHandlers: '<',
            modelName: '@',
            reportId: '<',
        },
        templateUrl: '/static/html/vtk-display.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope, $element) {

            $scope.vtkUtils = vtkUtils;

            // common
            var api = {
                getMode: getMode,
                setCam: setCam,
                setBg: setBgColor,
            };

            var display = this;
            //TODO (mvk): fill in with common vtk stuff
            var cam = null;
            var canvas3d = null;
            var fsRenderer = null;
            var renderer = null;
            var renderWindow = null;
            var snapshotCtx = null;

            function getMode() {
                return $scope.mode;
            }

            // override these event handlers
            function handleDblClick(e) {
            }
            function handlePtrDown(e) {
            }
            function handlePtrMove(e) {
            }
            function handlePtrUp(e) {
            }
            function handleWheel(e) {
            }

            function setBgColor(hexColor) {
                renderer.setBackground(vtk.Common.Core.vtkMath.hex2float(hexColor));
            }

            function setCam(pos, vu) {
                if (! fsRenderer) {
                    return;
                }
                var cam = renderer.get().activeCamera;
                cam.setPosition(...(pos || [1, 0, 0]));
                cam.setFocalPoint(0, 0, 0);
                cam.setViewUp(...(vu || [0, 0, 1]));
                renderer.resetCamera();
                renderWindow.render();
            }

            $scope.init = function() {
                const rw = angular.element($($element).find('.vtk-canvas-holder'))[0];
                fsRenderer = vtk.Rendering.Misc.vtkFullScreenRenderWindow.newInstance({
                    background: [1, 1, 1, 1],
                    container: rw,
                    listenWindowResize: false,
                });
                renderer = fsRenderer.getRenderer();
                renderWindow = fsRenderer.getRenderWindow();
                var interactor = renderWindow.getInteractor();
                var mainView = renderWindow.getViews()[0];

                cam = renderer.get().activeCamera;

                var worldCoord = vtk.Rendering.Core.vtkCoordinate.newInstance({
                    renderer: renderer
                });
                worldCoord.setCoordinateSystemToWorld();

                rw.addEventListener('dblclick', ($scope.eventHandlers || {}).handleDblClick || handleDblClick);
                rw.onpointerdown = ($scope.eventHandlers || {}).handlePtrDown || handlePtrDown;
                rw.onpointermove = ($scope.eventHandlers || {}).handlePtrMove || handlePtrMove;
                rw.onpointerup = ($scope.eventHandlers || {}).handlePtrUp || handlePtrUp;
                rw.onwheel = ($scope.eventHandlers || {}).handleWheel || handleWheel;

                canvas3d = $($element).find('canvas')[0];

                // this canvas is used to store snapshots of the 3d canvas
                var snapshotCanvas = document.createElement('canvas');
                snapshotCtx = snapshotCanvas.getContext('2d');
                plotToPNG.addCanvas(snapshotCanvas, $scope.reportId);

                // allow ancestor scopes access to the renderer etc.
                $scope.$emit('vtk-init', {
                    api: api,
                    objects: {
                        camera: cam,
                        renderer: renderer,
                        window: renderWindow,
                    }
                });
            };

            $scope.canvasGeometry = function() {
                var vtkCanvasHolder = $($element).find('.vtk-canvas-holder')[0];
                return {
                    pos: $(vtkCanvasHolder).position(),
                    size: {
                        width: $(vtkCanvasHolder).width(),
                        height: $(vtkCanvasHolder).height()
                    }
                };
            };

            $scope.mode = vtkUtils.INTERACTION_MODE_MOVE;
            $scope.setMode = function(mode) {
                //srdbg(mode);
                $scope.mode = mode;
                renderWindow.getInteractor().setRecognizeGestures(mode === vtkUtils.INTERACTION_MODE_MOVE);
            };


            $scope.axisDirs = {
                dir: 1,
                x: {
                    camViewUp: [0, 0, 1]
                },
                y: {
                    camViewUp: [0, 0, 1]
                },
                z: {
                    camViewUp: [0, 1, 0]
                }
            };
            $scope.side = 'x';
            $scope.showSide = function(side) {
                if (side == $scope.side) {
                    $scope.axisDirs.dir *= -1;
                }
                $scope.side = side;
                var cp = geometry.basisVectors[side].map(function (c) {
                    return c * $scope.axisDirs.dir;
                });
                setCam(cp, $scope.axisDirs[side].camViewUp);
            };

            appState.whenModelsLoaded($scope, function () {
                srdbg('vtk display models loaded');
                $scope.init();
            });
        },

        //link: function link(scope, element) {
        //    vtkPlotting.vtkPlot(scope, element);
        //},
    };
});

// general-purpose vtk methods
SIREPO.app.service('vtkService', function(appState, panelState, requestSender, frameCache, plotting, vtkPlotting, layoutService, utilities, geometry) {
    var svc = {};
    return svc;
});

SIREPO.app.factory('vtkUtils', function() {

    var self = {};

    self.INTERACTION_MODE_MOVE = 'move';
    self.INTERACTION_MODE_SELECT = 'select';
    self.INTERACTION_MODES = [self.INTERACTION_MODE_MOVE, self.INTERACTION_MODE_SELECT];

    // Converts vtk colors ranging from 0 -> 255 to 0.0 -> 1.0
    // can't map, because we will still have a UINT8 array
    self.rgbToFloat = function (rgb) {
        var sc = [];
        for (var i = 0; i < rgb.length; ++i) {
            sc.push(rgb[i] / 255.0);
        }
        return sc;
    };

    return self;
});
