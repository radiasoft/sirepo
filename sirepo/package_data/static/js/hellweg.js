'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.PLOTTING_SUMMED_LINEOUTS = true;

SIREPO.app.controller('HellwegLatticeController', function (appState, panelState, $scope) {
    var self = this;
    self.appState = appState;
    //self.toolbarItems = ['powerElement', 'cellElement', 'cellsElement', 'driftElement', 'saveElement'];
    self.toolbarItems = ['powerElement', 'cellElement', 'cellsElement', 'driftElement'];

    function isElementModelName(modelName) {
        return modelName.indexOf('Element') >= 0;
    }

    function itemIndex(item) {
        var beamline = appState.models.beamline;
        for (var i = 0; i < beamline.length; i++) {
            if (beamline[i].id == item.id) {
                return i;
            }
        }
        return -1;
    }

    function newItem(modelName) {
        return appState.setModelDefaults({
            type: modelName,
        }, modelName);
    }

    function updateSaveElementFields() {
        var m = appState.models.saveElement;
        if (m) {
            panelState.showField('saveElement', 'particleLimit', m.particleRange == 'count');
            ['particleStart', 'particleEnd'].forEach(function(f) {
                panelState.showField('saveElement', f, m.particleRange == 'range');
            });
        }
    }

    self.deleteItem = function(item) {
        if (! item) {
            return;
        }
        self.selectItem(item);
        $('#hellweg-delete-element-confirmation').modal('show');
    };

    self.deleteSelected = function() {
        if (self.selectedItem) {
            var index = itemIndex(self.selectedItem);
            if (index >= 0) {
                self.selectedItem = null;
                appState.models.beamline.splice(index, 1);
                appState.saveChanges('beamline');
            }
        }
    };

    self.dropItem = function(index, item) {
        if (! item) {
            return;
        }
        if (angular.isObject(item)) {
            var beamline = appState.models.beamline;
            var i = itemIndex(item);
            if (index == i) {
                return;
            }
            item = beamline.splice(i, 1)[0];
            if (i < index) {
                index--;
            }
            beamline.splice(index, 0, item);
            appState.saveChanges('beamline');
            self.selectItem(item);
        }
        else {
            self.selectedIndex = index;
            self.editItem(newItem(item));
        }
    };

    // expects a negative number to move up, positive to move down
    $scope.moveItem = function(direction, item) {
        var d = direction == 0 ? 0 : (direction > 0 ? 1 : -1);
        var currentIndex = itemIndex(item);
        var beamline = appState.models.beamline;
        var newIndex = currentIndex + d;
        if(newIndex >= 0 && newIndex < beamline.length) {
            var tmp = beamline[newIndex];
            beamline[newIndex] = item;
            beamline[currentIndex] = tmp;
            appState.saveChanges('beamline');
        }
    };
    self.copyItem= function(item) {
        var itemCopy = newItem(item.type);
        var iIndex = itemIndex(item);
        for(var prop in item) {
            if(prop != 'id' && prop != '$$hashKey') {
                itemCopy[prop] = item[prop];
            }
        }
        self.selectedIndex = iIndex + 1;
        self.editItem(itemCopy);
    };

    self.dropLast = function(item) {
        self.dropItem(appState.models.beamline.length, item);
    };

    self.editItem = function(item) {
        appState.models[item.type] = item;
        panelState.showModalEditor(item.type);
    };

    self.handleModalShown = function(name) {
        if (name == 'saveElement') {
            updateSaveElementFields();
        }
    };

    self.isSelected = function(item) {
        if (self.selectedItem) {
            return item.id == self.selectedItem.id;
        }
        return false;
    };

    self.itemName = function(item) {
        var modelName = angular.isObject(item) ? item.type : item;
        if (modelName) {
            return appState.viewInfo(modelName).title;
        }
        return '';
    };

    self.itemValues = function(item) {
        return appState.viewInfo(item.type).advanced.map(function(f) {
            return item[f];
        }).join(' ');
    };

    self.selectItem = function(item) {
        self.selectedItem = angular.isObject(item) ? item : null;
    };

    self.selectedItemName = function() {
        if (self.selectedItem) {
            return self.itemName(self.selectedItem) + ' ' + self.itemValues(self.selectedItem);
        }
        return '';
    };

    $scope.$on('cancelChanges', function(e, name) {
        if (isElementModelName(name)) {
            appState.removeModel(name);
            appState.cancelChanges('beamline');
        }
    });

    $scope.$on('modelChanged', function(e, name) {
        if (isElementModelName(name)) {
            if (! appState.models[name].id) {
                appState.models[name].id = appState.maxId(appState.models.beamline) + 1;
                appState.models.beamline.splice(self.selectedIndex, 0, appState.models[name]);
                self.selectedItem = appState.models[name];
            }
            appState.removeModel(name);
            appState.saveChanges('beamline');
        }
    });

    appState.watchModelFields($scope, ['saveElement.particleRange'], updateSaveElementFields);
});

