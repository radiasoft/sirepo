'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;
SIREPO.appReportTypes = [
    '<div data-ng-switch-when="dicomTranspose" data-dicom-plot="" class="sr-plot" data-dicom-plane="t" data-model-name="{{ modelKey }}"></div>',
    '<div data-ng-switch-when="dicomSagittal" data-dicom-plot="" class="sr-plot" data-dicom-plane="s" data-model-name="{{ modelKey }}"></div>',
    '<div data-ng-switch-when="dicomCoronal" data-dicom-plot="" class="sr-plot" data-dicom-plane="c" data-model-name="{{ modelKey }}"></div>',
    '<div data-ng-switch-when="dicom3d" data-dicom-3d="" class="sr-plot" data-model-name="{{ modelKey }}" data-report-id="reportId"></div>',
].join('');
SIREPO.appPanelHeadingButtons = [
    '<div data-ng-if="isReport && modelKey == \'dicom3DReport\'" style="display: inline-block">',
      '<div data-toggle-report-button="dvh"></div>',
    '</div>',
    '<div data-ng-if="isReport && modelKey == \'dvhReport\'" style="display: inline-block">',
      '<div data-toggle-report-button="3d"></div>',
    '</div>',
].join('');

SIREPO.app.factory('iradService', function(appState, requestSender, $rootScope) {
    var self = {};
    var simulationId, roiPoints;
    var slicePosition = {};

    self.dicomTitle = function(dicomPlane) {
        return appState.enumDescription('DicomPlane', dicomPlane)
            + (slicePosition[dicomPlane]
               ? (' ' + slicePosition[dicomPlane].toFixed(3) + 'mm')
               : '');
    };

    self.downloadDataFile = function(modelName, frame) {
        var url = requestSender.formatUrl(
            'downloadDataFile',
            {
                '<simulation_id>': appState.models.simulation.simulationId,
                '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                '<model>': modelName,
                '<frame>': frame,
            });
        var reader = vtk.IO.Core.vtkHttpDataSetReader.newInstance();
        reader.setUrl(url, {
            compression: 'zip',
            fullpath: true,
            loadData: true,
        }).then(function() {
            $rootScope.$broadcast('irad-data-available', reader, frame);
        });
    };

    self.getROIPoints = function() {
        return roiPoints;
    };

    self.loadROIPoints = function() {
        if (simulationId == appState.models.simulation.simulationId) {
            $rootScope.$broadcast('roiPointsLoaded');
            return;
        }
        requestSender.getApplicationData(
            {
                method: 'roi_points',
                simulationId: appState.models.simulation.simulationId,
            },
            function(data) {
                if (! appState.isLoaded()) {
                    return;
                }
                simulationId = appState.models.simulation.simulationId;
                //dicomHistogram = data.models.dicomHistogram;
                roiPoints = data.regionOfInterest;
                $rootScope.$broadcast('roiPointsLoaded');
            });
    };

    self.setSlicePosition = function(dicomPlane, position) {
        slicePosition[dicomPlane] = position;
    };

    $rootScope.$on('modelsUnloaded', function() {
        simulationId = null;
        roiPoints = null;
        slicePosition = {};
    });

    appState.setAppService(self);
    return self;
});

SIREPO.app.controller('SourceController', function (appState, iradService, $scope) {
    var self = this;
    self.iradService = iradService;

    self.showReport = function(toggle) {
        if (! appState.isLoaded()) {
            if (toggle == '3d') {
                return true;
            }
            return false;
        }
        return appState.models.dvhReport.toggle == toggle;
    };

    //TODO(pjm): work-around to turn off plot legend on DVH report
    $scope.$on('sr-plotLinked', function(event) {
        var plotScope = event.targetScope;
        if (plotScope.modelName == 'dvhReport') {
            var loadFunction = plotScope.load;
            plotScope.load = function(json) {
                loadFunction(json);
                plotScope.margin.bottom = 47;
            };
        }
    });
});

SIREPO.app.directive('appFooter', function() {
    return {
	restrict: 'A',
	scope: {
            nav: '=appFooter',
	},
        template: [
            '<div data-common-footer="nav"></div>',
	].join(''),
    };
});

SIREPO.app.directive('appHeader', function(appState, panelState) {
    return {
	restrict: 'A',
	scope: {
            nav: '=appHeader',
	},
        template: [
            '<div data-app-header-brand="nav"></div>',
            '<div data-app-header-left="nav" data-simulations-link-text="Studies"></div>',
            '<div data-app-header-right="nav">',
              '<app-header-right-sim-loaded>',
		'<div data-sim-sections="">',
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-flash"></span> Source</a></li>',
		'</div>',
              '</app-header-right-sim-loaded>',
              '<app-settings>',
		//  '<div>App-specific setting item</div>',
              '</app-settings>',
              '<app-header-right-sim-list>',
              '</app-header-right-sim-list>',
            '</div>',
	].join(''),
    };
});

