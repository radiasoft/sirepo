'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.appReportTypes = [
        '<div data-ng-switch-when="dicom" data-dicom-plot="" class="sr-plot" data-model-name="{{ modelKey }}"></div>',
    ].join('');
    SIREPO.PLOTTING_COLOR_MAP = 'grayscale';
    SIREPO.appFieldEditors += [
        '<div data-ng-switch-when="ROI" class="col-sm-7">',
          '<div data-roi-selector="" data-field="model[field]"></div>',
        '</div>',
        '<div data-ng-switch-when="ROIArray" class="col-sm-7">',
          '<div data-roi-selection-list="" data-field="model[field]" data-model-name="modelName"></div>',
        '</div>',
    ].join('');
});

SIREPO.app.factory('rs4piService', function(appState, frameCache, requestSender, $rootScope) {
    var self = {};
    var PLANE_COORD_NAME = {
        t: 'z',
        s: 'x',
        c: 'y',
    };
    var dicomHistogram = {};
    var planeCoord = {};
    var roiPoints = {};
    var simulationId = null;
    // zoom or advanceFrame
    self.mouseWheelMode = 'advanceFrame';
    self.isEditing = false;
    // select or draw
    self.editMode = 'select';
    // for simulated dose calculations
    self.showDosePanels = false;


    self.computeModel = function(analysisModel) {
        if (! analysisModel || analysisModel.indexOf('dicomAnimation') >=0) {
            return 'dicomAnimation';
        }
        if (analysisModel == 'dicomDose') {
            return 'doseCalculation';
        }
        return analysisModel;
    };

    self.dicomTitle = function(modelName) {
        if (! appState.isLoaded()) {
            return;
        }
        var series = appState.models.dicomSeries;
        var enumText = '';
        var plane = appState.models[modelName].dicomPlane;
        SIREPO.APP_SCHEMA.enum.DicomPlane.forEach(function(enumInfo) {
            if (enumInfo[0] == plane) {
                enumText = enumInfo[1];
            }
        });
        var planeCoord = self.getPlaneCoord(plane);
        return enumText + ' (' + (frameCache.getCurrentFrame(modelName) + 1)
            + ' / ' + series.planes[plane].frameCount + ') '
            + (planeCoord ? (
                PLANE_COORD_NAME[plane] + ': ' + planeCoord.toFixed(1) + 'mm'
            ) : '');
    };

    self.getActiveROI = function() {
        if (! appState.isLoaded()) {
            return null;
        }
        return appState.models.dicomSeries.activeRoiNumber;
    };

    self.getActiveROIPoints = function() {
        return roiPoints[self.getActiveROI()];
    };


    self.getDicomHistogram = function() {
        return dicomHistogram;
    };

    self.getPlaneCoord = function(plane) {
        return planeCoord[plane];
    };

    self.getROIPoints = function() {
        return roiPoints;
    };

    self.getSortedList = function() {
        var res = [];
        Object.keys(roiPoints).forEach(function(roiNumber) {
            var roi = roiPoints[roiNumber];
            roi.roiNumber = roiNumber;
            if (roi.color && roi.contour && ! $.isEmptyObject(roi.contour)) {
                res.push(roi);
            }
        });
        res.sort(function(a, b) {
            return a.name.localeCompare(b.name);
        });
        return res;
    };

    self.hasDoseFrames = function() {
        if (appState.isLoaded()) {
            return appState.models.dicomDose.frameCount > 0;
        }
        return false;
    };

    self.hasROIContours = function() {
        for (var roiNumber in roiPoints) {
            var roi = roiPoints[roiNumber];
            if (roi.contour) {
                for (var frameId in roi.contour) {
                    if (roi.contour[frameId].length) {
                        return true;
                    }
                }
            }
        }
        return false;
    };

    self.isEditMode = function(mode) {
        if (self.isEditing) {
            return self.editMode == mode;
        }
        return false;
    };

    self.isMouseWheelMode = function(mode) {
        return self.mouseWheelMode == mode;
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
                dicomHistogram = data.models.dicomHistogram;
                roiPoints = data.models.regionsOfInterest;
                $rootScope.$broadcast('roiPointsLoaded');
            });
    };

    self.setActiveROI = function(roiNumber) {
        appState.models.dicomSeries.activeRoiNumber = roiNumber;
        $rootScope.$broadcast('roiActivated');
    };

    self.setEditMode = function(mode) {
        self.editMode = mode;
    };

    self.setEditorDirty = function() {
        var editorState = appState.models.dicomEditorState;
        editorState.editCounter = (editorState.editCounter || 0) + 1;
    };

    self.setPlaneCoord = function(plane, v) {
        if (planeCoord[plane] != v) {
            planeCoord[plane] = v;
            $rootScope.$broadcast('planeCoordChanged');
        }
    };

    self.setMouseWheelMode = function(mode) {
        self.mouseWheelMode = mode;
        $rootScope.$broadcast('refreshDicomPanels');
    };

    self.toggleEditing = function() {
        self.isEditing = ! self.isEditing;
    };

    self.updateDicomAndDoseFrame = function(waitForDose) {
        var status = appState.models.simulationStatus;
        if (status.dicomAnimation && status.dicomAnimation.percentComplete == 100) {
            if (! waitForDose) {
                frameCache.setFrameCount(1);
            }
            else if (status.doseCalculation && status.doseCalculation.percentComplete == 100) {
                // wait for both dicomAnimation and doseCalculation status
                frameCache.setFrameCount(1);
            }
        }
    };

    self.updateROIPoints = function(editedContours) {
        requestSender.getApplicationData(
            {
                method: 'update_roi_points',
                simulationId: appState.models.simulation.simulationId,
                editedContours: editedContours,
            },
            function() {});
    };

    appState.setAppService(self);
    return self;
});

SIREPO.app.controller('Rs4piDoseController', function (appState, frameCache, panelState, persistentSimulation, rs4piService, $scope) {
    var self = this;
    self.simScope = $scope;
    self.analysisModel = 'doseCalculation';

    self.panelState = panelState;

    self.simHandleStatus = function (data) {
        if (data.report == 'doseCalculation' && data.state == 'completed') {
            if (data.dicomDose && ! appState.deepEquals(appState.models.dicomDose, data.dicomDose)) {
                appState.models.dicomDose = data.dicomDose;
                appState.saveChanges('dicomDose');
            }
            rs4piService.updateDicomAndDoseFrame(true);
        }
    };

    self.showDosePanels = function() {
        return rs4piService.showDosePanels;
    };

    self.hasDoseFrames = function() {
        if (appState.isLoaded()) {
            return appState.models.dicomDose.frameCount > 0;
        }
        return false;
    };

    appState.whenModelsLoaded($scope, function() {
        rs4piService.loadROIPoints();
    });

    self.simState = persistentSimulation.initSimulationState(self);
});