SIREPO.app.controller('HellwegSourceController', function (appState, panelState, $scope) {
    var self = this;

    function isActiveField(model, field) {
        var fieldClass = '.model-' + model + '-' + field;
        return $(fieldClass).find('input').is(':focus');
    }

    function updateAllFields() {
        updateBeamFields();
        updateSolenoidFields();
    }

    function updateBeamFields() {
        var beam = appState.models.beam;
        if (beam.transversalDistribution == 'sph2d') {
            updateCurvature();
        }
        var isDistribution = beam.beamDefinition == 'transverse_longitude';
        panelState.showField('beam', 'spaceChargeCore', beam.spaceCharge == 'coulomb' || beam.spaceCharge == 'elliptic');
        panelState.showTab('beam', 2, isDistribution && beam.transversalDistribution == 'twiss4d');
        panelState.showTab('beam', 3, isDistribution && beam.transversalDistribution == 'sph2d');
        panelState.showTab('beam', 4, isDistribution && beam.transversalDistribution == 'ell2d');
        panelState.showTab('beam', 5, isDistribution && beam.longitudinalDistribution == 'norm2d');
        panelState.showTab('beam', 6, beam.beamDefinition == 'cst_pid' || (isDistribution && beam.longitudinalDistribution == 'file1d'));
        panelState.showField('energyPhaseDistribution', 'energyDeviation', beam.longitudinalDistribution == 'norm2d' && appState.models.energyPhaseDistribution.distributionType == 'gaussian');
        panelState.showField('energyPhaseDistribution', 'phaseDeviation', (beam.longitudinalDistribution == 'norm2d' || beam.longitudinalDistribution == 'file1d') && appState.models.energyPhaseDistribution.distributionType == 'gaussian');
        panelState.showField('beam', 'cstCompress', beam.beamDefinition == 'cst_pit');
        ['transversalDistribution', 'longitudinalDistribution'].forEach(function(f) {
            panelState.showField('beam', f, isDistribution);
        });
        panelState.showField('beam', 'transversalFile2d', beam.transversalDistribution == 'file2d');
        panelState.showField('beam', 'transversalFile4d', beam.transversalDistribution == 'file4d');
        panelState.showField('beam', 'longitudinalFile1d', beam.longitudinalDistribution == 'file1d');
        panelState.showField('beam', 'longitudinalFile2d', beam.longitudinalDistribution == 'file2d');
        panelState.showField('beam', 'cstFile', ! isDistribution);
    }

    function updateCurvature() {
        var dist = appState.models.sphericalDistribution;
        if (isActiveField('sphericalDistribution', 'curvatureFactor')) {
            if (dist.curvatureFactor !== undefined) {
                dist.curvature = dist.curvatureFactor > 0
                    ? 'concave'
                    : (dist.curvatureFactor < 0
                       ? 'convex'
                       : 'flat');
            }
        }
        else {
            if (dist.curvature == 'concave') {
                if (dist.curvatureFactor === 0) {
                    dist.curvatureFactor = 1;
                }
                else {
                    dist.curvatureFactor = Math.abs(dist.curvatureFactor);
                }
            }
            else if (dist.curvature == 'convex') {
                if (dist.curvatureFactor === 0) {
                    dist.curvatureFactor = -1;
                }
                else {
                    dist.curvatureFactor = - Math.abs(dist.curvatureFactor);
                }
            }
            else {
                dist.curvatureFactor = 0;
            }
        }
    }

    function updateSolenoidFields() {
        var solenoid = appState.models.solenoid;
        ['fieldStrength', 'length', 'fringeRegion', 'z0'].forEach(function(f) {
            panelState.showField('solenoid', f, solenoid.sourceDefinition == 'values');
        });
        panelState.showField('solenoid', 'solenoidFile', solenoid.sourceDefinition == 'file');
    }

    self.handleModalShown = function() {
        updateAllFields();
    };

    appState.watchModelFields($scope, ['beam.transversalDistribution', 'beam.longitudinalDistribution', 'beam.spaceCharge', 'beam.beamDefinition', 'sphericalDistribution.curvature', 'sphericalDistribution.curvatureFactor', 'energyPhaseDistribution.distributionType'], updateBeamFields);
    appState.watchModelFields($scope, ['solenoid.sourceDefinition'], updateSolenoidFields);
    appState.whenModelsLoaded($scope, updateAllFields);
});