SIREPO.app.directive('dicom3d', function(appState, geometry, iradService, plotting, requestSender, vtkPlotting, vtkToPNG) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
            reportId: '<',
        },
        template: [
              '<div class="sr-dicom3d-content"></div>',
            // force the Download Report menu to appear
            '<svg style="display: none"></svg>',
        ].join(''),
        controller: function($scope, $element) {
            var fsRenderer, orientationMarker, pngCanvas;
            var actor = null;
            var roiActors = [];
            //TODO(pjm): set the variables below when selecting from Components panel
            var selected3DROI = 31; //null; //31;
            var showRTDose = false;
            $scope.isClientOnly = true;

            // the coordinate system may depend on the data?
            var t = geometry.transform([
                [1, 0, 0],
                [0, -1, 0],
                [0, 0, -1]
            ]);
            var cm = vtkPlotting.coordMapper(t);
            var ha = cm.buildFromSource(homunculus()).actor;

            function addOrientationMarker() {
                orientationMarker = vtk.Interaction.Widgets.vtkOrientationMarkerWidget.newInstance({
                    actor: ha,   //vtk.Rendering.Core.vtkAxesActor.newInstance(),
                    interactor: fsRenderer.getRenderWindow().getInteractor(),
                    viewportCorner: vtk.Interaction.Widgets.vtkOrientationMarkerWidget.Corners.TOP_RIGHT,
                    viewportSize: 0.10,
                });
                orientationMarker.setEnabled(true);
            }

            function color(v) {
                return vtk.Common.Core.vtkMath.hex2float(v);
            }

            function getCoord(pts, cIdx) {
                return pts.filter(function (p, pIdx) {
                    return pIdx % 2 === cIdx;
                });
            }

            function homunculus(bodyCenter) {

                bodyCenter = bodyCenter || [0, 0, 0];
                var thetaRez = 24;
                var phiRez = 24;
                var bodyRadius = 1.0;
                var bodyHeight = 3 * bodyRadius;

                var source = vtk.Filters.General.vtkAppendPolyData.newInstance();

                // plane names
                var VENTRAL = SIREPO.APP_SCHEMA.constants.planeVentral;
                var DORSAL = SIREPO.APP_SCHEMA.constants.planeDorsal;
                var DEXTER = SIREPO.APP_SCHEMA.constants.planeDexter;
                var SINISTER = SIREPO.APP_SCHEMA.constants.planeSinister;
                var ROSTRAL = SIREPO.APP_SCHEMA.constants.planeRostral;
                var CAUDAL = SIREPO.APP_SCHEMA.constants.planeCaudal;

                var quadrantColors = {};
                quadrantColors[VENTRAL + DEXTER] = [0, 255, 0, 255];
                quadrantColors[VENTRAL + SINISTER] = [255, 0, 0, 255];
                quadrantColors[DORSAL + DEXTER] = [0, 0, 255, 255];
                quadrantColors[DORSAL + SINISTER] = [255, 255, 0, 255];

                var extentPlanes = {};
                extentPlanes[ROSTRAL] = {norm: [0, 0, -1], origin: [0, 0, bodyHeight / 2.0]};
                extentPlanes[CAUDAL] = {norm: [0, 0, 1], origin: [0, 0, -bodyHeight / 2.0]};

                var quadrantPlanes = {};
                quadrantPlanes[VENTRAL] = {norm: [0, 1, 0], origin: bodyCenter};
                quadrantPlanes[DEXTER] = {norm: [1, 0, 0], origin: bodyCenter};
                quadrantPlanes[DORSAL] = {norm: [0, -1, 0], origin: bodyCenter};
                quadrantPlanes[SINISTER] = {norm: [-1, 0, 0], origin: bodyCenter};

                var headRadius = 0.70 * bodyRadius;
                var headCenter = [bodyCenter[0], bodyCenter[1], bodyCenter[2] + bodyHeight / 2.0 + 0.9 * headRadius];
                var headQuadrants = {};
                headQuadrants[VENTRAL + DEXTER] = {th1: 0, th2: 90};
                headQuadrants[VENTRAL + SINISTER] = {th1: 90, th2: 180};
                headQuadrants[DORSAL + DEXTER] = {th1: 270, th2: 360};
                headQuadrants[DORSAL + SINISTER] = {th1: 180, th2: 270};

                var n = 0;
                [VENTRAL, DORSAL].forEach(function (vd) {
                    [SINISTER, DEXTER].forEach(function (sd) {
                        var qc = quadrantColors[vd + sd];
                        var s = vtkPlotting.cylinderSection(
                            bodyCenter, [0, 0 , 1], bodyRadius, bodyHeight,
                            [extentPlanes[ROSTRAL], extentPlanes[CAUDAL], quadrantPlanes[vd], quadrantPlanes[sd]]
                        ).getOutputData();
                        vtkPlotting.setColorScalars(s, qc);
                        if (n === 0) {
                            source.setInputData(s);
                        }
                        else {
                            source.addInputData(s);
                        }
                        ++n;
                        var hq = headQuadrants[vd + sd];
                        s = vtk.Filters.Sources.vtkSphereSource.newInstance({
                            radius: headRadius,
                            center: headCenter,
                            thetaResolution: thetaRez,
                            phiResolution: phiRez,
                            startTheta: hq.th1,
                            endTheta: hq.th2
                        }).getOutputData();
                        vtkPlotting.setColorScalars(s, qc);
                        source.addInputData(s);
                        ++n;
                    });
                });

                var noseRadius = 0.33 * headRadius;
                var noseCenter = [headCenter[0], bodyCenter[1] + headRadius + 0.66 * noseRadius, headCenter[2]];
                var s = vtk.Filters.Sources.vtkSphereSource.newInstance({
                    radius: noseRadius,
                    center: noseCenter,
                    thetaResolution: thetaRez,
                    phiResolution: phiRez,
                }).getOutputData();
                vtkPlotting.setColorScalars(s, [255, 255, 255, 255]);
                source.addInputData(s);
                ++n;

                // might omit limbs for clarity, but leaving the code
                /*
                var limbRadius = bodyRadius / 6.0;
                var limbGeom = {};
                limbGeom[ROSTRAL] = {
                    length: 0.5 * bodyHeight,
                    angle: -Math.PI / 3.0,
                    zPos: 0.50 * bodyHeight,
                };
                limbGeom[CAUDAL] = {
                    length: 0.75 * bodyHeight,
                    angle: Math.PI / 12.0,
                    zPos: -0.75 * bodyHeight,
                };

                [ROSTRAL, CAUDAL].forEach(function (rc, rcIdx) {
                    var len = limbGeom[rc].length;
                    var th = limbGeom[rc].angle;
                    var rcDir = 2 * rcIdx - 1;
                    var offset = Math.hypot(len / 2.0, limbRadius) *
                        Math.sin(th + Math.sign(th) * Math.atan2(limbRadius, len / 2.0)) -
                        Math.sign(th) * 2 * limbRadius * Math.cos(th) +
                        rcDir * bodyRadius;
                    [VENTRAL, DORSAL].forEach(function (vd) {
                        [SINISTER, DEXTER].forEach(function (sd, sdIdx) {
                            var sdDir = 2 * sdIdx - 1;
                            var s = vtkPlotting.cylinderSection(
                               [rcDir * sdDir * offset, 0, limbGeom[rc].zPos],
                                [-sdDir * Math.sin(th), 0, Math.cos(th)],
                                limbRadius,
                                len,
                                [extentPlanes[ROSTRAL], extentPlanes[CAUDAL], quadrantPlanes[vd]]
                            ).getOutputData();
                            vtkPlotting.setColorScalars(s, quadrantColors[vd + sd]);
                            source.addInputData(s);
                            ++n;
                        });
                    });
                });
                */
                return source;
            }

            function refresh(event, reader, frame) {
                if (frame == 2 && ! showRTDose) {
                    return;
                }
                removeActors();

                actor = vtk.Rendering.Core.vtkVolume.newInstance();
                var mapper = vtk.Rendering.Core.vtkVolumeMapper.newInstance();
                actor.setMapper(mapper);
                mapper.setInputConnection(reader.getOutputPort());
                var renderer = fsRenderer.getRenderer();

                var ofun, ctfun;
                if (frame == 1) {
                    //mapper.setSampleDistance(0.7);
                    //mapper.setSampleDistance(4);
                    ctfun = vtk.Rendering.Core.vtkColorTransferFunction.newInstance();
                    ctfun.addRGBPoint(200.0, 0.4, 0.2, 0.0);
                    ctfun.addRGBPoint(2000.0, 1.0, 1.0, 1.0);
                    ofun = vtk.Common.DataModel.vtkPiecewiseFunction.newInstance();
                    ofun.addPoint(200.0, 0.0);
                    ofun.addPoint(1200.0, 0.5);
                    ofun.addPoint(3000.0, 0.8);
                    actor.getProperty().setRGBTransferFunction(0, ctfun);
                    actor.getProperty().setScalarOpacity(0, ofun);
                    //      actor.getProperty().setScalarOpacityUnitDistance(0, 4.5);
                    actor.getProperty().setScalarOpacityUnitDistance(0, 10);
                    actor.getProperty().setInterpolationTypeToLinear();
                    actor.getProperty().setUseGradientOpacity(0, true);
                    //actor.getProperty().setGradientOpacityMinimumValue(0, 15);
                    actor.getProperty().setGradientOpacityMinimumValue(0, 99);
                    actor.getProperty().setGradientOpacityMinimumOpacity(0, 0.0);
                    actor.getProperty().setGradientOpacityMaximumValue(0, 100);
                    actor.getProperty().setGradientOpacityMaximumOpacity(0, 1.0);
                    //      actor.getProperty().setShade(true);
                    actor.getProperty().setAmbient(0.2);
                    actor.getProperty().setDiffuse(0.7);
                    actor.getProperty().setSpecular(0.3);
                    actor.getProperty().setSpecularPower(8.0);

                    renderer.addVolume(actor);
                    renderer.resetCamera();
                    var cam =  renderer.getActiveCamera();
                    var pos = cam.getPosition();
                    cam.zoom(1.5);
                    cam.roll(30);
                    cam.elevation(-100);
                    renderer.updateLightsGeometryToFollowCamera();

                    addOrientationMarker();
                }
                else {
                    ofun = vtk.Common.DataModel.vtkPiecewiseFunction.newInstance();
                    ofun.addPoint(0, 0);
                    var dmin = 100000;
                    var dmax = 1051663;
                    ofun.addPoint(dmin, 0);
                    ofun.addPoint(dmax, 0.01);
                    actor.getProperty().setScalarOpacity(0, ofun);
                    actor.getProperty().setInterpolationTypeToLinear();
                    ctfun = vtk.Rendering.Core.vtkColorTransferFunction.newInstance();
                    ctfun.addRGBPoint(dmin, 1.0, 1.0, 0.0);
                    ctfun.addRGBPoint(dmax, 0.8, 0.0, 0.0);
                    actor.getProperty().setRGBTransferFunction(0, ctfun);
                    renderer.addVolume(actor);
                }
                fsRenderer.getRenderWindow().render();
                pngCanvas.copyCanvas();
            }

            function removeActors() {
                var renderer = fsRenderer.getRenderer();
                renderer.getActors().forEach(function(actor) {
                    renderer.removeActor(actor);
                });
            }

            function showActiveRoi() {
                roiActors.forEach(function (a) {
                    fsRenderer.getRenderer().removeActor(a);
                });
                roiActors = [];

                var roi = selected3DROI ? iradService.getROIPoints()[selected3DROI] : null;
                if (! roi) {
                    return;
                }

                var aColor = roi.color[0].map(function (c) {
                    return parseFloat(c) / 255.0;
                });
                var c, i, j, z, segment, points;
                var bnds = [
                    Number.MAX_VALUE, -Number.MAX_VALUE,
                    Number.MAX_VALUE, -Number.MAX_VALUE,
                    Number.MAX_VALUE, -Number.MAX_VALUE,
                ];
                var nGrid = [0, 0, 0];

                var aBnds = actor.getBounds().slice();
                var aCtr = [
                    (aBnds[0] + aBnds[1]) / 2,
                    (aBnds[2] + aBnds[3]) / 2,
                    (aBnds[4] + aBnds[5]) / 2
                ];
                var aSize = [
                    aBnds[1] - aBnds[0],
                    aBnds[3] - aBnds[2],
                    aBnds[5] - aBnds[4]
                ];
                //srdbg('actor bnds', aBnds, 'ctr', aCtr, 'size', aSize);

                var maxSegs = 0;
                for (z in roi.contour) {
                    ++nGrid[2];
                    bnds[4] = Math.min(bnds[4], parseFloat(z));
                    bnds[5] = Math.max(bnds[5], parseFloat(z));
                    var nSegs = roi.contour[z].length;
                    maxSegs = Math.max(maxSegs, nSegs);
                    for (segment = 0; segment < nSegs; segment++) {
                        points = roi.contour[z][segment];
                        for (i = 0; i < 2; ++i) {
                            c = getCoord(points, i);
                            nGrid[i] = Math.max(nGrid[i], c.length);
                            bnds[2 * i] = Math.min(bnds[2 * i], Math.min.apply(null, c));
                            bnds[2 * i + 1] = Math.max(bnds[2 * i + 1], Math.max.apply(null, c));
                        }
                    }
                }
                //srdbg('max grid', nGrid);

                var zShift = 2 * aBnds[4];
                bnds[4] = zShift - bnds[4];
                bnds[5] = zShift - bnds[5];

                var ctr = [
                    (bnds[0] + bnds[1]) / 2.0,
                    (bnds[2] + bnds[3]) / 2.0,
                    (bnds[4] + bnds[5]) / 2.0,
                ];
                //srdbg('shifted bnds', bnds.slice(), 'ctr', ctr, 'size', sz);

                var zPlanes = Object.keys(roi.contour)
                    .sort(function (zp1, zp2) {
                    return parseFloat(zp1) - parseFloat(zp2);
                });
                //var shZPlanes = zPlanes.map(function (zp) {
                //    return '' +  (zShift - parseFloat(zp));
                //});
                var dz = Math.abs((parseFloat(zPlanes[zPlanes.length - 1]) - parseFloat(zPlanes[0])) / (zPlanes.length - 1));
                //srdbg('zplanes', zPlanes);

                // don't go beyond maximal grid (yet?)
                nGrid = [
                    Math.min(128, nGrid[0]),
                    Math.min(128, nGrid[1]),
                    Math.min(128, nGrid[2])
                ];
                //srdbg('final grid', nGrid);
                var gridSpc = [
                    Math.abs((bnds[1] - bnds[0])) / (nGrid[0] - 1),
                    Math.abs((bnds[3] - bnds[2])) / (nGrid[1] - 1),
                    Math.abs((bnds[5] - bnds[4])) / (nGrid[2] - 1),
                ];

                var segBnds = Array(maxSegs);
                var segGrid = Array(maxSegs);
                var segCtr = Array(maxSegs);
                for (i = 0; i < maxSegs; ++i) {
                    segBnds[i] = [];
                    for (j = 0; j < 6; ++j) {
                        segBnds[i].push((1 - 2 * (j % 2)) * Number.MAX_VALUE);
                    }
                }

                var polys = {};
                zPlanes.forEach(function (zp, zpIdx) {
                    var z = parseFloat(zp);  // raw z
                    var shz = zShift - z;  // shift z
                    var revzp = zPlanes[zPlanes.length - zpIdx - 1];
                    var revz = parseFloat(revzp);  // reverse z
                    var shrevz = zShift - revz;  // reverse shift z
                    var nSegs = roi.contour[zp].length;
                    var zPolys = Array(nSegs);
                    for (segment = 0; segment < nSegs; segment++) {
                        segBnds[segment][4] = Math.min(segBnds[segment][4], shz);
                        segBnds[segment][5] = Math.max(segBnds[segment][5], shz);
                        var cPoints = roi.contour[zp][segment];
                        var segPolyPts = Array(cPoints.length / 2);
                        for (i = 0; i < cPoints.length; i += 2) {
                            segPolyPts[i / 2] = [cPoints[i], cPoints[i + 1], shrevz];
                            for (j = 0; j < 2; ++j) {
                                segBnds[segment][2 * j] = Math.min(segBnds[segment][2 * j], cPoints[i + j]);
                                segBnds[segment][2 * j + 1] = Math.max(segBnds[segment][2 * j + 1], cPoints[i + j]);
                            }
                        }
                        zPolys[segment] = geometry.polygon(segPolyPts);
                    }
                    //polys[zp] = zPolys;
                    // reverse the z plane associated with this polygon, and shift fot later lookup
                    polys['' + shrevz] = zPolys;
                });
                //srdbg('segBnds', segBnds.slice());
                //srdbg('polys', polys);

                // reduce the space for marching cubes to the bounds of each segment
                for (i = 0; i < maxSegs; ++i) {
                    var b = segBnds[i];
                    segGrid[i] = Array(3);
                    segCtr[i] = Array(3);
                    for (j = 0; j < 3; ++j) {
                        // add a grid spacing on each side to close off the volume - or
                        // not, it does slow things down and may not be necessary
                        //b[2 * j] -= gridSpc[j];  b[2 * j + 1] += gridSpc[j];
                        //segGrid[i][j] = 2 + Math.floor(Math.abs((b[2 * j + 1] - b[2 * j])) / gridSpc[0]),
                        // must be at least 2 grid points in each direction
                        segGrid[i][j] = Math.max(
                            2,
                            Math.floor(Math.abs((b[2 * j + 1] - b[2 * j])) / gridSpc[j])
                        );
                        segCtr[i][j] = (b[2 * j] + b[2 * j + 1]) / 2.0;
                    }
                }
                //srdbg('seg grid', segGrid, 'ctr', segCtr);

                // used by the vtk sample function to decide which points in the volume are in or out
                function segmentImpl(seg) {
                    return {
                        evaluateFunction: function (coords) {
                            var d = Math.hypot(ctr[0] - coords[0], ctr[1] - coords[1], ctr[2] - coords[2]);
                            // closest zplane
                            // don't use reverse zp;  otherwise it undoes the previous reversal
                            var zpIdx = zPlanes.length + Math.floor((coords[2] - bnds[4]) / dz) - 1;
                            var zp = '' + (zShift - parseFloat(zPlanes[zpIdx]));
                            if (! polys[zp] || ! polys[zp][seg]) {
                                return -d;
                            }
                            return polys[zp][seg].containsPoint(coords) ? d : -d;
                        },
                    };
                }

                for (i = 0; i < maxSegs; ++i) {
                    var s = vtk.Imaging.Hybrid.vtkSampleFunction.newInstance({
                        implicitFunction: segmentImpl(i),
                        modelBounds: segBnds[i],
                        sampleDimensions: segGrid[i]
                    });
                    c = vtk.Filters.General.vtkImageMarchingCubes.newInstance({ contourValue: 0.0 });
                    c.setInputConnection(s.getOutputPort());
                    var m = vtk.Rendering.Core.vtkMapper.newInstance();
                    m.setInputConnection(c.getOutputPort());
                    var a = vtk.Rendering.Core.vtkActor.newInstance({
                        mapper: m,
                    });
                    //a.getProperty().setColor(...aColor);
                    // hacks for report screenshot
                    a.getProperty().setColor(0.0, 0.9, 0.9);
                    if (i === 0) {
                       a.getProperty().setOpacity(0.6);
                    }
                    roiActors.push(a);
                    fsRenderer.getRenderer().addActor(a);
                }

                fsRenderer.getRenderer().resetCamera();
                fsRenderer.getRenderWindow().render();
            }

            $scope.destroy = function() {
                window.removeEventListener('resize', fsRenderer.resize);
                fsRenderer.getInteractor().unbindEvents();
                pngCanvas.destroy();
            };

            $scope.init = function() {
                if (! appState.isLoaded()) {
                    appState.whenModelsLoaded($scope, $scope.init);
                    return;
                }
                fsRenderer = vtk.Rendering.Misc.vtkFullScreenRenderWindow.newInstance({
                    background: color('#000'),
                    container: $('.sr-dicom3d-content')[0],
                });
                pngCanvas = vtkToPNG.pngCanvas($scope.reportId, fsRenderer, $element);
                iradService.downloadDataFile($scope.modelName, 1);
            };

            $scope.$on('roiPointsLoaded', function() {
                //srdbg('received points loaded', iradService.getROIPoints());
                showActiveRoi();
            });

            $scope.$on('irad-data-available', refresh);

            $scope.resize = function() {};
        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});