SIREPO.app.controller('Rs4piSourceController', function (appState, frameCache, rs4piService, $rootScope, $scope) {
    var self = this;

    self.dicomTitle = function() {
        if (! appState.isLoaded()) {
            return;
        }
        return appState.models.dicomSeries.description;
    };

    self.hasFrames = function() {
        return frameCache.hasFrames();
    };

    $scope.$on('cancelChanges', function(e, name) {
        if (name == 'dicomEditorState') {
            $rootScope.$broadcast('roiPointsLoaded');
        }
    });

    appState.whenModelsLoaded($scope, function() {
        rs4piService.loadROIPoints();
    });
});

SIREPO.app.directive('appHeader', function(appState, fileManager, panelState, rs4piService) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appHeader',
        },
        template: [
            '<div data-app-header-brand="nav"></div>',
            '<div data-app-header-left="nav" data-simulations-link-text="Studies"></div>',
            '<ul class="nav navbar-nav navbar-right" data-login-menu=""></ul>',
            '<ul class="nav navbar-nav navbar-right" data-ng-show="isLoaded()">',
              '<li data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-equalizer"></span> Structure</a></li>',
              '<li data-ng-show="rs4piService.hasDoseFrames()" data-ng-class="{active: nav.isActive(\'dose\')}"><a href data-ng-click="nav.openSection(\'dose\')"><span class="glyphicon glyphicon-dashboard"></span> Dose</a></li>',
            '</ul>',
            '<ul class="nav navbar-nav navbar-right" data-ng-show="nav.isActive(\'simulations\')">',
              '<li><a href data-ng-click="importDicomModal()"><span class="glyphicon glyphicon-plus sr-small-icon"></span><span class="glyphicon glyphicon-file"></span> Import DICOM</a></li>',
              '<li><a href data-ng-click="showNewFolderModal()"><span class="glyphicon glyphicon-plus sr-small-icon"></span><span class="glyphicon glyphicon-folder-close"></span> New Folder</a></li>',
            '</ul>',

        ].join(''),
        controller: function($scope) {
            $scope.rs4piService = rs4piService;
            $scope.isLoaded = function() {
                return appState.isLoaded();
            };
            $scope.showNewFolderModal = function() {
                appState.models.simFolder.parent = fileManager.defaultCreationFolderPath();
                panelState.showModalEditor('simFolder');
            };
            $scope.importDicomModal = function() {
                $('#dicom-import').modal('show');
            };

        },
    };
});

SIREPO.app.directive('appFooter', function() {
    return {
        restrict: 'A',
        scope: {
            nav: '=appFooter',
        },
        template: [
            '<div data-dicom-import-dialog=""></div>',
        ].join(''),
    };
});

SIREPO.app.directive('dicomFrames', function(frameCache, persistentSimulation, rs4piService) {
    return {
        restrict: 'A',
        scope: {
            model: '@dicomFrames',
            waitForDose: '@',
        },
        controller: function($scope) {
            var self = this;
            self.simScope = $scope;
            self.analysisModel = $scope.model;

            self.simHandleStatus = function(data) {
                if ($scope.model == 'dicomAnimation' && data.state == 'missing' && data.percentComplete === 0) {
                    $scope.simState.runSimulation();
                    return;
                }
                rs4piService.updateDicomAndDoseFrame($scope.waitForDose);
            };

            $scope.simState = persistentSimulation.initSimulationState(self);
        },
    };
});

SIREPO.app.directive('roiSelector', function(appState, rs4piService) {
    return {
        scope: {
            field: '=',
        },
        restrict: 'A',
        template: [
            '<select class="form-control" data-ng-model="field" data-ng-options="item.roiNumber as item.name for item in roiList"></select>',
        ].join(''),
        controller: function($scope) {
            function loadROIPoints() {
                $scope.roiList = rs4piService.getSortedList();
            }
            if (rs4piService.getROIPoints()) {
                loadROIPoints();
            }
            $scope.$on('roiPointsLoaded', loadROIPoints);
        },
    };
});

SIREPO.app.directive('roiSelectionList', function(appState, rs4piService) {
    return {
        scope: {
            field: '=',
            modelName: '=',
        },
        restrict: 'A',
        template: [
            '<div style="margin: 5px 0; min-height: 34px; max-height: 20em; overflow-y: auto; border: 1px solid #ccc; border-radius: 4px">',
              '<table class="table table-condensed table-hover" style="margin:0">',
                '<tbody>',
                  '<tr data-ng-repeat="roi in roiList | filter:canSelectROI track by $index" data-ng-click="toggleROI(roi)">',
                    '<td>{{ roi.name }}</td>',
                    '<td><input type="checkbox" data-ng-checked="isSelected(roi)"></td>',
                  '</tr>',
                '</tbody>',
              '</table>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            function loadROIPoints() {
                $scope.roiList = rs4piService.getSortedList();
            }
            $scope.canSelectROI = function(roi) {
                if (appState.isLoaded()) {
                    if ($scope.modelName == 'doseCalculation') {
                        return roi.roiNumber != appState.models.doseCalculation.selectedPTV;
                    }
                    return true;
                }
                return false;
            };
            $scope.isSelected = function(roi) {
                if ($scope.field) {
                    return $scope.field.indexOf(roi.roiNumber) >= 0;
                }
                return false;
            };
            $scope.toggleROI = function(roi) {
                if ($scope.field) {
                    if ($scope.isSelected(roi)) {
                        $scope.field.splice($scope.field.indexOf(roi.roiNumber), 1);
                    }
                    else {
                        $scope.field.push(roi.roiNumber);
                    }
                }
            };
            if (rs4piService.getROIPoints()) {
                loadROIPoints();
            }
            $scope.$on('roiPointsLoaded', loadROIPoints);
        },
    };
});

SIREPO.app.directive('computeDoseForm', function(appState, panelState, rs4piService, $timeout) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<form class="form-horizontal">',
            '<div data-model-field="\'selectedPTV\'" data-model-name="\'doseCalculation\'" data-label-size="3"></div>',
            '<div data-model-field="\'selectedOARs\'" data-model-name="\'doseCalculation\'" data-label-size="3"></div>',
            '<div class="col-sm-10">',
              '<div class="pull-right">',
                '<button class="btn btn-default" data-ng-disabled="! appState.models.doseCalculation.selectedPTV" data-ng-click="updatePTV()">Compute Dose</button>',
              '</div>',
            '</div>',
            '</form>',
        ].join(''),
        controller: function($scope) {
            $scope.appState = appState;
            $scope.doseController = panelState.findParentAttribute($scope, 'dose');
            var complete = 0;

            function simulationDoseCalculation() {
                if (complete < 100) {
                    complete += 16;
                    $timeout(simulationDoseCalculation, 1000);
                }
                else {
                    rs4piService.showDosePanels = true;
                    complete = 0;
                    $scope.doseController.simState.isProcessing = function() {
                        return false;
                    };
                }
            }

            function stateAsText() {
                if (complete < 100) {
                    return 'Computing Dose';
                }
                return 'Complete';
            }

            $scope.updatePTV = function() {
                //$scope.doseController.simState.saveAndRunSimulation('doseCalculation');
                $scope.doseController.simState.stateAsText = stateAsText;
                $scope.doseController.simState.isProcessing = function() {
                    return true;
                };
                $scope.doseController.simState.getPercentComplete = function() {
                    return complete;
                };
                $timeout(simulationDoseCalculation, 1000);
            };
        },
    };
});