SIREPO.app.controller('HellwegVisualizationController', function (appState, frameCache, panelState, persistentSimulation, plotRangeService, $scope, $rootScope) {
    var self = this;
    self.panelState = panelState;

    function handleStatus(data) {
        if (data.startTime && ! data.error) {
            plotRangeService.computeFieldRanges(self, 'beamAnimation', data.percentComplete);
            ['beamAnimation', 'beamHistogramAnimation', 'particleAnimation', 'parameterAnimation'].forEach(function(modelName) {
                appState.models[modelName].startTime = data.startTime;
                appState.saveQuietly(modelName);
            });
            $rootScope.$broadcast('animation.summaryData', data.summaryData);
            if (data.frameCount) {
                frameCache.setFrameCount(1, 'particleAnimation');
                frameCache.setFrameCount(1, 'parameterAnimation');
            }
        }
        frameCache.setFrameCount(data.frameCount);
    }

    self.handleModalShown = function(name) {
        if (name == 'beamAnimation') {
            plotRangeService.processPlotRange(self, name);
        }
    };

    appState.whenModelsLoaded($scope, function() {
        appState.watchModelFields($scope, ['beamAnimation.plotRangeType'], function() {
            plotRangeService.processPlotRange(self, 'beamAnimation');
        });
    });

    self.simState = persistentSimulation.initSimulationState($scope, 'animation', handleStatus, {
        beamAnimation: [SIREPO.ANIMATION_ARGS_VERSION + '2', 'reportType', 'histogramBins', 'plotRangeType', 'horizontalSize', 'horizontalOffset', 'verticalSize', 'verticalOffset', 'isRunning', 'startTime'],
        beamHistogramAnimation: [SIREPO.ANIMATION_ARGS_VERSION + '1', 'reportType', 'histogramBins', 'startTime'],
        particleAnimation: [SIREPO.ANIMATION_ARGS_VERSION + '1', 'reportType', 'renderCount', 'startTime'],
        parameterAnimation: [SIREPO.ANIMATION_ARGS_VERSION + '1', 'reportType', 'startTime'],
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
            '<div data-import-dialog=""></div>',
        ].join(''),
    };
});

SIREPO.app.directive('appHeader', function(appState) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appHeader',
        },
        template: [
            '<div data-app-header-brand="nav" data-app-url="/old#/rslinac"></div>',
            '<div data-app-header-left="nav"></div>',
            '<div data-app-header-right="nav">',
              '<app-header-right-sim-loaded>',
                '<div data-sim-sections="">',
                    '<li class="sim-section" data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-flash"></span> Source</a></li>',
                    '<li class="sim-section" data-ng-class="{active: nav.isActive(\'lattice\')}"><a href data-ng-click="nav.openSection(\'lattice\')"><span class="glyphicon glyphicon-option-horizontal"></span> Lattice</a></li>',
                    '<li class="sim-section" data-ng-if="showVisualizationTab()" data-ng-class="{active: nav.isActive(\'visualization\')}"><a href data-ng-click="nav.openSection(\'visualization\')"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>',
                '</div>',
              '</app-header-right-sim-loaded>',
              '<app-settings>',
              //  '<div>App-specific setting item</div>',
              '</app-settings>',
              '<app-header-right-sim-list>',
                '<ul class="nav navbar-nav sr-navbar-right">',
                  '<li><a href data-ng-click="nav.showImportModal()"><span class="glyphicon glyphicon-cloud-upload"></span> Import</a></li>',
                '</ul>',
              '</app-header-right-sim-list>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.hasLattice = function() {
                return appState.isLoaded();
            };
            $scope.showVisualizationTab = function() {
                if (appState.isLoaded()) {
                    return appState.models.beamline.length;
                }
                return false;
            };
        },
    };
});

SIREPO.app.directive('summaryTable', function() {
    return {
        restrict: 'A',
        scope: {
            modelName: '@summaryTable',
        },
        template: [
            '<div class="col-sm-12">',
              '<div class="lead" data-ng-if="summaryRows">Results</div>',
                '<table>',
                '<tr data-ng-repeat="item in summaryRows">',
                  '<td data-ng-if="item.length == 1"><br /><strong>{{ item[0] }}</strong></td>',
                  '<td data-ng-if="item.length > 1">{{ item[0] }}:</td>',
                  '<td>&nbsp;</td>',
                  '<td>{{ item[1] }}</td>',
                '</tr>',
              '</table>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            function parseSummaryRows(summaryText) {
                var text = summaryText.replace(/^(\n|.)*RESULTS\n+==+/, '').replace(/==+/, '');
                var label = null;
                $scope.summaryRows = [];
                text.split(/\n+/).forEach(function(line) {
                    line.split(/\s*=\s*/).forEach(function(v) {
                        if (label) {
                            $scope.summaryRows.push([label, v]);
                            label = null;
                        }
                        else if (v.indexOf(':') >= 0) {
                            $scope.summaryRows.push([v]);
                        }
                        else {
                            label = v;
                        }
                    });
                });
            }

            function updateSummaryInfo(e, summaryText) {
                if (summaryText) {
                    parseSummaryRows(summaryText);
                }
                else {
                    $scope.summaryRows = null;
                }
            }
            $scope.$on($scope.modelName + '.summaryData', updateSummaryInfo);
        }
    };
});