function dicomROIFeature($scope, iradService) {
    var roiLine, xAxisScale, yAxisScale;
    var frameId = null;
    var roiContours = null;

    function addContours() {
        clearContours();
        var rois = iradService.getROIPoints();
        if (! rois) {
            return;
        }
        var yMax = $scope.yMax();
        if (! roiContours && Object.keys(rois).length === 0) {
            return;
        }
        Object.keys(rois).forEach(function(roiNumber) {
            rois[roiNumber].isVisible = false;
        });
        roiContours = {};
        Object.keys(rois).forEach(function(roiNumber) {
            var roi = rois[roiNumber];
            var contourDataList = getContourForFrame(roi);
            if (contourDataList) {
                var points = [];
                contourDataList.forEach(function(contourData) {
                    if (points.length) {
                        // roiLine.defined() controls breaks between path segments
                        points.push(null);
                    }
                    for (var i = 0; i < contourData.length; i += 2) {
                        points.push([
                            contourData[i],
                            //TODO(pjm): flipud
                            yMax - contourData[i + 1],
                        ]);
                    }
                });
                roi.isVisible = points.length ? true : false;
                var parent = $scope.select('.draw-area');
                roiContours[roiNumber] = {
                    roi: roi,
                    roiNumber: roiNumber,
                    points: points,
                    roiPath: parent.append('path')
                        .attr('class', 'dicom-roi')
                        .datum(points),
                    dragPath: parent.append('path')
                        .attr('class', 'dicom-dragpath')
                        .datum(points),
                };
                roiContours[roiNumber].dragPath.append('title').text(roi.name);
            }
        });
        redrawContours();
    }

    function clearContours() {
        roiContours = null;
        $scope.select().selectAll('.draw-area path').remove();
    }

    function getContourForFrame(roi) {
        if (roi.contour && roi.contour[frameId]) {
            return roi.contour[frameId];
        }
        return null;
    }

    function redrawContours() {
        if (! roiContours) {
            addContours();
            return;
        }
        //var canDrag = false; //rs4piService.isEditMode('select');
        //var activeROI = null; //rs4piService.getActiveROI();
        Object.keys(roiContours).forEach(function(roiNumber) {
            var v = roiContours[roiNumber];
            v.roiPath.attr('d', roiLine)
                .attr('style', roiStyle(v.roi, roiNumber));
            v.dragPath.attr('d', roiLine)
                .classed('dicom-dragpath-select', true)
                .classed('selectable-path', true);
        });
    }

    function roiStyle(roi, roiNumber) {
        var color = roi.color;
        return 'stroke: rgb(' + color.join(',') + ')';
    }

    return {
        clear: clearContours,
        draw: redrawContours,
        init: function(x, y) {
            xAxisScale = x;
            yAxisScale = y;
            roiLine = d3.svg.line()
                .defined(function(d) { return d !== null; })
                .interpolate('linear-closed')
                .x(function(d) {
                    return xAxisScale(d[0]);
                })
                .y(function(d) {
                    return yAxisScale(d[1]);
                });
        },
        load: function(newFrameId) {
            if (frameId != newFrameId) {
                frameId = newFrameId;
                roiContours = null;
            }
        }
    };
}