SIREPO.app.directive('dicomImportDialog', function(appState, fileManager, fileUpload, requestSender) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<div class="modal fade" data-backdrop="static" id="dicom-import" tabindex="-1" role="dialog">',
              '<div class="modal-dialog modal-lg">',
                '<div class="modal-content">',
                  '<div class="modal-header bg-info">',
                    '<button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>',
                    '<div data-help-button="{{ title }}"></div>',
                    '<span class="lead modal-title text-info">{{ title }}</span>',
                  '</div>',
                  '<div class="modal-body">',
                    '<div class="container-fluid">',
                        '<form class="form-horizontal" name="importForm">',
                          '<div data-ng-show="filename" class="form-group">',
                            '<label class="col-xs-4 control-label">Importing file</label>',
                            '<div class="col-xs-8">',
                              '<p class="form-control-static">{{ filename }}</p>',
                            '</div>',
                          '</div>',
                          '<div data-ng-show="isState(\'ready\')">',
                            '<div data-ng-show="isState(\'ready\')" class="form-group">',
                              '<label>Select DICOM Series (.zip) File</label>',
                              '<input id="dicom-file-import" type="file" data-file-model="dicomFile" accept=".zip" />',
                              '<br />',
                              '<div class="text-warning"><strong>{{ fileUploadError }}</strong></div>',
                            '</div>',
                            '<div class="col-sm-6 pull-right">',
                              '<button data-ng-click="importDicomFile(dicomFile)" class="btn btn-primary" data-ng-disabled="! dicomFile">Import File</button>',
                              ' <button data-dismiss="modal" class="btn btn-default">Cancel</button>',
                            '</div>',
                          '</div>',
                          '<div data-ng-show="isState(\'import\')" class="col-sm-12">',
                            '<div class="text-center">',
                              '<span class="glyphicon glyphicon-hourglass"> </span> ',
                              'Importing file - please wait.',
                              '<br /><br />',
                            '</div>',
                          '</div>',
                        '</form>',
                      '</div>',
                    '</div>',
                  '</div>',
                '</div>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.title = 'Import DICOM File';
            $scope.state = 'ready';

            function hideAndRedirect(id) {
                $('#dicom-import').modal('hide');
                requestSender.localRedirect('source', {
                    ':simulationId': id,
                });
            }

            $scope.importDicomFile = function(dicomFile) {
                if (! dicomFile) {
                    return;
                }
                $scope.state = 'import';
                fileUpload.uploadFileToUrl(
                    dicomFile,
                    {
                        folder: fileManager.getActiveFolderPath(),
                    },
                    requestSender.formatUrl(
                        'importFile',
                        {
                            '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                        }),
                    function(data) {
                        if (data.error || ! data.models) {
                            $scope.resetState();
                            $scope.fileUploadError = data.error || 'A server error occurred.';
                        }
                        else {
                            hideAndRedirect(data.models.simulation.simulationId);
                        }
                    });
            };

            $scope.isState = function(state) {
                return $scope.state == state;
            };

            $scope.resetState = function() {
                $scope.dicomFile = null;
                $scope.fileUploadError = '';
                $scope.state = 'ready';
            };
        },
        link: function(scope, element) {
            $(element).on('show.bs.modal', function() {
                $('#dicom-file-import').val(null);
                scope.$applyAsync(scope.resetState);
            });
            scope.$on('$destroy', function() {
                $(element).off();
            });
        },
    };
});

SIREPO.app.directive('dicomHistogram', function(appState, plotting, rs4piService) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        template: [
            '<svg class="sr-plot sr-histogram" width="100%" ng-attr-height="{{ height + margin.top + margin.bottom }}">',
              '<g class="plot-g" ng-attr-transform="translate({{ margin.left }},{{ margin.top }})">',
                '<g class="x axis" ng-attr-transform="translate(0, {{ height }})">',
                  '<text class="x-axis-label" ng-attr-x="{{ width / 2 }}" y="40">Hounsfield Units (HU)</text>',
                '</g>',
              '</g>',
            '</svg>',
        ].join(''),
        controller: function($scope) {
            var MIN_HEIGHT = 40;
            $scope.margin = {top: 20, right: 20, bottom: 45, left: 20};
            $scope.width = 0;
            $scope.height = 0;
            var arc, bins, brush, brushg, histogram, plotg, svg, xAxis, xScale, yScale;
            $scope.isClientOnly = true;

            function brushend() {
                if (brush.empty()) {
                    setBounds(null);
                    return;
                }
                var b = brush.extent();
                var left = b[0],
                    right = b[1];
                bins.map(function(d) {
                    left = trimBound(d, left);
                    right = trimBound(d, right);
                });
                setBounds([left, right]);
            }

            function redrawSelectedArea() {
                if (brush.empty()) {
                    svg.selectAll('.bar rect').style('opacity', '1');
                    return;
                }
                var b = brush.extent();
                svg.selectAll('.bar rect').style('opacity', function(d) {
                    return d.x + d.dx/2.0 > b[0] && d.x + d.dx/2.0 < b[1] ? "1" : ".4";
                });
            }

            function setBounds(bounds) {
                if (bounds && bounds[0] != bounds[1]) {
                    //TODO(pjm): validate bounds within domain?
                    brushg.call(brush.extent(bounds));
                }
                else {
                    brush.clear();
                    bounds = xScale.domain();
                }
                var dicomWindow = appState.models.dicomWindow;
                dicomWindow.width = bounds[1] - bounds[0];
                dicomWindow.center = bounds[0] + dicomWindow.width / 2;
                $scope.$applyAsync(function() {
                    appState.saveChanges('dicomWindow');
                });
            }

            function trimBound(d, bound) {
                if (d.x + d.dx > bound && d.x < bound) {
                    if (d.x + d.dx/2.0 > bound) {
                        return d.x;
                    }
                    return d.x + d.dx;
                }
                return bound;
            }

            $scope.destroy = function() {
            };

            $scope.init = function() {
                svg = d3.select($scope.element).select('.sr-histogram');
                plotg = svg.select('.plot-g');
                histogram = d3.layout.histogram();
                xScale = d3.scale.linear();
                yScale = d3.scale.linear();
                brush = d3.svg.brush()
                    .on('brush', redrawSelectedArea)
                    .on('brushend', brushend);
                arc = d3.svg.arc()
                    .startAngle(0)
                        .endAngle(function(d, i) { return i ? -Math.PI : Math.PI; });
                xAxis = d3.svg.axis()
                   .scale(xScale)
                   .orient('bottom');
            };

            $scope.load = function() {
                if (! svg) {
                    return;
                }
                var dicomHistogram = rs4piService.getDicomHistogram();
                var idx = 0;
                var extent = dicomHistogram.extent;
                if (! extent) {
                    // dicomHistogram not loaded yet
                    return;
                }
                var dx = (extent[1] - extent[0]) / (extent[2] - 1);
                xScale.domain([extent[0], extent[1]]);
                bins = plotting.linearlySpacedArray(extent[0], extent[1], extent[2]).map(function(d) {
                    return {
                        x: d,
                        dx: dx,
                        y: dicomHistogram.histogram[idx++],
                    };
                });
                yScale.domain([0, d3.max(bins, function(d){return d.y;})]).nice();
                plotg.selectAll('.bar').remove();
                var bar = plotg.selectAll('.bar')
                    .data(bins)
                    .enter().append('g')
                    .attr('class', 'bar');
                bar.append('rect')
                    .attr('x', 1);
                plotg.selectAll('.brush').remove();
                brushg = plotg.append('g')
                    .attr('class', 'brush')
                    .call(brush);
                brushg.selectAll('.resize').append('path');
                $scope.resize();
            };

            $scope.resize = function() {
                if (plotg.select('.bar').empty()) {
                    return;
                }
                $scope.width = parseInt(svg.style('width')) - $scope.margin.left - $scope.margin.right;
                $scope.height = Math.floor($scope.width / 1.5) - $scope.margin.top - $scope.margin.bottom;
                if ($scope.height < MIN_HEIGHT) {
                    $scope.height = MIN_HEIGHT;
                }
                xScale.range([0, $scope.width]);
                yScale.range([$scope.height, 0]);
                plotting.ticks(xAxis, $scope.width, true);
                plotg.selectAll('.bar')
                    .attr('transform', function(d) { return 'translate(' + xScale(d.x) + ',' + yScale(d.y) + ')'; });
                plotg.selectAll('.bar rect')
                    .attr('width', (xScale(bins[0].dx) - xScale(0)) - 1)
                    .attr('height', function(d) { return $scope.height - yScale(d.y); });
                plotg.select('.x.axis')
                    .call(xAxis);
                arc.outerRadius($scope.height / 15);
                brush.x(xScale);
                brushg.call(brush);
                brushg.selectAll('.resize path')
                    .attr('transform', 'translate(0,' +  $scope.height / 2 + ')')
                    .attr('d', arc);
                brushg.selectAll('.resize path')
                    .attr('transform', 'translate(0,' +  $scope.height / 2 + ')');
                brushg.selectAll('rect')
                    .attr('height', $scope.height);
                var dicomWindow = appState.models.dicomWindow;
                var b = [dicomWindow.center - dicomWindow.width / 2, dicomWindow.center + dicomWindow.width / 2];
                if (b[0] == xScale.domain()[0] && b[1] == xScale.domain()[1]) {
                    brush.clear();
                }
                else {
                    brushg.call(brush.extent(b));
                }
                redrawSelectedArea();
            };

            $scope.$on('roiPointsLoaded', function() {
                $scope.load();
            });

            $scope.$on('dicomWindow.changed', function() {
                $scope.resize();
            });

        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});

