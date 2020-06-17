'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;
SIREPO.appReportTypes = [
    '<div data-ng-switch-when="dicomPlot" data-dicom-plot="" class="sr-plot" data-model-name="{{ modelKey }}"></div>',
    '<div data-ng-switch-when="dicomComparePlot" data-dicom-plot="" data-is-compare-plot="1" class="sr-plot" data-model-name="{{ modelKey }}"></div>',
    '<div data-ng-switch-when="doseDifferencePlot" data-dicom-plot="" data-is-difference-plot="1" class="sr-plot" data-model-name="{{ modelKey }}"></div>',
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

SIREPO.app.factory('iradService', function(appState, panelState, requestSender, simulationQueue, utilities, $rootScope) {
    var self = {
        maxDose: 0,
    };
    var dicomReader, doseFrames, doseReader, dose2Reader, roiPoints;
    var doseComparisonTriggerPerPlane = {
        s: doseComparisonTrigger('s'),
        t: doseComparisonTrigger('t'),
        c: doseComparisonTrigger('c'),
    };

    self.downloadStatus = '';

    function downloadFiles(callback) {
        if (! appState.isLoaded()) {
            return;
        }
        self.downloadStatus = 'Loading DICOM';
        panelState.waitForUI(function() {
            downloadVTIDataFile(SIREPO.APP_SCHEMA.constants.dicomFrame, function() {
                self.downloadStatus = 'Loading Dose';
                panelState.waitForUI(function() {
                    downloadVTIDataFile(SIREPO.APP_SCHEMA.constants.doseFrame, function() {
                        panelState.waitForUI(function() {
                            downloadROIDataFile(callback);
                        });
                    });
                });
            });
        });
    }

    function downloadROIDataFile(callback) {
        if (! appState.isLoaded()) {
            return;
        }
        self.downloadStatus = 'Loading Regions of Interest';
        var simId = appState.models.simulation.simulationId;
        requestSender.sendRequest(
            urlForFrame(simId, SIREPO.APP_SCHEMA.constants.roiFrame),
            function(data) {
                if (isValidSimulation(simId)) {
                    self.downloadStatus = '';
                    roiPoints = data.regionOfInterest;
                    $rootScope.$broadcast('irad-roi-available');
                    if (callback) {
                        callback();
                    }
                }
            });
    }

    function doseComparisonTrigger(plane) {
        return utilities.debounce(
            function(doseFrames) {
                $rootScope.$broadcast('irad-compute-dose-comparison', plane, doseFrames);
            }, 100);
    }

    function downloadVTIDataFile(frame, callback) {
        var simId = appState.models.simulation.simulationId;
        var reader = vtk.IO.Core.vtkHttpDataSetReader.newInstance();
        reader.setUrl(urlForFrame(simId, frame), {
            compression: 'zip',
            fullpath: true,
            loadData: true,
        }).then(function() {
            if (isValidSimulation(simId)) {
                if (frame == SIREPO.APP_SCHEMA.constants.dicomFrame) {
                    dicomReader = reader;
                }
                else if (frame == SIREPO.APP_SCHEMA.constants.doseFrame) {
                    doseReader = reader;
                }
                else if (frame == SIREPO.APP_SCHEMA.constants.dose2Frame) {
                    dose2Reader = reader;
                }
                $rootScope.$broadcast('irad-vti-available', frame);
                callback();
            }
        });
    }

    function isValidSimulation(simulationId) {
        return appState.isLoaded() && simulationId == appState.models.simulation.simulationId;
    }

    function urlForFrame(simulationId, frame) {
        return requestSender.formatUrl(
            'downloadDataFile',
            {
                '<simulation_id>': simulationId,
                '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                '<model>': 'dicom3DReport',
                '<frame>': frame,
            });
    }

    self.getActiveROI = function() {
        if (! appState.isLoaded()) {
            return null;
        }
        return appState.models.dicomSettings.activeRoiNumber;
    };

    self.getDicomReader = function() {
        return dicomReader;
    };

    self.getDoseReader = function() {
        return doseReader;
    };

    self.getDose2Reader = function() {
        return dose2Reader;
    };

    self.getROIPoints = function() {
        return roiPoints;
    };

    self.loadDataFiles = function(callback) {
        if (roiPoints) {
            if (callback) {
                callback();
            }
            return;
        }
        self.downloadStatus = 'Initializing Data Files';
        simulationQueue.addTransientItem(
            'dicom3DReport',
            appState.applicationState(),
            function() {
                downloadFiles(callback);
            });
    };

    self.loadDose2File = function() {
        if (dose2Reader) {
            return;
        }
        self.downloadStatus = 'Loading Dose 2';
        panelState.waitForUI(function() {
            downloadVTIDataFile(SIREPO.APP_SCHEMA.constants.dose2Frame, function() {
                self.downloadStatus = '';
                $rootScope.$digest();
            });
        });
    };

    self.setActiveROI = function(roiNumber) {
        appState.models.dicomSettings.activeRoiNumber = roiNumber;
        appState.saveQuietly('dicomSettings');
        $rootScope.$broadcast('irad-roi-activated', roiNumber);
    };

    self.setDosePixels = function(dicomPlane, isCompareDose, zFrame, dosePixels, doseDomain) {
        if (! doseFrames) {
            doseFrames = {};
        }
        if (! doseFrames[dicomPlane]) {
            doseFrames[dicomPlane] = [];
        }
        doseFrames[dicomPlane][isCompareDose ? 1 : 0] = [zFrame, dosePixels, doseDomain];
        if (doseFrames[dicomPlane].length == 2 && doseFrames[dicomPlane][0][0] == doseFrames[dicomPlane][1][0]) {
            doseComparisonTriggerPerPlane[dicomPlane](doseFrames[dicomPlane]);
        }
    };

    $rootScope.$on('modelsUnloaded', function() {
        dicomReader = doseFrames = doseReader = dose2Reader = roiPoints = null;
        self.maxDose = 0;
        self.downloadStatus = '';
    });

    appState.setAppService(self);
    return self;
});

SIREPO.app.controller('DoseController', function (appState, iradService, $scope) {
    var self = this;
    self.iradService = iradService;

    function reportForId(id) {
        if (appState.isLoaded()) {
            return appState.models.dicomReports[id - 1];
        }
        return null;
    }

    appState.whenModelsLoaded($scope, function() {
        self.dicomReports = [];
        appState.models.dicomReports.forEach(function(report) {
            self.dicomReports.push({
                modelKey: 'dicomReport' + report.id,
                getData: function() {
                    return reportForId(report.id);
                },
                title: function(name) {
                    var model = reportForId(report.id);
                    return (name || appState.enumDescription('DicomPlane', model.dicomPlane))
                        + (isNaN(model.slicePosition)
                           ? ''
                           : (' ' + model.slicePosition.toFixed(3) + 'mm'));
                },
            });
        });
        iradService.loadDataFiles(iradService.loadDose2File);
    });
});

SIREPO.app.controller('SourceController', function (appState, iradService, $scope) {
    var self = this;
    self.iradService = iradService;
    var doseListener;

    self.showReport = function(toggle) {
        if (! appState.isLoaded()) {
            if (toggle == '3d') {
                return true;
            }
            return false;
        }
        return appState.models.dicomSettings.toggle3D == toggle;
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

    function reportForId(id) {
        if (appState.isLoaded()) {
            return appState.models.dicomReports[id - 1];
        }
        return null;
    }

    appState.whenModelsLoaded($scope, function() {
        self.dicomReports = [];
        appState.models.dicomReports.forEach(function(report) {
            self.dicomReports.push({
                modelKey: 'dicomReport' + report.id,
                getData: function() {
                    return reportForId(report.id);
                },
                title: function() {
                    var model = reportForId(report.id);
                    return appState.enumDescription('DicomPlane', model.dicomPlane)
                        + (isNaN(model.slicePosition)
                           ? ''
                           : (' ' + model.slicePosition.toFixed(3) + 'mm'));
                },
            });
        });
        iradService.loadDataFiles();
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
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-user"></span> DICOM Viewer</a></li>',
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'dose\')}"><a href data-ng-click="nav.openSection(\'dose\')"><span class="glyphicon glyphicon-picture"></span> Dose Comparison</a></li>',
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

SIREPO.app.directive('dicomOrientationMarker', function(geometry, vtkPlotting) {
    return {
        restrict: 'A',
        scope: {},
        controller: function($scope) {
            var marker;
            function init(event, fsRenderer) {
                var coordMapper = vtkPlotting.coordMapper(
                    // the coordinate system may depend on the data?
                    geometry.transform([
                        [1, 0, 0],
                        [0, -1, 0],
                        [0, 0, 1]
                    ])
                );
                var actor = coordMapper.buildFromSource(homunculus()).actor;
                actor.setUserMatrix(coordMapper.userMatrix());
                marker = vtk.Interaction.Widgets.vtkOrientationMarkerWidget.newInstance({
                    actor: actor,
                    interactor: fsRenderer.getRenderWindow().getInteractor(),
                    viewportCorner: vtk.Interaction.Widgets.vtkOrientationMarkerWidget.Corners.TOP_RIGHT,
                    viewportSize: 0.15,
                });
                marker.setEnabled(true);
            }

            function refresh() {
                marker.updateMarkerOrientation();
            }

            function homunculus() {
                var thetaRez = 24;
                var phiRez = 24;
                var bodyRadius = 1.0;
                var bodyHeight = 3 * bodyRadius;
                var bodyCenter = [0, 0, 0];
                var headRadius = 0.70 * bodyRadius;
                var headCenter = [bodyCenter[0], bodyCenter[1], bodyCenter[2] + bodyHeight / 2.0 + 0.9 * headRadius];
                // plane names
                var DEXTER = 'dexter';
                var DORSAL = 'dorsal';
                var SINISTER = 'sinister';
                var VENTRAL = 'ventral';

                // color and head theta
                var quadrants = {};
                quadrants[VENTRAL + SINISTER] = [[255, 0, 0, 255], {th1: 90, th2: 180}];
                quadrants[VENTRAL + DEXTER] = [[44, 160, 44, 255], {th1: 0, th2: 90}];
                quadrants[DORSAL + SINISTER] = [[255, 255, 0, 255], {th1: 180, th2: 270}];
                quadrants[DORSAL + DEXTER] = [[0, 0, 255, 255], {th1: 270, th2: 360}];

                var planes = {};
                planes[VENTRAL] = {norm: [0, 1, 0], origin: bodyCenter};
                planes[DORSAL] = {norm: [0, -1, 0], origin: bodyCenter};
                planes[DEXTER] = {norm: [1, 0, 0], origin: bodyCenter};
                planes[SINISTER] = {norm: [-1, 0, 0], origin: bodyCenter};

                var source = vtk.Filters.General.vtkAppendPolyData.newInstance();
                [VENTRAL, DORSAL].forEach(function (vd) {
                    [SINISTER, DEXTER].forEach(function (sd) {
                        var qc = quadrants[vd + sd][0];
                        var s = vtkPlotting.cylinderSection(
                            bodyCenter, [0, 0 , 1], bodyRadius, bodyHeight,
                            [
                                {norm: [0, 0, -1], origin: [0, 0, bodyHeight / 2.0]},
                                {norm: [0, 0, 1], origin: [0, 0, -bodyHeight / 2.0]},
                                planes[vd],
                                planes[sd],
                            ]
                        ).getOutputData();
                        vtkPlotting.setColorScalars(s, qc);
                        if (source.getInputData()) {
                            source.addInputData(s);
                        }
                        else {
                            source.setInputData(s);
                        }
                        var hq = quadrants[vd + sd][1];
                        s = vtk.Filters.Sources.vtkSphereSource.newInstance({
                            radius: headRadius,
                            center: headCenter,
                            thetaResolution: 24,
                            phiResolution: 24,
                            startTheta: hq.th1,
                            endTheta: hq.th2
                        }).getOutputData();
                        vtkPlotting.setColorScalars(s, qc);
                        source.addInputData(s);
                    });
                });

                var noseRadius = 0.33 * headRadius;
                var s = vtk.Filters.Sources.vtkSphereSource.newInstance({
                    radius: noseRadius,
                    center: [headCenter[0], bodyCenter[1] + headRadius + 0.66 * noseRadius, headCenter[2]],
                    thetaResolution: thetaRez,
                    phiResolution: phiRez,
                }).getOutputData();
                vtkPlotting.setColorScalars(s, [255, 255, 255, 255]);
                source.addInputData(s);
                return source;
            }

            $scope.$on('sr-dicom-init', init);
            $scope.$on('sr-dicom3d-refresh', refresh);
        },
    };
});

SIREPO.app.directive('dicom3d', function(appState, geometry, iradService, plotting, utilities, vtkToPNG) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
            reportId: '<',
        },
        template: [
            '<div data-ng-if="! is3dViewActivated">',
              '<div style="background: black; color: white; margin-bottom: 0; padding-top: 48%; padding-bottom: 48%">',
                '<div style="cursor: pointer" class="lead text-center"  data-ng-click="activate3dView()" data-ng-if="iradService.getROIPoints()">Click to view 3D model</div>',
              '</div>',
            '</div>',
            '<div data-ng-if="is3dViewActivated">',
              '<div data-dicom-orientation-marker=""></div>',
              '<div class="sr-dicom3d-content" style="max-width: 100vh; max-height: 100vh"></div>',
              // force the Download Report menu to appear
              '<svg style="display: none"></svg>',
            '</div>',
        ].join(''),
        controller: function($scope, $element) {
            $scope.iradService = iradService;
            var fsRenderer, pngCanvas;
            var actor = null;
            var roiActors = [];
            //TODO(pjm): set the variables below when selecting from Components panel
            var showRTDose = false;
            $scope.isClientOnly = true;
            $scope.is3dViewActivated = false;
            var dicomSpacing;
            var VOLUME_SHADING = {
                beige: {
                    gradientOpacity: [99, 0, 100, 1],
                    specularPower: 8,
                    scalarOpacity: [-824, 0, 176, 0.5, 1976, 0.8],
                    specular: 0.3,
                    shade: false,
                    ambient: 0.2,
                    colorTransfer: [-824, 0.4, 0.2, 0, 976, 1, 1, 1],
                    diffuse: 0.7,
                    interpolate: 1,
                    //opacityUnitDistance: 4.5,
                    opacityUnitDistance: 10,
                },
                ctCardiac3: {
                    gradientOpacity: [0, 1, 255, 1],
                    specularPower: 10,
                    scalarOpacity: [-3024, 0, -86.9767, 0, 45.3791, 0.169643, 139.919, 0.589286, 347.907, 0.607143, 1224.16, 0.607143, 3071, 0.616071],
                    specular: 0.2,
                    shade: true,
                    ambient: 0.1,
                    colorTransfer: [-3024, 0, 0, 0, -86.9767, 0, 0.25098, 1, 45.3791, 1, 0, 0, 139.919, 1, 0.894893, 0.894893, 347.907, 1, 1, 0.25098, 1224.16, 1, 1, 1, 3071, 0.827451, 0.658824, 1],
                    diffuse: 0.9,
                    interpolate: 1,
                    opacityUnitDistance: 1,
                },
                ct: {
                    shade: true,
                    interpolate: 1,
                    ambient: 0.1,
                    diffuse: 0.9,
                    specular: 0.2,
                    specularPower: 10,
                    gradientOpacity: [0, 0, 2000, 1],
                    scalarOpacity: [-800, 0, -750, 1, -350, 1, -300, 0, -200, 0, -100, 1, 10000, 0, 2570, 0, 2976, 1, 3000, 0],
                    colorTransfer: [-750, 0.08, 0.05, 0.03, -350, 0.39, 0.25, 0.16, -200, 0.8, 0.8, 0.8, 2750, 0.7, 0.7, 0.7, 3000, 0.35, 0.35, 0.35],
                    opacityUnitDistance: 1,
                },
            };

            function refresh(event, frame) {
                var reader;
                if (frame == SIREPO.APP_SCHEMA.constants.dicomFrame) {
                    reader = iradService.getDicomReader();
                    dicomSpacing = reader.getOutputData().getSpacing();
                }
                // else if (frame == SIREPO.APP_SCHEMA.constants.doseFrame) {
                //     reader = iradService.getDoseReader();
                //     if (! showRTDose) {
                //         return;
                //     }
                // }
                else {
                    return;
                }
                actor = vtk.Rendering.Core.vtkVolume.newInstance();
                var mapper = vtk.Rendering.Core.vtkVolumeMapper.newInstance();
                actor.setMapper(mapper);
                var renderer = fsRenderer.getRenderer();
                mapper.setInputConnection(reader.getOutputPort());
                var metadata = reader.getOutputData().get().metadata;

                var ofun, ctfun;
                if (frame == SIREPO.APP_SCHEMA.constants.dicomFrame) {
                    //mapper.setSampleDistance(0.7);
                    setVolumeProperties(reader, actor, VOLUME_SHADING.beige);

                    /* cropping widget - crashes if pngCanvas is used
                    var widgetManager = vtk.Widgets.Core.vtkWidgetManager.newInstance();
                    widgetManager.setRenderer(renderer);
                    var widget = vtk.Widgets.Widgets3D.vtkImageCroppingWidget.newInstance();
                    widget.set({
                        faceHandlesEnabled: false,
                        //cornerHandlesEnabled: false,
                        edgeHandlesEnabled: false,
                    });
                    widgetManager.addWidget(widget);
                    var cropFilter = vtk.Filters.General.vtkImageCropFilter.newInstance();
                    cropFilter.setInputConnection(reader.getOutputPort());
                    mapper.setInputConnection(cropFilter.getOutputPort());
                    var image = reader.getOutputData();
                    var extent = image.getExtent();
                    cropFilter.setCroppingPlanes(extent[0], extent[1], extent[2], extent[3], extent[4], extent[5]);
                    widget.copyImageDataDescription(image);
                    var cropState = widget.getWidgetState().getCroppingPlanes();
                    cropState.onModified(function() {
                        cropFilter.setCroppingPlanes(cropState.getPlanes());
                    });
                    */

                    renderer.addVolume(actor);
                    renderer.resetCamera();
                    renderer.resetCameraClippingRange();

                    var cam =  renderer.getActiveCamera();
                    cam.zoom(1.5);
                    //TODO(pjm): set camera position instead?
                    cam.elevation(-100);
                    cam.roll(180);
                    renderer.updateLightsGeometryToFollowCamera();
                }
                else {
                    var dmin = 4 / metadata.DoseGridScaling;
                    var dmax = metadata.DoseMax;
                    ofun = vtk.Common.DataModel.vtkPiecewiseFunction.newInstance();
                    ofun.addPoint(0, 0);
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
                $scope.$broadcast('sr-dicom3d-refresh');
                fsRenderer.getRenderWindow().render();
                pngCanvas.copyCanvas();
            }

            function setVolumeProperties(reader, actor, prop) {
                var metadata = reader.getOutputData().get().metadata;
                var i;
                var p = actor.getProperty();
                var ctfun = vtk.Rendering.Core.vtkColorTransferFunction.newInstance();
                for (i = 0; i < prop.colorTransfer.length; i += 4) {
                    ctfun.addRGBPoint(
                        prop.colorTransfer[i] / metadata.RescaleSlope - metadata.RescaleIntercept,
                        prop.colorTransfer[i + 1],
                        prop.colorTransfer[i + 2], prop.colorTransfer[i + 3]);
                }
                p.setRGBTransferFunction(0, ctfun);
                var ofun = vtk.Common.DataModel.vtkPiecewiseFunction.newInstance();
                for (i = 0; i < prop.scalarOpacity.length; i += 2) {
                    ofun.addPoint(
                        prop.scalarOpacity[i] / metadata.RescaleSlope - metadata.RescaleIntercept,
                        prop.scalarOpacity[i + 1]);
                }
                p.setScalarOpacity(0, ofun);
                p.setScalarOpacityUnitDistance(0, prop.opacityUnitDistance);
                if (prop.interpolate == 1) {
                    p.setInterpolationTypeToLinear();
                }
                //TODO(pjm): configure this off if all 100?
                p.setUseGradientOpacity(0, true);
                p.setGradientOpacityMinimumValue(0, prop.gradientOpacity[0]);
                p.setGradientOpacityMinimumOpacity(0, prop.gradientOpacity[1]);
                p.setGradientOpacityMaximumValue(0, prop.gradientOpacity[2]);
                p.setGradientOpacityMaximumOpacity(0, prop.gradientOpacity[3]);
                p.setShade(prop.shade);
                p.setAmbient(prop.ambient);
                p.setDiffuse(prop.diffuse);
                p.setSpecular(prop.specular);
                p.setSpecularPower(prop.specularPower);
            }

            function showActiveRoi() {
                roiActors.forEach(fsRenderer.getRenderer().removeActor);
                roiActors = [];
                var activeROI = iradService.getActiveROI();
                var roi = activeROI ? iradService.getROIPoints()[activeROI] : null;
                if (! roi) {
                    fsRenderer.getRenderWindow().render();
                    pngCanvas.copyCanvas();
                    return;
                }
                var i, j, segment;
                var bnds = [
                    Number.MAX_VALUE, -Number.MAX_VALUE,
                    Number.MAX_VALUE, -Number.MAX_VALUE,
                    Number.MAX_VALUE, -Number.MAX_VALUE,
                ];

                function getCoord(pts, cIdx) {
                    return pts.filter(function (p, pIdx) {
                        return pIdx % 2 === cIdx;
                    });
                }

                var nGrid = [0, 0, 0];
                var maxSegs = 0;
                for (var z in roi.contour) {
                    ++nGrid[2];
                    bnds[4] = Math.min(bnds[4], parseFloat(z));
                    bnds[5] = Math.max(bnds[5], parseFloat(z));
                    var nSegs = roi.contour[z].length;
                    maxSegs = Math.max(maxSegs, nSegs);
                    for (segment = 0; segment < nSegs; segment++) {
                        var points = roi.contour[z][segment];
                        for (i = 0; i < 2; ++i) {
                            var c = getCoord(points, i);
                            nGrid[i] = Math.max(nGrid[i], c.length);
                            bnds[2 * i] = Math.min(bnds[2 * i], Math.min.apply(null, c));
                            bnds[2 * i + 1] = Math.max(bnds[2 * i + 1], Math.max.apply(null, c));
                        }
                    }
                }
                //console.log('maxSegs:', maxSegs);

                // don't go beyond maximal grid (yet?)
                //var maxGrid = 128;
                var maxGrid = 40;
                nGrid = [
                    Math.min(maxGrid, nGrid[0]),
                    Math.min(maxGrid, nGrid[1]),
                    Math.min(maxGrid, nGrid[2])
                ];


                var segBnds = Array(maxSegs);
                for (i = 0; i < maxSegs; ++i) {
                    segBnds[i] = [];
                    for (j = 0; j < 6; ++j) {
                        segBnds[i].push((1 - 2 * (j % 2)) * Number.MAX_VALUE);
                    }
                }

                var zPlanes = Object.keys(roi.contour)
                    .sort(function (zp1, zp2) {
                        return parseFloat(zp1) - parseFloat(zp2);
                    });
                var polys = {};
                zPlanes.forEach(function (zp, zpIdx) {
                    var z = parseFloat(zp);
                    var revz = z;
                    var nSegs = roi.contour[zp].length;
                    var zPolys = Array(nSegs);
                    for (segment = 0; segment < nSegs; segment++) {
                        segBnds[segment][4] = Math.min(segBnds[segment][4], z);
                        segBnds[segment][5] = Math.max(segBnds[segment][5], z);
                        var cPoints = roi.contour[zp][segment];
                        var segPolyPts = Array(cPoints.length / 2);
                        for (i = 0; i < cPoints.length; i += 2) {
                            segPolyPts[i / 2] = [cPoints[i], cPoints[i + 1], z];
                            for (j = 0; j < 2; ++j) {
                                segBnds[segment][2 * j] = Math.min(segBnds[segment][2 * j], cPoints[i + j]);
                                segBnds[segment][2 * j + 1] = Math.max(segBnds[segment][2 * j + 1], cPoints[i + j]);
                            }
                        }
                        if (segPolyPts.length >= 3) {
                            // ignore 1 point polygons
                            zPolys[segment] = geometry.polygon(segPolyPts);
                        }
                    }
                    // reverse the z plane associated with this polygon, and shift fot later lookup
                    polys['' + z] = zPolys;
                    //console.log('poly:', '' + z);
                });
                var gridSpc = [
                    Math.abs((bnds[1] - bnds[0])) / (nGrid[0] - 1),
                    Math.abs((bnds[3] - bnds[2])) / (nGrid[1] - 1),
                    Math.abs((bnds[5] - bnds[4])) / (nGrid[2] - 1),
                ];

                var segGrid = Array(maxSegs);
                var segCtr = Array(maxSegs);
                // reduce the space for marching cubes to the bounds of each segment
                for (i = 0; i < maxSegs; ++i) {
                    var b = segBnds[i];
                    segGrid[i] = Array(3);
                    segCtr[i] = Array(3);
                    for (j = 0; j < 3; ++j) {
                        // add a grid spacing on each side to close off the volume
                        b[2 * j] -= gridSpc[j];  b[2 * j + 1] += gridSpc[j];
                        // must be at least 2 grid points in each direction
                        segGrid[i][j] = Math.max(
                            2,
                            Math.floor(Math.abs((b[2 * j + 1] - b[2 * j])) / gridSpc[j])
                        );
                        segCtr[i][j] = (b[2 * j] + b[2 * j + 1]) / 2.0;
                    }
                }
                var ctr = [
                    (bnds[0] + bnds[1]) / 2.0,
                    (bnds[2] + bnds[3]) / 2.0,
                    (bnds[4] + bnds[5]) / 2.0,
                ];
                var dz = parseFloat(zPlanes[1]) - parseFloat(zPlanes[0]);
                // used by the vtk sample function to decide which points in the volume are in or out
                function segmentImpl(seg) {
                    return {
                        evaluateFunction: function (coords) {
                            var d = Math.hypot(ctr[0] - coords[0], ctr[1] - coords[1], ctr[2] - coords[2]);
                            // closest zplane
                            var zpIdx = Math.floor((coords[2] - bnds[4]) / dz);
                            var zp = '' + parseFloat(zPlanes[zpIdx]);
                            if (! polys[zp] || ! polys[zp][seg]) {
                                //console.log('missed zplane:', zpIdx, zp, polys[zp], -d);
                                return -d;
                                //return -1;
                            }
                            return polys[zp][seg].containsPoint(coords) ? d : -d;
                        },
                    };
                }

                var aColor = roi.color[0].map(function (c) {
                    return c / 255.0;
                });
                for (i = 0; i < maxSegs; ++i) {
                    var s = vtk.Imaging.Hybrid.vtkSampleFunction.newInstance({
                        implicitFunction: segmentImpl(i),
                        modelBounds: segBnds[i],
                        sampleDimensions: segGrid[i]
                    });
                    var cubes = vtk.Filters.General.vtkImageMarchingCubes.newInstance({ contourValue: 0.0 });
                    cubes.setInputConnection(s.getOutputPort());
                    var m = vtk.Rendering.Core.vtkMapper.newInstance();
                    m.setInputConnection(cubes.getOutputPort());
                    var a = vtk.Rendering.Core.vtkActor.newInstance({
                        mapper: m,
                    });
                    a.getProperty().setColor(aColor[0], aColor[1], aColor[2]);
                    // if (maxSegs > 1 && i === 0) {
                    //     a.getProperty().setOpacity(0.6);
                    // }
                    roiActors.push(a);
                    fsRenderer.getRenderer().addActor(a);
                }
                //var startTime = new Date().getTime();
                fsRenderer.getRenderWindow().render();
                pngCanvas.copyCanvas();
                //console.log('elapsed render seconds:', (new Date().getTime() - startTime) / 1000);
            }

            $scope.activate3dView = function() {
                if (! iradService.getROIPoints()) {
                    return;
                }
                $scope.is3dViewActivated = true;
                appState.whenModelsLoaded($scope, function() {
                    plotting.linkPlot($scope, $element);
                    $scope.initData();
                });
            };

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
                    background: [0, 0, 0],
                    container: $('.sr-dicom3d-content')[0],
                });
                pngCanvas = vtkToPNG.pngCanvas($scope.reportId, fsRenderer, $('.sr-dicom3d-content'));
                $scope.$broadcast('sr-dicom-init', fsRenderer);
            };

            $scope.initData = function() {
                if (iradService.getROIPoints()) {
                    refresh(null, SIREPO.APP_SCHEMA.constants.dicomFrame);
                    refresh(null, SIREPO.APP_SCHEMA.constants.doseFrame);
                    showActiveRoi();
                }
                else {
                    $scope.$on('irad-roi-available', showActiveRoi);
                    $scope.$on('irad-vti-available', refresh);
                }
                $scope.$on('irad-roi-activated', showActiveRoi);
            };

            $scope.resize = function() {
                if (! utilities.isFullscreen()) {
                    // ensure the canvas size is reset when returning from full screen
                    var container = fsRenderer.getContainer();
                    var canvas = $(container).find('canvas')[0];
                    if (canvas.height != canvas.width) {
                        canvas.height = canvas.width;
                        fsRenderer.resize();
                    }
                }
            };
        },
    };
});

function dicomROIFeature($scope, appState, iradService) {
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
            if (appState.models.dicomSettings.selectedROIs[roiNumber] != '1') {
                return;
            }
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
                        .datum(points)
                        .on('click', roiClick),
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
        var activeROI = iradService.getActiveROI();
        Object.keys(roiContours).forEach(function(roiNumber) {
            var v = roiContours[roiNumber];
            v.roiPath.attr('d', roiLine)
                .classed('dicom-roi-selected', roiNumber == activeROI)
                .attr('style', roiStyle(v.roi, roiNumber));
            v.dragPath.attr('d', roiLine)
                .classed('dicom-dragpath-select', true)
                .classed('selectable-path', true);
        });
    }

    function roiClick() {
        /*jshint validthis: true*/
        if (d3.event.defaultPrevented) {
            return;
        }
        d3.event.preventDefault();
        setActiveROIFromNode(this);
    }

    function roiStyle(roi, roiNumber) {
        var color = roi.color;
        return 'stroke: rgb(' + color.join(',') + ')';
    }

    function setActiveROI(roiNumber) {
        if (roiNumber == iradService.getActiveROI()) {
            roiNumber = null;
        }
        $scope.$applyAsync(function() {
            iradService.setActiveROI(roiNumber);
            redrawContours();
        });
    }

    function setActiveROIFromNode(node) {
        var roiNumbers = Object.keys(roiContours);
        for (var i = 0; i < roiNumbers.length; i++) {
            if (roiContours[roiNumbers[i]].dragPath.node() === node) {
                setActiveROI(roiNumbers[i]);
                return;
            }
        }
        throw new Error('invalid dragPath');
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

function imageFeature(isOverlay) {
    var cacheCanvas, colorScale, heatmap, imageData, transparency, xAxisScale, yAxisScale;

    function initColormap() {
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

    //TODO(pjm): should be controlled by UI
    //var DOSE_CUTOFF = 10;
    var DOSE_CUTOFF = 3;

    return {
        DOSE_CUTOFF: DOSE_CUTOFF,
        draw: function(canvas, xDomain, yDomain) {
            if (! isValidHeatmap()) {
                return;
            }
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
                -(yDomain[1] - yZoomDomain[1]) / zoomHeight * canvas.height,
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
        prepareImage: function(showCT) {
            if (! isValidHeatmap()) {
                return;
            }
            if (! isOverlay) {
                initColormap();
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
                        if (v < DOSE_CUTOFF) {
                            imageData.data[p] = 0;
                        }
                    }
                    else {
                        if (! showCT) {
                            c = 0;
                        }
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

SIREPO.app.directive('dicomPlot', function(appState, panelState, plotting, iradService, $interval, $rootScope, $window) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
            modelData: '=',
            isComparePlot: '@',
            isDifferencePlot: '@',
        },
        template: [
          '<div style="position: relative; background: black" ng-class="{\'sr-plot-loading\': isLoading(), \'sr-plot-cleared\': dataCleared}">',
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
          '<input class="irad-dicom-slider" data-ng-model="model.frameIdx" selected data-ng-change="rangeChanged()" type="range" min="0" max="{{ maxFrame }}" step="1" />',
        ].join(''),
        controller: function($scope) {
            $scope.canvasHeight = 0;
            $scope.canvasWidth = 0;
            $scope.margin = {top: 0, left: 0, right: 0, bottom: 0};

            var canvas, dicomDomain, xAxisScale, xValues, yAxisScale, yValues, zoom;
            var slicePosition, roiFeature, zFrame;
            var data3d, dose3d, frameScale;
            var xdomain, ydomain;
            var doseFeature = imageFeature(true);
            var dicomFeature = imageFeature();
            var boundsIndexForDomain = {
                t: [0, 2, 0, 1],
                c: [0, 4, 0, 2],
                s: [2, 4, 1, 2],
            };
            $scope.isClientOnly = true;
            $scope.maxFrame = Number.MAX_VALUE;

            $scope.rangeChanged = function() {
                if (data3d) {
                    appState.saveQuietly('dicomReports');
                }
            };

            function computeDoseComparison(event, dicomPlane, doseFrame) {
                if (dicomPlane != $scope.model.dicomPlane || ! $scope.isDifferencePlot) {
                    return;
                }
                var dose1Pixels = doseFrame[0][1];
                var dose1Domain = doseFrame[0][2];
                var dose2Pixels = doseFrame[1][1];
                var dose2Domain = doseFrame[1][2];
                if (! (dose1Pixels && dose2Pixels)) {
                    return;
                }
                if (! dose2Pixels.length) {
                    xdomain = null;
                    refresh();
                    return;
                }
                xdomain = [
                    Math.min(dose1Domain[0][0], dose2Domain[0][0]),
                    Math.max(dose1Domain[1][0], dose2Domain[1][0]),
                ];
                ydomain = [
                    Math.min(dose1Domain[0][1], dose2Domain[0][1]),
                    Math.max(dose1Domain[1][1], dose2Domain[1][1]),
                ];
                var x1Step = (dose1Domain[1][0] - dose1Domain[0][0]) / dose1Pixels[0].length;
                var x2Step = (dose2Domain[1][0] - dose2Domain[0][0]) / dose2Pixels[0].length;
                var xStep = Math.min(x1Step, x2Step);
                var y1Step = (dose1Domain[1][1] - dose1Domain[0][1]) / dose1Pixels.length;
                var y2Step = (dose2Domain[1][1] - dose2Domain[0][1]) / dose2Pixels.length;
                var yStep = Math.min(y1Step, y2Step);

                var dosePixels = [];
                var maxDose = 0;
                var yIdx = 0;
                var offset = 0;
                if (dicomPlane == 'c' || dicomPlane == 's') {
                    //TODO(pjm): another odd offset adjustment
                    offset = Math.round(((ydomain[1] - dose2Domain[1][1]) - (dose2Domain[0][1] - ydomain[0])) / y2Step);
                }
                for (var y = ydomain[0]; y < ydomain[1]; y = ydomain[0] + yIdx * yStep) {
                    var row = [];
                    dosePixels.push(row);
                    var yIdx1 = Math.round((y - dose1Domain[0][1]) / y1Step);
                    var yIdx2 = Math.round((y - dose2Domain[0][1]) / y2Step);
                    yIdx2 -= offset;
                    var xIdx = 0;
                    for (var x = xdomain[0]; x < xdomain[1]; x = xdomain[0] + xIdx * xStep) {
                        var v1 = 0;
                        var v2 = 0;
                        //TODO(pjm): combine into a shared function for x/y
                        if (yIdx1 < 0 || yIdx1 >= dose1Pixels.length) {
                        }
                        else {
                            var xIdx1 = Math.round((x - dose1Domain[0][0]) / x1Step);
                            if (xIdx1 < 0 || xIdx1 > dose1Pixels[0].length) {
                            }
                            else {
                                v1 = dose1Pixels[yIdx1][xIdx1];
                            }
                        }
                        if (yIdx2 < 0 || yIdx2 >= dose2Pixels.length) {
                        }
                        else {
                            var xIdx2 = Math.round((x - dose2Domain[0][0]) / x2Step);
                            if (xIdx2 < 0 || xIdx2 > dose2Pixels[0].length) {
                            }
                            else {
                                v2 = dose2Pixels[yIdx2][xIdx2];
                            }
                        }
                        var diff = Math.abs(v2 - v1);
                        row.push(diff);
                        if (diff > maxDose) {
                            maxDose = diff;
                        }
                        xIdx++;
                    }
                    yIdx++;
                }
                renderDose(dosePixels, maxDose);
                refresh();
            }

            function createData3d(data) {
                return {
                    pointData: data.get().pointData.get().arrays[0].data.getData(),
                    dim: data.getDimensions(),
                    bounds: data.getBounds(),
                    spacing: data.getSpacing(),
                    metadata: data.get().metadata,
                };
            }

            function domainForPlane(data3d) {
                var i = boundsIndexForDomain[$scope.model.dicomPlane];
                var halfSpacing = [
                    data3d.spacing[i[2]] / 2,
                    data3d.spacing[i[3]] / 2,
                ];
                return [
                    [
                        data3d.bounds[i[0]] - halfSpacing[0],
                        data3d.bounds[i[1]] - halfSpacing[1],
                    ],
                    [
                        data3d.bounds[i[0] + 1] + halfSpacing[0],
                        data3d.bounds[i[1] + 1] + halfSpacing[1],
                    ],
                ];
            }

            function getRange(values) {
                return [values[0], values[values.length - 1]];
            }

            function getSize(values) {
                return Math.abs(values[values.length - 1] - values[0]);
            }

            function loadData3d(event, frame) {
                if (frame == SIREPO.APP_SCHEMA.constants.dicomFrame) {
                    data3d = createData3d(iradService.getDicomReader().getOutputData());
                    $scope.maxFrame = data3d.dim[$scope.model.dicomPlane == 't' ? 2 : $scope.model.dicomPlane == 'c' ? 1 : 0];
                }
                else if (frame == SIREPO.APP_SCHEMA.constants.doseFrame) {
                    if ($scope.isComparePlot || $scope.isDifferencePlot) {
                        return;
                    }
                    dose3d = createData3d(iradService.getDoseReader().getOutputData());
                }
                else if (frame == SIREPO.APP_SCHEMA.constants.dose2Frame) {
                    if (! $scope.isComparePlot) {
                        return;
                    }
                    dose3d = createData3d(iradService.getDose2Reader().getOutputData());
                }
                renderData();
            }

            function refresh() {
                if (! dicomDomain) {
                    return;
                }
                if (d3.event && d3.event.sourceEvent && ! d3.event.sourceEvent.deltaY) {
                    // x zoom: change frames
                    var scale = d3.event.sourceEvent.deltaX;
                    d3.event = null;
                    if (scale) {
                        if (scale < 0) {
                            $scope.model.frameIdx++;
                        }
                        else {
                            $scope.model.frameIdx--;
                        }
                        $scope.$applyAsync();
                        appState.saveQuietly('dicomReports');
                        return;
                    }
                }

                plotting.trimDomain(xAxisScale, getRange(xValues));
                plotting.trimDomain(yAxisScale, getRange(yValues));
                dicomFeature.draw(canvas, getRange(xValues), getRange(yValues));
                if (roiFeature) {
                    if (appState.models.dicomSettings.showRTStruct == '1') {
                        roiFeature.draw();
                    }
                    else{
                        roiFeature.clear();
                    }
                }
                var offset = 0;
                if (appState.models.dicomSettings.showRTDose == '1') {
                    if ($scope.isDifferencePlot) {
                        if (! xdomain) {
                            return;
                        }
                        if ($scope.model.dicomPlane == 't') {
                            offset = (dicomDomain[1][1] - ydomain[1])
                                - (ydomain[0] - dicomDomain[0][1]);
                        }
                        doseFeature.draw(
                            canvas, xdomain, [
                                ydomain[0] + offset,
                                ydomain[1] + offset,
                            ]);
                    }
                    else if (dose3d) {
                        var doseDomain = domainForPlane(dose3d);
                        if ($scope.model.dicomPlane == 't') {
                            //TODO(pjm): why is offset required for transverse only?
                            offset = (dicomDomain[1][1] - doseDomain[1][1])
                                - (doseDomain[0][1] - dicomDomain[0][1]);
                        }
                        doseFeature.draw(
                            canvas, [
                                doseDomain[0][0],
                                doseDomain[1][0],
                            ], [
                                doseDomain[0][1] + offset,
                                doseDomain[1][1] + offset,
                            ]);
                    }
                }
                resetZoom();
            }

            function initROI() {
                if (dicomDomain && roiFeature) {
                    roiFeature.clear();
                    refresh();
                }
                if (iradService.getDose2Reader()) {
                    loadData3d(null, SIREPO.APP_SCHEMA.constants.dose2Frame);
                }
            }

            function renderData() {
                if (! data3d) {
                    return;
                }

                if ($scope.model.frameIdx > 1e100) {
                    $scope.model.frameIdx = parseInt(
                        data3d.dim[
                            $scope.model.dicomPlane == 't'
                                ? 2
                                : $scope.model.dicomPlane == 's'
                                ? 1 : 0
                        ] / 2);
                }

                // load slice here, sets zFrame
                var pixels = sliceArray(data3d, data3d.metadata.RescaleIntercept, data3d.metadata.RescaleSlope);
                if (roiFeature) {
                    roiFeature.load(zFrame);
                }
                if (dose3d) {
                    if ($scope.isDifferencePlot) {
                        return;
                    }
                    var dosePixels = sliceArray(dose3d, 0, dose3d.metadata.DoseGridScaling);
                    iradService.setDosePixels(
                        $scope.model.dicomPlane,
                        $scope.isComparePlot,
                        zFrame,
                        dosePixels,
                        domainForPlane(dose3d));
                    //TODO(pjm): use one maxDose
                    renderDose(
                        dosePixels,
                        dose3d.metadata.DoseMax * dose3d.metadata.DoseGridScaling);
                }

                var preserveZoom = dicomDomain ? true : false;
                dicomDomain = domainForPlane(data3d);
                xValues = [dicomDomain[0][0], dicomDomain[1][0]];
                yValues = [dicomDomain[0][1], dicomDomain[1][1]];
                if (! preserveZoom) {
                    xAxisScale.domain(getRange(xValues));
                    yAxisScale.domain(getRange(yValues));
                }
                dicomFeature.load(pixels);
                dicomFeature.prepareImage(appState.models.dicomSettings.showCT == '1');
                if (roiFeature) {
                    roiFeature.clear();
                }
                $scope.resize();
            }

            function renderDose(dosePixels, maxDose) {
                if (maxDose > iradService.maxDose) {
                    iradService.maxDose = maxDose;
                }
                maxDose = iradService.maxDose;
                //var colorMap = plotting.colorMapFromModel($scope.modelName);
                var colorMap = plotting.colorMapOrDefault('jet');
                var colorScale = d3.scale.linear()
                    .domain(plotting.linearlySpacedArray(doseFeature.DOSE_CUTOFF, maxDose * 0.8, colorMap.length))
                    .range(colorMap)
                    .clamp(true);
                //TODO(pjm): model data
                var transparency = appState.models.dicomSettings.showCT == '1' ? 56 : 100;
                doseFeature.setColorScale(colorScale, transparency);
                doseFeature.load(dosePixels);
                doseFeature.prepareImage({});
            }

            function resetZoom() {
                zoom = d3.behavior.zoom();
                select('.plot-viewport').call(zoom);
                zoom.x(xAxisScale)
                    .y(yAxisScale)
                    .on('zoom', function() {
                        $rootScope.$broadcast('irad-dicom-zoom', $scope.model.dicomPlane, xAxisScale, yAxisScale);
                    });
            }

            $scope.$on('irad-dicom-zoom', function(evt, plane, x, y) {
                // keep zoom/pan in sync across all common planes
                if (plane == $scope.model.dicomPlane) {
                    xAxisScale.domain(x.domain());
                    yAxisScale.domain(y.domain());
                    refresh();
                }
            });

            function select(selector) {
                var e = d3.select($scope.element);
                return selector ? e.select(selector) : e;
            }
            $scope.select = select;

            function sliceArray(data, rescaleIntercept, rescaleSlope) {
                var voxels = data.pointData;
                var dim = data.dim;
                var res = [];
                var idx = $scope.model.frameIdx;

                //TODO(pjm): refactor the "if" into one sub
                var width, height, xmax, ymax, yi, xi;
                if ($scope.model.dicomPlane == 't') {
                    slicePosition = data3d.bounds[4] + idx * data3d.spacing[2];
                    if (data === dose3d) {
                        idx = Math.round((slicePosition - data.bounds[4]) / data.spacing[2]);
                        if (idx < 0 || idx > dim[2]) {
                            return res;
                        }
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
                else if ($scope.model.dicomPlane == 'c') {
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
                        //TODO(pjm): why are c and s pixels flipped?
                        res[ymax - yi - 1] = [];
                        for (xi = 0; xi < xmax; ++xi) {
                            res[ymax - yi - 1][xi] = voxels[yi * (width * height) + idx * width + xi] * rescaleSlope + rescaleIntercept;
                        }
                    }
                }
                else if ($scope.model.dicomPlane == 's') {
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
                        res[ymax - yi - 1] = [];
                        for (xi = 0; xi < xmax; ++xi) {
                            res[ymax - yi - 1][xi] = voxels[yi * (width * height) + idx + width * xi] * rescaleSlope + rescaleIntercept;
                        }
                    }
                }
                //TODO(pjm): this is directly tied to pkcli.irad ct_z formatting
                zFrame = slicePosition.toFixed(1);
                $scope.model.slicePosition = slicePosition;
                return res;
            }

            $scope.destroy = function() {
                zoom.on('zoom', null);
            };

            $scope.init = function() {
                if (! appState.isLoaded()) {
                    return;
                }
                appState.models.dicomReports.forEach(function(report) {
                    var modelKey = 'dicomReport' + report.id;
                    if (modelKey == $scope.modelName) {
                        $scope.model = report;
                    }
                });
                roiFeature = $scope.model.dicomPlane == 't' ? dicomROIFeature($scope, appState, iradService) : null;

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
                if (select().empty() || ! dicomDomain) {
                    return;
                }
                var canvasWidth = parseInt(select().style('width')) - $scope.margin.left - $scope.margin.right;
                if (isNaN(canvasWidth)) {
                    return;
                }
                $scope.canvasWidth = canvasWidth;
                $scope.canvasHeight = canvasWidth * getSize(yValues) / getSize(xValues);
                var w = $($window);
                if ($scope.canvasHeight > w.height()) {
                    // full screen - don't extend past height
                    var scale = w.height() / $scope.canvasHeight * 0.9;
                    $scope.canvasWidth *= scale;
                    $scope.canvasHeight *= scale;
                }
                else if ($scope.canvasWidth > $scope.canvasHeight) {
                    $scope.margin.top = ($scope.canvasWidth - $scope.canvasHeight) / 2;
                    $scope.margin.bottom = ($scope.canvasWidth - $scope.canvasHeight) / 2;
                }
                xAxisScale.range([0, $scope.canvasWidth]);
                yAxisScale.range([$scope.canvasHeight, 0]);
                canvas.width = $scope.canvasWidth;
                canvas.height = $scope.canvasHeight;
                refresh();
            };

            $scope.yMax = function() {
                return yValues[yValues.length - 1] + yValues[0];
            };

            $scope.initData = function() {
                $scope.$on('irad-vti-available', loadData3d);
                if (iradService.getROIPoints()) {
                    loadData3d(null, SIREPO.APP_SCHEMA.constants.dicomFrame);
                    loadData3d(null, SIREPO.APP_SCHEMA.constants.doseFrame);
                    initROI();
                }
                else {
                    $scope.$on('irad-roi-available', initROI);
                }
                $scope.$on('dicomSettings.changed', renderData);
                $scope.$watch('model.frameIdx', renderData);
                $scope.$on('irad-compute-dose-comparison', computeDoseComparison);
            };
        },
        link: function link(scope, element) {
            appState.whenModelsLoaded(scope, function() {
                plotting.linkPlot(scope, element);
                scope.initData();
            });
        },
    };
});

SIREPO.app.directive('dicomObjectSelector', function(appState, iradService) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            //TODO(pjm): move style into classes
            '<div data-ng-repeat="row in rows" style="padding: 0.5ex 0; white-space: nowrap; overflow: hidden">',
              '<div>',
                '<div data-ng-if="row.items" style="display: inline-block; cursor: pointer; margin-right: 5px; white-space: nowrap" data-ng-click="toggleExpanded(row)">',
                  '<span class="glyphicon" data-ng-class="row.isExpanded ? \'glyphicon-collapse-up\' : \'glyphicon-collapse-down\'"></span>',
                '</div>',
                '<div style="display: inline-block; cursor: pointer; white-space: nowrap" data-ng-click="toggleSelected(row)">',
                  '<span class="glyphicon" data-ng-class="appState.models.dicomSettings[row.field] == \'1\' ? \'glyphicon-check\' : \'glyphicon-unchecked\'"></span>',
                  ' {{ row.name }}',
                '</div>',
              '</div>',
              '<div data-ng-show="row.isExpanded" data-ng-repeat="item in row.items" style="padding: 0.3ex 0;">',
                '<div style="white-space: nowrap; overflow: hidden; padding-left: 18px;">',

                  ' <div style="display: inline-block; cursor: pointer" data-ng-click="toggleSubitem(row, item)">',
                    '<span class="glyphicon" data-ng-class="appState.models.dicomSettings.selectedROIs[item.id] == \'1\' ? \'glyphicon-check\' : \'glyphicon-unchecked\'"></span>',

                    ' <div class="irad-circle" data-ng-if="item.color" style="background-color: {{ itemColor(item) }}"> </div>',
                    ' {{ item.name }}',
                  '</div>',
                '</div>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.appState = appState;
            $scope.itemColor = function(item) {
                var c = item.color;
                return c && window.d3 ? d3.rgb(c[0], c[1], c[2]) : '#000';
            };

            function init() {
                if ($scope.rows) {
                    return;
                }
                $scope.rows = [];
                ['showCT', 'showRTDose', 'showRTStruct', 'showRTPlan'].forEach(function(f) {
                    var info = SIREPO.APP_SCHEMA.model.dicomSettings[f];
                    $scope.rows.push({
                        name: info[0],
                        model: 'dicomSettings',
                        field: f,
                        isExpanded: true,
                    });
                });
            }

            function loadROIs() {
                if (! appState.models.dicomSettings.selectedROIs) {
                    appState.models.dicomSettings.selectedROIs = {};
                }
                var rois = iradService.getROIPoints();
                var items = [];
                Object.keys(rois).forEach(function(roiNumber) {
                    if (!(roiNumber in appState.models.dicomSettings.selectedROIs)) {
                        appState.models.dicomSettings.selectedROIs[roiNumber] = '1';
                    }
                    var roi = rois[roiNumber];
                    if (! roi.color) {
                        return;
                    }
                    items.push({
                        id: roiNumber,
                        name: roi.name,
                        //TODO(pjm): why index 0?
                        color: roi.color[0],
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
                    },
                    {
                        name: 'Beam 2',
                    },
                ];
            }

            $scope.toggleExpanded = function(row) {
                row.isExpanded = ! row.isExpanded;
            };

            $scope.toggleSelected = function(row) {
                if (row.field) {
                    var v = appState.models[row.model][row.field];
                    appState.models[row.model][row.field] = v == '1' ? '0' : '1';
                    appState.saveChanges(row.model);
                }
            };

            $scope.toggleSubitem = function(row, item) {
                if (row.field == 'showRTStruct') {
                    var selected = appState.models.dicomSettings.selectedROIs;
                    selected[item.id] = selected[item.id] == '1' ? '0' : '1';
                    appState.saveChanges(row.model);
                }
            };

            appState.whenModelsLoaded($scope, function() {
                init();
                if (iradService.getROIPoints()) {
                    loadROIs();
                }
                else {
                    $scope.$on('irad-roi-available', loadROIs);
                }
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
                    appState.models.dicomSettings.toggle3D = $scope.selected;
                    appState.saveChanges('dicomSettings');
                }
            };
        },
    };
});

SIREPO.app.directive('downloadStatus', function(iradService) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<div data-ng-if="iradService.downloadStatus" class="col-sm-12">',
              '<div class="progress" style="height: 28px; margin-bottom: 5px">',
                '<div class="progress-bar progress-bar-striped active" role="progressbar" aria-valuenow="100" aria-valuemin="0" aria-valuemax="100" style="width: 100%; font-size: 24px">',
                  '<span class="glyphicon glyphicon-hourglass"></span> {{ iradService.downloadStatus }}',
                '</div>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.iradService = iradService;
        },
    };
});