function imageFeature() {
    var cacheCanvas, colorScale, heatmap, imageData, transparency, xAxisScale, yAxisScale;

    function initColormap(dicomWindow) {
        if (! colorScale) {
            // var zMin = dicomWindow.center - dicomWindow.width / 2;
            // var zMax = dicomWindow.center + dicomWindow.width / 2;
            var zMin = -160;
            var zMax = 240;
            var colorRange = [0, 255];
            colorScale = d3.scale.linear()
                .domain([zMin, zMax])
                .rangeRound(colorRange)
                .clamp(true);
        }
    }

    function isValidHeatmap() {
        return heatmap && heatmap.length;
    }
    var DOSE_CUTOFF = 10;

    return {
        DOSE_CUTOFF: DOSE_CUTOFF,
        clearColorScale: function() {
            colorScale = null;
        },
        draw: function(canvas, xDomain, yDomain) {
            //console.log('draw:', xDomain, yDomain);
            var xZoomDomain = xAxisScale.domain();
            var yZoomDomain = yAxisScale.domain();
            var zoomWidth = xZoomDomain[1] - xZoomDomain[0];
            var zoomHeight = yZoomDomain[1] - yZoomDomain[0];
            var ctx = canvas.getContext('2d');
            ctx.imageSmoothingEnabled = false;
            ctx.msImageSmoothingEnabled = false;
            ctx.drawImage(
                cacheCanvas,
                -(xZoomDomain[0] - xDomain[0]) / zoomWidth * canvas.width,
                (yDomain[0] - yZoomDomain[0]) / zoomHeight * canvas.height,
                (xDomain[1] - xDomain[0]) / zoomWidth * canvas.width,
                (yDomain[1] - yDomain[0]) / zoomHeight * canvas.height);
        },
        init: function(x, y) {
            xAxisScale = x;
            yAxisScale = y;
            cacheCanvas = document.createElement('canvas');
        },
        load: function(pixels) {
            heatmap = pixels;
            if (! isValidHeatmap()) {
                return;
            }
            cacheCanvas.width = heatmap[0].length;
            cacheCanvas.height = heatmap.length;
            imageData = cacheCanvas.getContext('2d').getImageData(0, 0, cacheCanvas.width, cacheCanvas.height);
        },
        prepareImage: function(dicomWindow, isOverlay) {
            if (! isValidHeatmap()) {
                return;
            }
            if (! isOverlay) {
                initColormap(dicomWindow);
            }
            var width = imageData.width;
            var height = imageData.height;
            var doseTransparency = isOverlay ? parseInt(transparency / 100.0 * 0xff) : 0;

            for (var yi = 0, p = -1; yi < height; ++yi) {
                for (var xi = 0; xi < width; ++xi) {
                    var v = heatmap[yi][xi];
                    if (! v) {
                        imageData.data[++p] = 0;
                        imageData.data[++p] = 0;
                        imageData.data[++p] = 0;
                        imageData.data[++p] = isOverlay ? 0 : 0xff;
                        continue;
                    }
                    var c = colorScale(v);
                    if (isOverlay) {
                        c = d3.rgb(c);
                        imageData.data[++p] = c.r;
                        imageData.data[++p] = c.g;
                        imageData.data[++p] = c.b;
                        imageData.data[++p] = doseTransparency;
                        //TODO(pjm): add adjustable % cut-off
                        if (v < DOSE_CUTOFF) {
                            imageData.data[p] = 0;
                        }
                    }
                    else {
                        imageData.data[++p] = c;
                        imageData.data[++p] = c;
                        imageData.data[++p] = c;
                        imageData.data[++p] = 0xff;
                    }
                }
            }
            cacheCanvas.getContext('2d').putImageData(imageData, 0, 0);
        },
        setColorScale: function(c, doseTransparency) {
            colorScale = c;
            if (doseTransparency < 0) {
                doseTransparency = 0;
            }
            else if (doseTransparency > 100) {
                doseTransparency = 100;
            }
            transparency = doseTransparency;
        },
    };
}