function dicomPlaneLinesFeature($scope, rs4piService) {
    var dragLine, xAxisScale, yAxisScale;
    var planeLines = null;

    function createPlaneLines(axis) {
        return {
            planeLine: $scope.select('.draw-area')
                .append('line')
                .attr('class', 'cross-hair')
                .attr(oppositeAxis(axis) + '1', 0),
            dragLine: $scope.select('.draw-area')
                .append('line')
                .attr('class', 'plane-dragline plane-dragline-' + axis)
                .attr(oppositeAxis(axis) + '1', 0)
                .call(dragLine),
        };
    }

    function lineDrag() {
        /*jshint validthis: true*/
        var line = d3.select(this);
        if (line.classed('plane-dragline-y')) {
            var y = parseFloat(line.attr('y1')) + parseFloat(d3.event.dy);
            line.attr('y1', y).attr('y2', y);
            planeLines.y.planeLine.attr('y1', y).attr('y2', y);
        }
        else if (line.classed('plane-dragline-x')) {
            var x = parseFloat(line.attr('x1')) + parseFloat(d3.event.dx);
            line.attr('x1', x).attr('x2', x);
            planeLines.x.planeLine.attr('x1', x).attr('x2', x);
        }
    }

    function lineDragEnd() {
        /*jshint validthis: true*/
        var line = d3.select(this);
        if (line.classed('plane-dragline-y')) {
            var y = yAxisScale.invert(line.attr('y1'));
            if ($scope.isTransversePlane()) {
                y = $scope.flipud(y);
            }
            $scope.updateTargetPlane('y', y);
        }
        else if (line.classed('plane-dragline-x')) {
            $scope.updateTargetPlane('x', xAxisScale.invert(line.attr('x1')));
        }
    }

    function oppositeAxis(axis) {
        if (axis == 'y') {
            return 'x';
        }
        if (axis == 'x') {
            return 'y';
        }
        throw new Error('invalid axis: ' + axis);
    }

    function updatePlaneLine(axis, axisScale, size) {
        var v = rs4piService.getPlaneCoord($scope.getTargetPlane(axis));
        if (axis == 'y' && $scope.isTransversePlane()) {
            v = $scope.flipud(v);
        }
        v = axisScale(v);
        if (! isNaN(v)) {
            ['planeLine', 'dragLine'].forEach(function (f) {
                planeLines[axis][f]
                    .attr(axis + '1', v)
                    .attr(axis + '2', v)
                    .attr(oppositeAxis(axis) + '2', size)
                    .classed('selectable-path', ! $scope.isDrawMode());
            });
        }
    }

    function updatePlaneLines() {
        // if (! dicomDomain) {
        //     return;
        // }
        if (! planeLines) {
            planeLines = {
                x: createPlaneLines('x'),
                y: createPlaneLines('y'),
            };
        }
        updatePlaneLine('x', xAxisScale, $scope.canvasHeight);
        updatePlaneLine('y', yAxisScale, $scope.canvasWidth);
    }

    $scope.$on('planeCoordChanged', updatePlaneLines);

    return {
        draw: updatePlaneLines,
        init: function(x, y) {
            xAxisScale = x;
            yAxisScale = y;
            dragLine = d3.behavior.drag()
                .on('drag', lineDrag)
                .on('dragstart', function() {
                    // don't let event propagate to zoom behavior
                    d3.event.sourceEvent.stopPropagation();
                })
                .on('dragend', lineDragEnd);
        },
    };
}

