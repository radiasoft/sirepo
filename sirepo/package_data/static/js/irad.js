'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;
SIREPO.appReportTypes = [
    '<div data-ng-switch-when="dicomTranspose" data-dicom-plot="" class="sr-plot" data-dicom-plane="t" data-model-name="{{ modelKey }}"></div>',
    '<div data-ng-switch-when="dicomSagittal" data-dicom-plot="" class="sr-plot" data-dicom-plane="s" data-model-name="{{ modelKey }}"></div>',
    '<div data-ng-switch-when="dicomCoronal" data-dicom-plot="" class="sr-plot" data-dicom-plane="c" data-model-name="{{ modelKey }}"></div>',
    '<div data-ng-switch-when="dicom3d" data-dicom-3d="" class="sr-plot" data-model-name="{{ modelKey }}" data-report-id="reportId"></div>',
].join('');

SIREPO.app.factory('iradService', function(appState, requestSender, $rootScope) {
    var self = {};
    var simulationId;
    var roiPoints;

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

    $rootScope.$on('modelsUnloaded', function() {
        simulationId = null;
        roiPoints = null;
    });

    appState.setAppService(self);
    return self;
});

SIREPO.app.controller('SourceController', function (appState, panelState, $scope) {
    var self = this;
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

SIREPO.app.directive('dicom3d', function(appState, iradService, plotting, requestSender, vtkToPNG) {
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
            $scope.isClientOnly = true;

            function addOrientationMarker() {
                orientationMarker = vtk.Interaction.Widgets.vtkOrientationMarkerWidget.newInstance({
                    actor: vtk.Rendering.Core.vtkAxesActor.newInstance(),
                    interactor: fsRenderer.getRenderWindow().getInteractor(),
                    viewportCorner: vtk.Interaction.Widgets.vtkOrientationMarkerWidget.Corners.TOP_RIGHT,
                    viewportSize: 0.15,
                });
                orientationMarker.setEnabled(true);
            }

            function color(v) {
                return vtk.Common.Core.vtkMath.hex2float(v);
            }

            function refresh(event, reader, frame) {
                if (frame != 1) {
                    return;
                }
                removeActors();

                var actor = vtk.Rendering.Core.vtkVolume.newInstance();
                var mapper = vtk.Rendering.Core.vtkVolumeMapper.newInstance();
                //mapper.setSampleDistance(0.7);
                //mapper.setSampleDistance(4);
                actor.setMapper(mapper);
                mapper.setInputConnection(reader.getOutputPort());

                var ctfun = vtk.Rendering.Core.vtkColorTransferFunction.newInstance();
                ctfun.addRGBPoint(200.0, 0.4, 0.2, 0.0);
                ctfun.addRGBPoint(2000.0, 1.0, 1.0, 1.0);
                var ofun = vtk.Common.DataModel.vtkPiecewiseFunction.newInstance();
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

                var renderer = fsRenderer.getRenderer();
                renderer.addVolume(actor);
                renderer.resetCamera();
                var cam =  renderer.getActiveCamera();
                var pos = cam.getPosition();
                cam.zoom(1.5);
                cam.roll(30);
                cam.elevation(-100);
                renderer.updateLightsGeometryToFollowCamera();
                fsRenderer.getRenderWindow().render();

                addOrientationMarker();
                pngCanvas.copyCanvas();
            }

            function removeActors() {
                var renderer = fsRenderer.getRenderer();
                renderer.getActors().forEach(function(actor) {
                    renderer.removeActor(actor);
                });
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

    return {
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
            '<div><svg class="sr-plot" style="position: relative;" ng-attr-width="{{ margin.left + margin.right + canvasWidth }}" ng-attr-height="{{ margin.top + margin.bottom + canvasHeight }}">',
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
            $scope.margin = {top: 0, left: 0, right: 0, bottom: 0};

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
            var zFrame;

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
                res.bounds[5] = res.bounds[4] - res.spacing[2] * (res.dim[2] - 1);
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
                        .domain(plotting.linearlySpacedArray(0, maxDose * 0.8, colorMap.length))
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
                var width, height, xmax, ymax, yi, xi, pos;
                if (dicomPlane == 't') {
                    if (data === dose3d) {
                        pos = data3d.bounds[4] - idx * data3d.spacing[2];
                        idx = Math.round((zFrame - data.bounds[4]) / -data.spacing[2]);
                        zFrame = pos.toFixed(1);
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
                    if (data === dose3d) {
                        pos = data3d.bounds[2] + idx * data3d.spacing[1];
                        idx = Math.round((pos - data.bounds[2]) / data.spacing[1]);
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
                    if (data === dose3d) {
                        pos = data3d.bounds[0] + idx * data3d.spacing[0];
                        idx = Math.round((pos - data.bounds[0]) / data.spacing[0]);
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
                return res;
            }

            $scope.destroy = function() {
                zoom.on('zoom', null);
            };

            // $scope.dicomTitle = function() {
            //     return rs4piService.dicomTitle($scope.modelName);
            // };

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