SIREPO.app.directive('dicomPlot', function(appState, panelState, plotting, iradService, $interval, $rootScope) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
            dicomPlane: '@',
        },
        template: [
          '<div style="position: relative" ng-class="{\'sr-plot-loading\': isLoading(), \'sr-plot-cleared\': dataCleared}">',
            '<canvas ng-attr-style="position: absolute; left: {{ margin.left }}px; top: {{ margin.top }}px;"></canvas>',
            '<div><svg class="sr-plot" style="position: relative;" ng-attr-width="{{ margin.left + margin.right + canvasWidth }}" ng-attr-height="{{ margin.top + margin.bottom + canvasHeight}}">',
              '<g ng-attr-transform="translate({{ margin.left }},{{ margin.top }})">',
                '<svg class="plot-viewport" ng-attr-width="{{ canvasWidth }}" ng-attr-height="{{ canvasHeight }}">',
                  '<rect class="overlay mouse-zoom" ng-attr-width="{{ canvasWidth }}" ng-attr-height="{{ canvasHeight }}"></rect>',
                  '<defs>',
                    '<clippath id="{{ modelName }}-clip">',
                      '<rect ng-attr-width="{{ canvasWidth }}" ng-attr-height="{{ canvasHeight }}"></rect>',
                    '</clippath>',
                  '</defs>',
                  '<g class="draw-area" ng-attr-clip-path="url(#{{ modelName }}-clip)"></g>',
                '</svg>',
              '</g>',
            '</svg></div>',
          '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.canvasHeight = 0;
            $scope.canvasWidth = 0;
            $scope.margin = {top: 0, left: 0, right: 0, bottom: -5};

            var canvas, dicomDomain, xAxisScale, xValues, yAxisScale, yValues, zoom;
            var data3d, dose3d, frameScale;
            var doseFeature = imageFeature();
            var dicomFeature = imageFeature();
            $scope.isClientOnly = true;

            //TODO(pjm): get this from scope
            // c, t, s
            var dicomPlane = $scope.dicomPlane;
            //TODO(pjm): get this from appState
            //var frameIdx = dicomPlane == 't' ? 41 : dicomPlane == 'c' ? 301 : 255;
            var frameIdx = dicomPlane == 't' ? 110 : dicomPlane == 'c' ? 301 : 255;
            var roiFeature = dicomPlane == 't' ? dicomROIFeature($scope, iradService) : null;
            var zFrame, slicePosition;

            function advanceFrame() {
                if (! d3.event || ! d3.event.sourceEvent || d3.event.sourceEvent.type == 'mousemove') {
                    return;
                }
                var scale = d3.event.scale;
                // don't advance for small scale adjustments, ex. from laptop touchpad
                if (Math.abs(scale - 1) < 0.03) {
                    return;
                }
                $scope.$applyAsync(function() {
                    if (scale > 1 && frameIdx < data3d.dim[dicomPlane == 't' ? 2 : dicomPlane == 'c' ? 1 : 0] - 1) {
                        frameIdx += 1;
                        renderData();
                    }
                    else if (scale < 1 && frameIdx > 0) {
                        frameIdx -= 1;
                        renderData();
                    }
                    else {
                        resetZoom();
                    }
                    //console.log('frame:', frameIdx);
                });
            }

            function createData3d(data) {
                var res = {
                    pointData: data.get().pointData.get().arrays[0].data.getData(),
                    dim: data.getDimensions(),
                    bounds: data.getBounds(),
                    spacing: data.getSpacing(),
                };
                //TODO(pjm): this could be a flag based on patient position
                //srdbg('res bnds before', res.spacing, res.dim, res.bounds.slice());
                res.bounds[5] = res.bounds[4] - res.spacing[2] * (res.dim[2] - 1);
                //srdbg('res bnds after', res.bounds.slice());

                return res;
            }

            function domainForPlane(data3d) {
                //TODO(pjm): convert "if" into sub
                if (dicomPlane == 't') {
                    return [
                        [
                            data3d.bounds[0] - data3d.spacing[0] / 2,
                            data3d.bounds[2] - data3d.spacing[1] / 2,
                        ],
                        [
                            data3d.bounds[1] + data3d.spacing[0] / 2,
                            data3d.bounds[3] + data3d.spacing[1] / 2,
                        ],
                    ];
                }
                else if (dicomPlane == 'c') {
                    return [
                        [
                            data3d.bounds[0] - data3d.spacing[0] / 2,
                            data3d.bounds[4] - data3d.spacing[2] / 2,
                        ],
                        [
                            data3d.bounds[1] + data3d.spacing[0] / 2,
                            data3d.bounds[5] + data3d.spacing[2] / 2,
                        ],
                    ];
                }
                else if (dicomPlane == 's') {
                    return [
                        [
                            data3d.bounds[2] - data3d.spacing[1] / 2,
                            data3d.bounds[4] - data3d.spacing[2] / 2,
                        ],
                        [
                            data3d.bounds[3] + data3d.spacing[1] / 2,
                            data3d.bounds[5] + data3d.spacing[2] / 2,
                        ],
                    ];
                }
            }

            function getRange(values) {
                return [values[0], values[values.length - 1]];
            }

            function getSize(values) {
                return Math.abs(values[values.length - 1] - values[0]);
            }

            function loadData3d(event, reader, frame) {
                var data = createData3d(reader.getOutputData());
                if (frame == 1) {
                    iradService.downloadDataFile($scope.modelName, 2);
                    data3d = data;
                }
                else if (frame == 2) {
                    dose3d = data;
                    iradService.loadROIPoints();
                }
                renderData();
            }

            function prepareImage() {
                dicomFeature.prepareImage(appState.models.dicomWindow);
            }

            function refresh() {
                if (! xValues) {
                    return;
                }
                // if (rs4piService.isMouseWheelMode('zoom')) {
                //     plotting.trimDomain(xAxisScale, getRange(xValues));
                //     plotting.trimDomain(yAxisScale, getRange(yValues));
                // }
                // updateCursor();
                dicomFeature.draw(canvas, getRange(xValues), getRange(yValues));
                if (roiFeature) {
                    roiFeature.draw();
                }

                if (dose3d) {
                    var doseDomain = domainForPlane(dose3d);
                    doseFeature.draw(canvas, [doseDomain[0][0], doseDomain[1][0]], [doseDomain[0][1], doseDomain[1][1]]);
                }

                resetZoom();
            }

            function renderData() {
                var width = data3d.dim[0];
                var height = data3d.dim[1];
                var depth = data3d.dim[2];
                //TODO(pjm): metadata
                var rescaleIntercept = -1024.0;
                var rescaleSlope = 1;
                var pixels = sliceArray(data3d, rescaleIntercept, rescaleSlope);
                if (roiFeature) {
                    roiFeature.load(zFrame);
                }
                if (dose3d) {
                    //TODO(pjm): metadata
                    var doseScaling = 6.1609162e-5;
                    var dosePixels = sliceArray(dose3d, 0, doseScaling);
                    //var colorMap = plotting.colorMapFromModel($scope.modelName);
                    var colorMap = plotting.colorMapOrDefault('jet');
                    //TODO(pjm): metadata
                    var maxDose = 62.6127136398;
                    var colorScale = d3.scale.linear()
                        //TODO(pjm): add adjustable % cut-off
                        .domain(plotting.linearlySpacedArray(doseFeature.DOSE_CUTOFF, maxDose * 0.8, colorMap.length))
                        .range(colorMap)
                        .clamp(true);
                    //TODO(pjm): model data
                    var transparency = 56;
                    doseFeature.setColorScale(colorScale, transparency);
                    doseFeature.load(dosePixels);
                    doseFeature.prepareImage({}, true);
                }

                var preserveZoom = xValues ? true : false;
                dicomDomain = domainForPlane(data3d);
                xValues = plotting.linearlySpacedArray(dicomDomain[0][0], dicomDomain[1][0], width);
                yValues = plotting.linearlySpacedArray(dicomDomain[0][1], dicomDomain[1][1], height);
                if (! preserveZoom) {
                    xAxisScale.domain(getRange(xValues));
                    yAxisScale.domain(getRange(yValues));
                }
                dicomFeature.load(pixels);
                prepareImage();
                $scope.resize();
            }

            function resetZoom() {
                zoom = d3.behavior.zoom();
                select('.plot-viewport').call(zoom);
                // if (rs4piService.isMouseWheelMode('zoom')) {
                //     zoom.x(xAxisScale)
                //         .y(yAxisScale)
                //         .on('zoom', refresh);
                // }
                // else if (rs4piService.isMouseWheelMode('advanceFrame')) {
                   zoom.x(frameScale)
                       .on('zoom', advanceFrame);
                // }
            }

            function select(selector) {
                var e = d3.select($scope.element);
                return selector ? e.select(selector) : e;
            }
            $scope.select = select;

            function sliceArray(data, rescaleIntercept, rescaleSlope) {
                var voxels = data.pointData;
                var dim = data.dim;
                var res = [];
                var idx = frameIdx;

                //TODO(pjm): refactor the "if" into one sub
                var width, height, xmax, ymax, yi, xi;
                if (dicomPlane == 't') {
                    slicePosition = data3d.bounds[4] - idx * data3d.spacing[2];
                    if (data === dose3d) {
                        idx = Math.round((zFrame - data.bounds[4]) / -data.spacing[2]);
                    }
                    width = dim[0];
                    height = dim[1];
                    //TODO(pjm): don't need to nest arrays - it gets unwound for putImageData() above
                    for (yi = 0; yi < height; ++yi) {
                        res[yi] = [];
                        for (xi = 0; xi < width; ++xi) {
                            res[yi][xi] = voxels[idx * (width * height) + yi * width + xi] * rescaleSlope + rescaleIntercept;
                        }
                    }
                }
                else if (dicomPlane == 'c') {
                    slicePosition = data3d.bounds[2] + idx * data3d.spacing[1];
                    if (data === dose3d) {
                        idx = Math.round((slicePosition - data.bounds[2]) / data.spacing[1]);
                        if (idx < 0 || idx > dim[1]) {
                            return res;
                        }
                    }
                    width = dim[0];
                    height = dim[1];
                    xmax = dim[0];
                    ymax = dim[2];
                    for (yi = 0; yi < ymax; ++yi) {
                        res[yi] = [];
                        for (xi = 0; xi < xmax; ++xi) {
                            res[yi][xi] = voxels[yi * (width * height) + idx * width + xi] * rescaleSlope + rescaleIntercept;
                        }
                    }
                }
                else if (dicomPlane == 's') {
                    slicePosition = data3d.bounds[0] + idx * data3d.spacing[0];
                    if (data === dose3d) {
                        idx = Math.round((slicePosition - data.bounds[0]) / data.spacing[0]);
                        if (idx < 0 || idx > dim[0]) {
                            return res;
                        }
                    }
                    width = dim[0];
                    height = dim[1];
                    xmax = dim[1];
                    ymax = dim[2];
                    for (yi = 0; yi < ymax; ++yi) {
                        res[yi] = [];
                        for (xi = 0; xi < xmax; ++xi) {
                            res[yi][xi] = voxels[yi * (width * height)  + idx + width * xi] * rescaleSlope + rescaleIntercept;
                        }
                    }
                }
                zFrame = slicePosition.toFixed(1);
                iradService.setSlicePosition(dicomPlane, slicePosition);
                return res;
            }

            $scope.destroy = function() {
                zoom.on('zoom', null);
            };

            $scope.init = function() {
                select('svg').attr('height', plotting.initialHeight($scope));
                xAxisScale = d3.scale.linear();
                yAxisScale = d3.scale.linear();
                frameScale = d3.scale.linear();
                if (roiFeature) {
                    roiFeature.init(xAxisScale, yAxisScale);
                }
                resetZoom();
                canvas = select('canvas').node();
                dicomFeature.init(xAxisScale, yAxisScale);
                doseFeature.init(xAxisScale, yAxisScale);
            };

            $scope.resize = function() {
                if (select().empty()) {
                    return;
                }
                var canvasWidth = parseInt(select().style('width')) - $scope.margin.left - $scope.margin.right;
                if (isNaN(canvasWidth) || ! xValues) {
                    return;
                }
                $scope.canvasWidth = canvasWidth;
                $scope.canvasHeight = canvasWidth * getSize(yValues) / getSize(xValues);
                xAxisScale.range([0, canvasWidth]);
                yAxisScale.range([$scope.canvasHeight, 0]);
                canvas.width = $scope.canvasWidth;
                canvas.height = $scope.canvasHeight;
                refresh();
            };

            $scope.yMax = function() {
                return yValues[yValues.length - 1] + yValues[0];
            };

            $scope.$on('roiPointsLoaded', function() {
                //console.log('received points loaded');
                if (xValues) {
                    if (roiFeature) {
                        roiFeature.clear();
                    }
                    refresh();
                }
            });

            $scope.$on('irad-data-available', loadData3d);
        },
        link: function link(scope, element) {
            appState.whenModelsLoaded(scope, function() {
                plotting.linkPlot(scope, element);
            });
        },
    };
});