function dicomROIFeature($scope, rs4piService, isDoseDicom) {
    var drag, roiLine, xAxisScale, yAxisScale;
    var drawPath = null;
    var drawPoints = null;
    var editedContours = {};
    var frameId = null;
    var hasDragged = false;
    var roiContours = null;

    function addContours() {
        clearContours();
        var rois = rs4piService.getROIPoints();
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

    function redrawActivePath() {
        var active = roiContours[rs4piService.getActiveROI()];
        if (active) {
            active.roiPath.attr('d', roiLine);
            active.dragPath.attr('d', roiLine);
        }
    }

    function getContourForFrame(roi) {
        var editRoi = editedContours[roi.roiNumber];
        if (editRoi && editRoi[frameId]) {
            return editRoi[frameId];
        }
        if (roi.contour && roi.contour[frameId]) {
            return roi.contour[frameId];
        }
        return null;
    }

    function mousedown() {
        d3.event.preventDefault();
        drawPoints = [mousePoint()];
        var roi = rs4piService.getActiveROIPoints();
        drawPath = $scope.select('.draw-area').append('path')
            .attr('class', 'dicom-roi dicom-roi-selected')
            .datum(drawPoints)
            .attr('d', roiLine)
            .attr('style', roiStyle(roi));
        $scope.select('.draw-area').append('circle')
            .attr('cx', xAxisScale(drawPoints[0][0]))
            .attr('cy', yAxisScale(drawPoints[0][1]))
            .attr('r', 10)
            .attr('class', 'dicom-draw-start')
            .attr('style', roiStyle(roi));
        $scope.select('.overlay').on('mousemove', mousemove)
            .on('mouseup', mouseup);
    }

    function mousemove() {
        if ('buttons' in d3.event && ! d3.event.buttons) {
            // buttonup already happened off the svg
            mouseup();
            return;
        }
        drawPoints.push(mousePoint());
        drawPath.attr('d', roiLine);
    }

    function mousePoint() {
        var p = d3.mouse($scope.select('.overlay').node());
        return [xAxisScale.invert(p[0]), yAxisScale.invert(p[1])];
    }

    function mouseup() {
        drawPath.remove();
        $scope.select('.dicom-draw-start').remove();
        $scope.select('.overlay').on('mousemove', null)
            .on('mouseup', null);
        if (drawPoints.length > 1) {
            var roi = rs4piService.getActiveROIPoints();
            if (roiContours[roi.roiNumber]) {
                var points = roiContours[roi.roiNumber].points;
                if (points.length) {
                    points.push(null);
                    drawPoints = $.merge(points, drawPoints);
                }
            }
            updateContourData(drawPoints);
            addContours();
            rs4piService.setEditorDirty();
            $scope.$applyAsync();
        }
    }

    function redrawContours() {
        if (! roiContours) {
            addContours();
            return;
        }
        var canDrag = rs4piService.isEditMode('select');
        var activeROI = rs4piService.getActiveROI();
        Object.keys(roiContours).forEach(function(roiNumber) {
            var v = roiContours[roiNumber];
            v.roiPath.attr('d', roiLine)
                .classed('dicom-roi-selected', roiNumber == activeROI)
                .attr('style', roiStyle(v.roi, roiNumber));
            v.dragPath.attr('d', roiLine)
                .classed('dicom-dragpath-move', canDrag)
                .classed('dicom-dragpath-select', ! canDrag)
                .classed('selectable-path', ! $scope.isDrawMode());
            if (canDrag) {
                v.dragPath.call(drag);
            }
            else {
                v.dragPath.on('.drag', null);
            }
        });
        $scope.select('.overlay').on('mousemove', null)
            .on('mouseup', null)
            .on('mousedown', $scope.isDrawMode() ? mousedown : null);
    }

    function roiClick() {
        /*jshint validthis: true*/
        if (d3.event.defaultPrevented) {
            return;
        }
        d3.event.preventDefault();
        setActiveROIFromNode(this);
    }

    function roiDrag(d) {
        /*jshint validthis: true*/
        if (! rs4piService.isEditing || ! rs4piService.isEditMode('select')) {
            srlog('roiDrag not select mode');
            return;
        }
        var dx = d3.event.dx;
        var dy = d3.event.dy;
        if (dx || dy) {
            hasDragged = true;
            var xDomain = xAxisScale.domain();
            var xPixelSize = dx * (xDomain[1] - xDomain[0]) / $scope.canvasWidth;
            var yDomain = yAxisScale.domain();
            var yPixelSize = dy * (yDomain[1] - yDomain[0]) / $scope.canvasHeight;
            d.forEach(function(p) {
                if (p) {
                    p[0] += xPixelSize;
                    p[1] -= yPixelSize;
                }
            });
            setActiveROIFromNode(this);
            redrawActivePath();
        }
    }

    function roiDragEnd(d) {
        if (hasDragged) {
            hasDragged = false;
            updateContourData(d);
            rs4piService.setEditorDirty();
            $scope.$applyAsync();
        }
    }

    function roiStyle(roi, roiNumber) {
        var color = roi.color;
        var res = 'stroke: rgb(' + color.join(',') + ')';
        if (! rs4piService.isEditing && ! isDoseDicom  && rs4piService.getActiveROI() == roiNumber) {
            res += '; fill: rgb(' + color.join(',') + '); fill-opacity: 0.5';
        }
        return res;
    }

    function setActiveROI(roiNumber) {
        if (roiNumber == rs4piService.getActiveROI()) {
            return;
        }
        $scope.$applyAsync(function() {
            rs4piService.setActiveROI(roiNumber);
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

    function updateContourData(points) {
        var roi = rs4piService.getActiveROIPoints();
        if (! editedContours[roi.roiNumber]) {
            editedContours[roi.roiNumber] = {};
        }
        var yMax = $scope.yMax();
        var contourList = [];
        editedContours[roi.roiNumber][frameId] = contourList;
        var current = [];
        contourList.push(current);
        points.forEach(function(p) {
            if (p) {
                current.push(
                    p[0],
                    //TODO(pjm): flipud
                    yMax - p[1]);
            }
            else {
                current = [];
                contourList.push(current);
            }
        });
    }

    $scope.deleteSelected = function() {
        var roi = rs4piService.getActiveROIPoints();
        if (! editedContours[roi.roiNumber]) {
            editedContours[roi.roiNumber] = {};
        }
        editedContours[roi.roiNumber][frameId] = [];
        rs4piService.setEditorDirty();
        clearContours();
        redrawContours();
    };

    $scope.isROISelected = function() {
        var num = rs4piService.getActiveROI();
        if (num) {
            var rois = rs4piService.getROIPoints();
            if (rois && num in rois) {
                return rois[num].isVisible;
            }
        }
        return false;
    };

    $scope.$on('cancelChanges', function(e, name) {
        if (name == 'dicomEditorState' && ! $scope.isSubFrame) {
            editedContours = {};
            clearContours();
            redrawContours();
        }
    });

    $scope.$on('dicomEditorState.changed', function() {
        if ($scope.isSubFrame) {
            return;
        }
        var rois = rs4piService.getROIPoints();
        Object.keys(editedContours).forEach(function(roiNumber) {
            Object.keys(editedContours[roiNumber]).forEach(function(frameId) {
                rois[roiNumber].contour[frameId] = editedContours[roiNumber][frameId];
            });
        });
        rs4piService.updateROIPoints(editedContours);
        editedContours = {};
    });

    return {
        clear: clearContours,
        draw: redrawContours,
        init: function(x, y) {
            xAxisScale = x;
            yAxisScale = y;
            drag = d3.behavior.drag()
                .origin(function(d) { return {x: d[0], y: d[1]}; })
                .on('drag', roiDrag)
                .on('dragstart', function() {
                    // don't let event propagate to zoom behavior
                    d3.event.sourceEvent.stopPropagation();
                })
                .on('dragend', roiDragEnd);
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
            var zMin = dicomWindow.center - dicomWindow.width / 2;
            var zMax = dicomWindow.center + dicomWindow.width / 2;
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

SIREPO.app.directive('dicomPlot', function(activeSection, appState, frameCache, panelState, plotting, rs4piService, $interval, $rootScope) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
            isSubFrame: '@',
        },
        templateUrl: '/static/html/dicom.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope) {
            $scope.canvasHeight = 0;
            $scope.canvasWidth = 0;
            $scope.margin = {top: 20, left: 10, right: 10, bottom: 0};
            $scope.requestCache = {};
            $scope.rs4piService = rs4piService;

            var canvas, dicomDomain, xAxisScale, xValues, yAxisScale, yValues, zoom;
            var frameScale;
            var inRequest = false;
            var oldDicomWindow = null;
            var selectedDicomPlane = '';
            var planeLinesFeature = activeSection.getActiveSection() == 'source' ? dicomPlaneLinesFeature($scope, rs4piService) : null;
            var doseFeature = activeSection.getActiveSection() == 'source' ? null : imageFeature();
            var dicomFeature = imageFeature();
            var roiFeature = dicomROIFeature($scope, rs4piService, doseFeature ? true : false);

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
                    if (scale > 1 && ! $scope.isLastFrame()) {
                        $scope.advanceFrame(1);
                    }
                    else if (scale < 1 && ! $scope.isFirstFrame()) {
                        $scope.advanceFrame(-1);
                    }
                    else {
                        resetZoom();
                    }
                });
            }

            function clearCache() {
                $scope.requestCache = {};
                dicomFeature.clearColorScale();
            }

            function dicomWindowChanged() {
                return !(oldDicomWindow && appState.deepEquals(oldDicomWindow, appState.models.dicomWindow));
            }

            function getRange(values) {
                return [values[0], values[values.length - 1]];
            }

            function getSize(values) {
                return values[values.length - 1] - values[0];
            }

            function getTargetPlane(axis) {
                if (axis == 'y') {
                    return $scope.isTransversePlane() ? 'c' : 't';
                }
                return selectedDicomPlane == 's' ? 'c' : 's';
            }
            $scope.getTargetPlane = getTargetPlane;

            function isDrawMode() {
                return rs4piService.isEditMode('draw') && $scope.isTransversePlane() && ! $scope.isSubFrame;
            }
            $scope.isDrawMode = isDrawMode;

            function prepareImage() {
                oldDicomWindow = appState.clone(appState.models.dicomWindow);
                dicomFeature.prepareImage(appState.models.dicomWindow);
            }

            function redrawIfChanged(newValue, oldValue) {
                if ($scope.isTransversePlane() && newValue != oldValue) {
                    roiFeature.draw();
                    if (planeLinesFeature) {
                        planeLinesFeature.draw();
                    }
                    resetZoom();
                    updateCursor();
                }
            }

            function refresh() {
                if (! xValues) {
                    return;
                }
                if (rs4piService.isMouseWheelMode('zoom')) {
                    plotting.trimDomain(xAxisScale, getRange(xValues));
                    plotting.trimDomain(yAxisScale, getRange(yValues));
                }
                updateCursor();
                dicomFeature.draw(canvas, getRange(xValues), getRange(yValues));
                if ($scope.isTransversePlane()) {
                    roiFeature.draw();
                    var doseDomain = appState.models.dicomDose.domain;
                    if (doseDomain && doseFeature) {
                        var colorMap = plotting.colorMapFromModel($scope.modelName);
                        var colorScale = d3.scale.linear()
                            .domain(plotting.linearlySpacedArray(0, appState.models.dicomDose.max * 0.8, colorMap.length))
                            .range(colorMap)
                            .clamp(true);
                        doseFeature.setColorScale(colorScale, appState.models[$scope.modelName].doseTransparency);
                        doseFeature.draw(canvas, [doseDomain[0][0], doseDomain[1][0]], [$scope.flipud(doseDomain[0][1]), $scope.flipud(doseDomain[1][1])]);
                    }
                }
                if (planeLinesFeature) {
                    planeLinesFeature.draw();
                }
                resetZoom();
            }

            function resetZoom() {
                zoom = d3.behavior.zoom();
                select('.plot-viewport').call(zoom);
                if (rs4piService.isMouseWheelMode('zoom')) {
                    zoom.x(xAxisScale)
                        .y(yAxisScale)
                        .on('zoom', refresh);
                }
                else if (rs4piService.isMouseWheelMode('advanceFrame')) {
                    zoom.x(frameScale)
                        .on('zoom', advanceFrame);
                }
                if (isDrawMode()) {
                    select('.plot-viewport').on('mousedown.zoom', null);
                }
            }

            function select(selector) {
                var e = d3.select($scope.element);
                return selector ? e.select(selector) : e;
            }
            $scope.select = select;

            function updateCurrentFrame() {
                appState.models.dicomSeries.planes[selectedDicomPlane].frameIndex = frameCache.getCurrentFrame($scope.modelName);
                appState.saveQuietly('dicomSeries');
            }

            function updateCursor() {
                select('.overlay').classed('dicom-roimode-draw', isDrawMode());
                select('.overlay').classed('mouse-zoom', rs4piService.isMouseWheelMode('zoom') && ! isDrawMode());
            }

            function updateSelectedDicomPlane(plane) {
                selectedDicomPlane = plane;
                var planeInfo = appState.models.dicomSeries.planes[selectedDicomPlane];
                frameCache.setCurrentFrame($scope.modelName, planeInfo.frameIndex);
                frameCache.setFrameCount(planeInfo.frameCount, $scope.modelName);
            }

            function updateTargetPlane(axis, v) {
                var values = axis == 'y' ? yValues : xValues;
                var min = values[0];
                var max = values[values.length - 1];
                if (v < min) {
                    v = min;
                }
                else if (v > max) {
                    v = max;
                }
                var series = appState.models.dicomSeries;
                var targetPlane = getTargetPlane(axis);
                var frameCount = series.planes[targetPlane].frameCount;
                var newIndex = Math.floor((v - min) * frameCount / (max - min));
                if (newIndex == frameCount) {
                    newIndex--;
                }
                $scope.$applyAsync(function() {
                    $rootScope.$broadcast('updatePlaneFrameIndex', targetPlane, newIndex);
                });
            }
            $scope.updateTargetPlane = updateTargetPlane;

            $scope.canEditROI = function() {
                return activeSection.getActiveSection() == 'source';
            };

            $scope.destroy = function() {
                zoom.on('zoom', null);
            };

            $scope.dicomTitle = function() {
                return rs4piService.dicomTitle($scope.modelName);
            };

            $scope.yMax = function() {
                return yValues[yValues.length - 1] + yValues[0];
            };

            $scope.flipud = function(v) {
                return $scope.yMax() - v;
            };

            $scope.getDefaultFrame = function() {
                var model = appState.models[$scope.modelName];
                return appState.models.dicomSeries.planes[model.dicomPlane].frameIndex || 0;
            };

            $scope.init = function() {
                select('svg').attr('height', plotting.initialHeight($scope));
                xAxisScale = d3.scale.linear();
                yAxisScale = d3.scale.linear();
                frameScale = d3.scale.linear();
                roiFeature.init(xAxisScale, yAxisScale);
                if (planeLinesFeature) {
                    planeLinesFeature.init(xAxisScale, yAxisScale);
                }
                resetZoom();
                canvas = select('canvas').node();
                dicomFeature.init(xAxisScale, yAxisScale);
                if (doseFeature) {
                    doseFeature.init(xAxisScale, yAxisScale);
                }
            };

            $scope.isTransversePlane = function() {
                return selectedDicomPlane == 't';
            };

            $scope.load = function(json) {
                if (! selectedDicomPlane) {
                    updateSelectedDicomPlane(appState.models[$scope.modelName].dicomPlane);
                }
                updateCurrentFrame();
                if ($scope.isTransversePlane()) {
                    roiFeature.load(json.frameId);
                    if (doseFeature) {
                        frameCache.getFrame('dicomDose', frameCache.getCurrentFrame($scope.modelName), false, function(index, data) {
                            if (frameCache.getCurrentFrame($scope.modelName) == index) {
                                doseFeature.load(data.dose_array);
                                doseFeature.prepareImage({}, true);
                                refresh();
                            }
                        });
                    }
                }
                var preserveZoom = xValues ? true : false;
                dicomDomain = appState.clone(json.domain);
                xValues = plotting.linearlySpacedArray(dicomDomain[0][0], dicomDomain[1][0], json.shape[1]);
                yValues = plotting.linearlySpacedArray(dicomDomain[0][1], dicomDomain[1][1], json.shape[0]);
                if (! preserveZoom) {
                    xAxisScale.domain(getRange(xValues));
                    yAxisScale.domain(getRange(yValues));
                }
                dicomFeature.load(json.pixel_array);
                prepareImage();
                $scope.resize();
                rs4piService.setPlaneCoord(selectedDicomPlane, dicomDomain[0][2]);
            };

            $scope.modelChanged = function() {
                var currentPlane = appState.models[$scope.modelName].dicomPlane;
                if (dicomWindowChanged()) {
                    dicomFeature.clearColorScale();
                }
                if (selectedDicomPlane != currentPlane) {
                    clearCache();
                    if ($scope.isTransversePlane()) {
                        roiFeature.clear();
                    }
                    var oldPlane = selectedDicomPlane;
                    updateSelectedDicomPlane(currentPlane);
                    xValues = null;
                    $scope.requestData();
                    if (! $scope.isSubFrame) {
                        ['dicomAnimation2', 'dicomAnimation3'].forEach(function(m) {
                            if (appState.models[m].dicomPlane == currentPlane) {
                                appState.models[m].dicomPlane = oldPlane;
                                appState.saveChanges(m);
                            }
                        });
                    }
                }
                else {
                    prepareImage();
                    $scope.resize();
                }
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


            $scope.requestData = function() {
                if (! $scope.hasFrames()) {
                    return;
                }
                var index = frameCache.getCurrentFrame($scope.modelName);
                if (index == $scope.prevFrameIndex) {
                    return;
                }
                var cache = $scope.requestCache[index];
                if (cache) {
                    $scope.load(cache);
                    $scope.prevFrameIndex = index;
                    return;
                }
                if (! inRequest) {
                    inRequest = true;
                    frameCache.getFrame($scope.modelName, index, false, function(index, data) {
                        inRequest = false;
                        if ($scope.element) {
                            if (data.error) {
                                panelState.setError($scope.modelName, data.error);
                                return;
                            }
                            $scope.requestCache[index] = data;
                            if (index == frameCache.getCurrentFrame($scope.modelName)) {
                                $scope.load(data);
                                $scope.prevFrameIndex = index;
                            }
                            else {
                                $scope.requestData();
                            }
                        }
                    });
                }
            };

            $scope.$on('refreshDicomPanels', refresh);

            $scope.$on('roiPointsLoaded', function() {
                if (xValues) {
                    if ($scope.isTransversePlane()) {
                        roiFeature.clear();
                    }
                    refresh();
                }
            });

            $scope.$on('updatePlaneFrameIndex', function(evt, plane, frameIndex) {
                if (plane == selectedDicomPlane) {
                    frameCache.setCurrentFrame($scope.modelName, frameIndex);
                    $scope.requestData();
                }
            });

            $scope.$watch('rs4piService.isEditing', redrawIfChanged);
            $scope.$watch('rs4piService.editMode', redrawIfChanged);

        },
        link: function link(scope, element) {
            appState.whenModelsLoaded(scope, function() {
                plotting.linkPlot(scope, element);
            });
        },
    };
});

SIREPO.app.directive('roiConfirmForm', function(appState) {
    return {
        restrict: 'A',
        scope: {},
        template: [
            '<form name="form" data-ng-if="isDirty()" class="panel panel-default" novalidate>',
              '<div class="panel-body">',
                '<div><p>Update the ROI contours?</p></div>',
                '<div class="pull-right" data-buttons="" data-model-name="modelName" data-fields="fields"></div>',
              '</div>',
            '</form>',
        ].join(''),
        controller: function($scope) {
            $scope.modelName = 'dicomEditorState';
            $scope.fields = ['editCounter'];

            $scope.isDirty = function() {
                var info = {};
                info[$scope.modelName] = $scope.fields;
                return appState.areFieldsDirty(info);
            };
        },
    };
});

SIREPO.app.directive('roiTable', function(appState, panelState, rs4piService) {
    return {
        restrict: 'A',
        scope: {
            source: '=controller',
        },
        template: [
            '<button data-ng-click="newRegion()" class="btn btn-info btn-xs pull-right"><span class="glyphicon glyphicon-plus"></span> New Region</button>',
            '<table style="width: 100%;  table-layout: fixed" class="table table-hover">',
              '<colgroup>',
                '<col>',
                '<col style="width: 8ex">',
              '</colgroup>',
              '<thead>',
                '<tr>',
                  '<th>Name</th>',
                  '<th style="white-space: nowrap">Color</th>',
                '</tr>',
              '</thead>',
              '<tbody>',
                '<tr data-ng-show="showROI(roi)" data-ng-click="activate(roi)" data-ng-repeat="roi in roiList track by roi.name" data-ng-class="{warning: isActive(roi)}">',
                  '<td style="padding-left: 1em">{{ roi.name }}</td>',
                  '<td><div style="border: 1px solid #333; background-color: {{ d3Color(roi.color) }}">&nbsp;</div></td>',
                '</tr>',
              '</tbody>',
            '</table>',
        ].join(''),
        controller: function($scope) {
            $scope.rs4piService = rs4piService;
            $scope.roiList = null;

            function loadROIPoints() {
                $scope.roiList = [];
                var rois = rs4piService.getROIPoints();
                Object.keys(rois).forEach(function(roiNumber) {
                    var roi = rois[roiNumber];
                    roi.roiNumber = roiNumber;
                    if (roi.color) {
                        $scope.roiList.push(roi);
                    }
                });
                $scope.roiList.sort(function(a, b) {
                    return a.name.localeCompare(b.name);
                });
            }

            $scope.activate = function(roi) {
                rs4piService.setActiveROI(roi.roiNumber);
                appState.saveChanges('dicomSeries');
            };

            $scope.d3Color = function(c) {
                return window.d3 ? d3.rgb(c[0], c[1], c[2]) : '#000';
            };

            $scope.isActive = function(roi) {
                if (appState.isLoaded()) {
                    return appState.models.dicomSeries.activeRoiNumber == roi.roiNumber;
                }
                return false;
            };

            $scope.newRegion = function() {
                appState.models.dicomROI = appState.setModelDefaults({}, 'dicomROI');
                panelState.showModalEditor('dicomROI');
            };

            $scope.showROI = function(roi) {
                return roi.isVisible || $scope.isActive(roi) || rs4piService.isEditMode('draw');
            };

            $scope.$on('cancelChanges', function(e, name) {
                if (name == 'dicomROI') {
                    appState.removeModel(name);
                }
            });

            $scope.$on('modelChanged', function(e, name) {
                if (name == 'dicomROI') {
                    var m = appState.models.dicomROI;
                    var c = d3.rgb(m.color);
                    if (c && (c.r > 0 || c.g > 0 || c.b > 0)) {
                        var rois = rs4piService.getROIPoints();
                        var id = appState.maxId(
                            $.map(rois, function(v) { return v; }),
                            'roiNumber') + 1;
                        var editedContours = {};
                        editedContours[id] = {
                            contour: {},
                            name: m.name,
                            color: [c.r, c.g, c.b],
                        };
                        rois[id] = editedContours[id];
                        rs4piService.updateROIPoints(editedContours);
                        loadROIPoints();
                        rs4piService.setActiveROI(id);
                        rs4piService.isEditing = true;
                        rs4piService.setEditMode('draw');
                    }
                    appState.removeModel(name);
                }
            });

            $scope.$on('roiPointsLoaded', loadROIPoints);
        },
    };
});

SIREPO.app.directive('roi3d', function(appState, panelState, rs4piService) {
    return {
        restrict: 'A',
        template: [
            '<div style="border: 1px solid #bce8f1; border-radius: 4px; margin: 20px 0;" class="sr-roi-3d">',
            '</div>',
        ].join(''),
        controller: function($scope, $element) {

            var activeRoi = null;
            var initialized = false;
            var fsRenderer = null;
            var actor = null;

            function init() {
                if (initialized) {
                    return;
                }
                initialized = true;
                var rw = $($element);
                rw.on('dblclick', reset);
                rw.height(rw.width() / 1.3);
                fsRenderer = vtk.Rendering.Misc.vtkFullScreenRenderWindow.newInstance(
                    {
                        background: [1, 1, 1, 1],
                        container: rw[0],
                    });
                fsRenderer.getRenderer().getLights()[0].setLightTypeToSceneLight();
            }

            function showActiveRoi() {
                if (actor) {
                    fsRenderer.getRenderer().removeActor(actor);
                }
                var roi = rs4piService.getActiveROIPoints();
                if (! roi) {
                    return;
                }
                var numPts = 0;
                var numLines = 0;
                var z, segment, points;
                for (z in roi.contour) {
                    for (segment = 0; segment < roi.contour[z].length; segment++) {
                        points = roi.contour[z][segment];
                        numPts += points.length / 2;
                        numLines++;
                    }
                }
                var lines = new window.Uint32Array(numPts + (numLines * 2));
                points = new window.Float32Array(numPts * 3);
                var pi = 0;
                var pl = 0;

                for (z in roi.contour) {
                    for (segment = 0; segment < roi.contour[z].length; segment++) {
                        var cPoints = roi.contour[z][segment];
                        var zp = parseFloat(z);
                        lines[pl] = cPoints.length / 2 + 1;
                        pl++;
                        var firstPoint = pi / 3;
                        for (var i = 0; i < cPoints.length; i += 2) {
                            points[pi] = cPoints[i];
                            points[pi + 1] = cPoints[i + 1];
                            points[pi + 2] = zp;
                            lines[pl] = pi / 3;
                            pl++;
                            pi += 3;
                        }
                        lines[pl] = firstPoint;
                        pl++;
                    }
                }
                var pd = vtk.Common.DataModel.vtkPolyData.newInstance();
                pd.getPoints().setData(points, 3);
                pd.getLines().setData(lines);

                /*
                var verts = new window.Uint32Array(numPts + 1);
                pd.getVerts().setData(verts, 1);
                verts[0] = numPts;
                for (var i = 0; i < numPts; i++) {
                    verts[i + 1] = i;
                }
                */

                var mapper = vtk.Rendering.Core.vtkMapper.newInstance();
                actor = vtk.Rendering.Core.vtkActor.newInstance();
                actor.getProperty().setColor(0.3, 0.4, 0.9);
                //actor.getProperty().setEdgeVisibility(true);
                //actor.getProperty().setPointSize(2);
                mapper.setInputData(pd);
                actor.setMapper(mapper);
                fsRenderer.getRenderer().addActor(actor);
                reset();
            }

            function reset() {
                var renderer = fsRenderer.getRenderer();
                var cam = renderer.get().activeCamera;
                cam.setPosition(0, -1, 0.002);
                cam.setFocalPoint(0, 0, 0);
                cam.setViewUp(0, 0, 1);
                renderer.resetCamera();
                cam.zoom(1.3);
                fsRenderer.getRenderWindow().render();
            }

            $scope.$on('$destroy', function() {
                $($element).off();
                fsRenderer.getInteractor().unbindEvents();
                fsRenderer.delete();
            });

            $scope.$on('roiPointsLoaded', function() {
                activeRoi = appState.models.dicomSeries.activeRoiNumber;
                init();
                showActiveRoi();
                $scope.$on('roiActivated', function() {
                    if (activeRoi != appState.models.dicomSeries.activeRoiNumber) {
                        activeRoi = appState.models.dicomSeries.activeRoiNumber;
                        showActiveRoi();
                    }
                });
            });
        }
    };
});