SIREPO.app.directive('dicomObjectSelector', function(appState, iradService) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<div data-ng-repeat="row in rows" style="padding: 0.5ex 0;">',
              '<div>',
                '<span data-ng-if="row.items && row.isExpanded" class="glyphicon glyphicon-collapse-up"></span>',
                ' <span data-ng-if="row.isSelected" class="glyphicon glyphicon-check"></span>',
                ' <span data-ng-if="! row.isSelected" class="glyphicon glyphicon-unchecked"></span>',
                ' {{ row.name }}',
              '</div>',
              '<div data-ng-repeat="item in row.items" style="padding: 0.3ex 0;">',
                '<div style="white-space: nowrap; overflow: hidden; padding-left: 18px;">',
                  ' <span data-ng-if="item.isSelected" class="glyphicon glyphicon-check"></span>',
                  ' <span data-ng-if="! item.isSelected" class="glyphicon glyphicon-unchecked"></span>',
                  ' <div class="irad-circle" data-ng-if="item.color" style="background-color: {{ itemColor(item) }}"> </div>',
                  ' {{ item.name }}',
                '</div>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.itemColor = function(item) {
                var c = item.color;
                return c && window.d3 ? d3.rgb(c[0], c[1], c[2]) : '#000';
            };
            $scope.rows = [
                {
                    name: 'CT PROSTATE',
                    isSelected: true,
                },
                {
                    name: 'RTDOSE',
                    isSelected: true,
                },
                {
                    name: 'RTSTRUCT',
                    isSelected: true,
                    isExpanded: true,
                },
                {
                    name: 'RTPLAN',
                    isSelected: false,
                    isExpanded: true,
                },
            ];
            $scope.$on('roiPointsLoaded', function() {
                var rois = iradService.getROIPoints();
                var items = [];
                Object.keys(rois).forEach(function(roiNumber) {
                    var roi = rois[roiNumber];
                    if (! roi.color) {
                        return;
                    }
                    items.push({
                        id: roiNumber,
                        name: roi.name,
                        //TODO(pjm): why index 0?
                        color: roi.color[0],
                        isSelected: true,
                    });
                });
                items.sort(function(a, b) {
                    return a.name.localeCompare(b.name);
                });
                $scope.rows[2].items = items;
                //TODO(pjm): dummy plan beams
                $scope.rows[3].items = [
                    {
                        name: 'Beam 1',
                        isSelected: false,
                    },
                    {
                        name: 'Beam 2',
                        isSelected: false,
                    },
                ];
            });
        },
    };
});

SIREPO.app.directive('toggleReportButton', function(appState) {
    return {
        restrict: 'A',
        scope: {
            selected: '@toggleReportButton',
        },
        template: [
            '<a href data-ng-click="toggleReport()">{{ label }}</a>',
        ].join(''),
        controller: function($scope) {
            $scope.label = appState.enumDescription('ReportToggle', $scope.selected);

            $scope.toggleReport = function() {
                if (appState.isLoaded()) {
                    appState.models.dvhReport.toggle = $scope.selected;
                }
            };
        },
    };
});
