'use strict';

app.directive('basicEditorPanel', function(appState, panelState) {
    return {
        scope: {
            modelName: '@',
        },
        template: [
            '<div class="panel panel-info">',
              '<div class="panel-heading" data-panel-heading="{{ panelTitle }}" data-model-name="{{ modelName }}" data-editor-id="{{ editorId }}"></div>',
              '<div class="panel-body cssFade" data-ng-hide="panelState.isHidden(modelName)">',
                '<form name="form" class="form-horizontal" novalidate>',
                  '<div class="form-group form-group-sm" data-ng-repeat="f in basicFields">',
                    '<div data-field-editor="f" data-model-name="modelName" data-model="appState.models[modelName]" class="model-{{modelName}}-{{f}}"></div>',
                  '</div>',
                  '<div data-buttons="" data-model-name="modelName"></div>',
                '</form>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.appState = appState;
            $scope.panelState = panelState;
            $scope.basicFields = appState.viewInfo($scope.modelName).basic;
            $scope.panelTitle = appState.viewInfo($scope.modelName).title;
            $scope.editorId = 'srw-' + $scope.modelName + '-editor';
            $scope.isStringField = function(f) {
                return typeof(f) == 'string' ? true : false;
            };
        },
    };
});

app.directive('buttons', function(appState) {
    return {
        scope: {
            modelName: '=',
            modalId: '@',
        },
        template: [
            '<div class="col-sm-6 pull-right cssFade" data-ng-show="form.$dirty">',
            '<button data-ng-click="saveChanges()" class="btn btn-primary" data-ng-class="{\'disabled\': ! form.$valid}">Save Changes</button> ',
              '<button data-ng-click="cancelChanges()" class="btn btn-default">Cancel</button>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.form = $scope.$parent.form;
            function changeDone() {
                $scope.form.$setPristine();
                if ($scope.modalId)
                    $('#' + $scope.modalId).modal('hide');
            }
            $scope.$on($scope.modelName + '.changed', function() {
                changeDone();
            });
            $scope.saveChanges = function() {
                if ($scope.form.$valid && $scope.modelName)
                    appState.saveChanges($scope.modelName);
            };
            $scope.cancelChanges = function() {
                appState.cancelChanges($scope.modelName);
                changeDone();
            };
        }
    };
});

app.directive('confirmationModal', function() {
    return {
        restrict: 'A',
        scope: {
            id: '@',
            title: '@',
            text: '@',
            okText: '@',
            okClicked: '&',
        },
        template: [
            '<div class="modal fade" id="{{ id }}" tabindex="-1" role="dialog">',
              '<div class="modal-dialog modal-lg">',
                '<div class="modal-content">',
                  '<div class="modal-header bg-warning">',
                    '<button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>',
                    '<span class="lead modal-title text-info">{{ title }}</span>',
                  '</div>',
                  '<div class="modal-body">',
                    '<div class="container-fluid">',
                      '<div class="row">',
                        '<div class="col-sm-6 col-sm-offset-3">',
                          '<p>{{ text }}</p>',
                        '</div>',
                      '</div>',
                      '<div class="row">',
                        '<div class="col-sm-6 pull-right">',
                          '<button data-dismiss="modal" data-ng-click="okClicked()" class="btn btn-default">{{ okText }}</button>',
                          ' <button data-dismiss="modal" class="btn btn-default">Cancel</button>',
                        '</div>',
                      '</div>',
                    '</div>',
                  '</div>',
                '</div>',
              '</div>',
            '</div>',
        ].join(''),
    };
});

app.directive('fieldEditor', function(appState, requestSender) {
    return {
        restirct: 'A',
        scope: {
            fieldEditor: '=',
            model: '=',
            modelName: '=',
            customLabel: '=',
            labelSize: "@",
            numberSize: "@",
            isReadOnly: "=",
        },
        template: [
            '<label data-ng-hide="customLabel" class="col-sm-{{ labelSize || \'5\' }} control-label">{{ info[0] }}</label>',
            '<label data-ng-show="customLabel" class="col-sm-{{ labelSize || \'5\' }} control-label">{{ customLabel }}</label>',
            '<div data-ng-switch="info[1]">',
              '<div data-ng-switch-when="BeamList" class="col-sm-5">',
                '<div class="dropdown">',
                  '<button class="btn btn-default dropdown-toggle form-control" type="button" data-toggle="dropdown">{{ model[fieldEditor] }} <span class="caret"></span></button>',
                  '<ul class="dropdown-menu">',
                    '<li class="dropdown-header">Predefined Electron Beams</li>',
                    '<li data-ng-repeat="item in requestSender.beams track by item.name">',
                      '<a href data-ng-click="selectBeam(item)">{{ item.name }}</a>',
                    '</li>',
                    '<li class="divider"></li>',
                    '<li class="dropdown-header">User Defined Electron Beams</li>',
                    '<li data-ng-repeat="item in appState.models.electronBeams track by item.name">',
                      '<a href data-ng-click="selectBeam(item)">{{ item.name }}</a>',
                    '</li>',
                    '<li><a href data-ng-click="newUserDefinedBeam()"><span class="glyphicon glyphicon-plus"></span> New</a></li>',
                  '</ul>',
                '</div>',
              '</div>',
              '<div data-ng-switch-when="Float" class="col-sm-{{ numberSize || \'3\' }}">',
                '<input string-to-number="" data-ng-model="model[fieldEditor]" class="form-control" style="text-align: right" required data-ng-readonly="isReadOnly">',
              '</div>',
              '<div data-ng-switch-when="Integer" class="col-sm-{{ numberSize || \'3\' }}">',
                '<input string-to-number="integer" data-ng-model="model[fieldEditor]" class="form-control" style="text-align: right" required data-ng-readonly="isReadOnly">',
              '</div>',
              '<div data-ng-switch-when="MirrorFile" class="col-sm-5">',
                '<div class="btn-group" role="group">',
                  '<div class="btn-group" role="group">',
                    '<button type="button" class="btn btn-default dropdown-toggle" data-toggle="dropdown">{{ model[fieldEditor] || "No Mirror Error" }} <span class="caret"></span></button>',
                    '<ul class="dropdown-menu">',
                      '<li data-ng-repeat="item in mirrorList()"><a href data-ng-click="selectMirror(item)">{{ item }}</a></li>',
                      '<li class="divider"></li>',
                      '<li data-ng-hide="requireMirrorErrors()"><a href data-ng-click="selectMirror(null)">No Mirror Error</a></li>',
                      '<li  data-ng-hide="requireMirrorErrors()" class="divider"></li>',
                      '<li><a href data-ng-click="showMirrorFileUpload()"><span class="glyphicon glyphicon-plus"></span> New</a></li>',
                    '</ul>',
                  '</div>',
                '</div> ',
                '<div data-ng-if="model[fieldEditor]" class="btn-group" role="group">',
                  '<button type="button" title="View Graph" class="btn btn-default" data-ng-click="showMirrorReport()"><span class="glyphicon glyphicon-eye-open"></span></button>',
                  '<a data-ng-href="{{ downloadMirrorFileUrl() }}" type="button" title="Download" class="btn btn-default""><span class="glyphicon glyphicon-cloud-download"></a>',
                '</div>',
              '</div>',
              '<div data-ng-switch-when="String" class="col-sm-5">',
                '<input data-ng-model="model[fieldEditor]" class="form-control" required data-ng-readonly="isReadOnly">',
              '</div>',
              //TODO(pjm): need a way to specify whether a field is option/required
              '<div data-ng-switch-when="OptionalString" class="col-sm-5">',
                '<input data-ng-model="model[fieldEditor]" class="form-control" data-ng-readonly="isReadOnly">',
              '</div>',
              // assume it is an enum
              '<div data-ng-switch-default class="col-sm-5">',
                '<select number-to-string class="form-control" data-ng-model="model[fieldEditor]" data-ng-options="item[0] as item[1] for item in enum[info[1]]"></select>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.appState = appState;
            $scope.requestSender = requestSender;

            var match = $scope.fieldEditor.match(/(.*?)\.(.*)/);
            if (match) {
                $scope.modelName = match[1];
                $scope.fieldEditor = match[2];
                if ($scope.$parent.fullModelName)
                    $scope.$parent.fullModelName = $scope.modelName;
            }

            function findParentAttribute(name) {
                var scope = $scope;
                while (scope && ! scope[name]) {
                    scope = scope.$parent;
                }
                return scope[name];
            }

            // field def: [label, type]
            $scope.info = appState.modelInfo($scope.modelName)[$scope.fieldEditor];
            $scope.downloadMirrorFileUrl = function() {
                if ($scope.model) {
                    return requestSender.formatUrl('downloadFile', {
                        '<simulation_id>': appState.models.simulation.simulationId,
                        '<simulation_type>': APP_SCHEMA.simulationType,
                        '<filename>': $scope.model[$scope.fieldEditor],
                    });
                }
                return '';
            };
            $scope.requireMirrorErrors = function() {
                return $scope.modelName == 'mirror';
            };
            $scope.selectBeam = function(item) {
                $scope.model = item;
                $scope.model[$scope.fieldEditor] = item.name;
                $scope.$parent.form.$setDirty();
            };
            $scope.selectMirror = function(item) {
                $scope.model[$scope.fieldEditor] = item;
                $scope.$parent.form.$setDirty();
            };
            $scope.showMirrorFileUpload = function() {
                findParentAttribute('beamline').showMirrorFileUpload();
            };
            $scope.showMirrorReport = function() {
                findParentAttribute('beamline').showMirrorReport($scope.model);
            };
            $scope.emptyList = [];
            $scope.mirrorList = function() {
                if (requestSender.mirrors)
                    return requestSender.mirrors;
                if (! appState.isLoaded())
                    return $scope.emptyList;
                requestSender.getAuxiliaryData(
                    'mirrors',
                    requestSender.formatUrl('listFiles', {
                        '<simulation_id>': appState.models.simulation.simulationId,
                        '<simulation_type>': APP_SCHEMA.simulationType,
                    }));
                return $scope.emptyList;
            };
            $scope.newUserDefinedBeam = function() {
                // copy the current beam, rename and show editor
                appState.addNewElectronBeam();
                $('#srw-electronBeam-editor').modal('show');
            };
        },
        link: function link(scope) {
            scope.enum = APP_SCHEMA.enum;
            if (scope.info && scope.info[1] == 'BeamList')
                requestSender.getAuxiliaryData('beams', '/static/json/beams.json');
        },
    };
});

app.directive('columnEditor', function(appState) {
    return {
        scope: {
            columnFields: '=',
            modelName: '=',
            fullModelName: '=',
            isReadOnly: '=',
        },
        template: [
            '<div class="row">',
              '<div class="col-sm-6" data-ng-repeat="col in columnFields">',
                '<div class="lead text-center">{{ col[0] }}</div>',
                '<div class="form-group form-group-sm" data-ng-repeat="f in col[1]">',
                  '<div data-field-editor="f" data-label-size="7" data-number-size="5" data-custom-label="customLabel(col[0], f)" data-model-name="modelName" data-model="appState.models[fullModelName]" data-is-read-only="isReadOnly" class="model-{{modelName}}-{{f}}"></div>',
                '</div>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.appState = appState;
            $scope.customLabel = function(heading, f) {
                var info = appState.modelInfo($scope.modelName)[f];
                var label = info[0];
                heading = heading.replace(/ .*/, '');
                label = label.replace(heading, '');
                return label;
            };
        },
        link: function(scope, element) {
        },
    };
});

app.directive('modalEditor', function(appState) {
    return {
        scope: {
            modalEditor: '@',
            // optional, for watch reports
            itemId: '@',
            isReadOnly: '=',
            parentController: '=',
        },
        template: [
            '<div class="modal fade" id="{{ editorId }}" tabindex="-1" role="dialog">',
              '<div class="modal-dialog modal-lg">',
                '<div class="modal-content">',
                  '<div class="modal-header bg-info">',
  	            '<button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>',
	            '<span class="lead modal-title text-info">{{ modalTitle }}</span>',
	          '</div>',
                  '<div class="modal-body">',
                    '<div class="container-fluid">',
                      '<div class="row">',
                        '<form name="form" class="form-horizontal" novalidate>',
                          '<div data-ng-repeat="f in advancedFields">',
                            '<div class="form-group form-group-sm model-{{modalEditor}}-{{f}}" data-ng-if="isStringField(f)" data-field-editor="f" data-model-name="modelName" data-model="appState.models[fullModelName]" data-is-read-only="isReadOnly"></div>',
                            '<div data-ng-if="! isStringField(f)" data-column-editor="" data-column-fields="f" data-model-name="modelName" data-full-model-name="fullModelName" data-is-read-only="isReadOnly"></div>',
                          '</div>',
                          '<div data-buttons="" data-model-name="fullModelName" data-modal-id="{{ editorId }}"></div>',
                        '</form>',
                      '</div>',
                    '</div>',
                  '</div>',
                '</div>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.appState = appState;
            var viewInfo = appState.viewInfo($scope.modalEditor);
            $scope.advancedFields = viewInfo.advanced;
            //TODO(pjm): cobbled-together to allow a view to refer to a model by name, ex. SRW simulationGrid view
            $scope.modelName = viewInfo.model || $scope.modalEditor;
            $scope.fullModelName = $scope.modelName + ($scope.itemId || '');
            $scope.editorId = 'srw-' + (viewInfo.model ? $scope.modalEditor : $scope.fullModelName) + '-editor';
            $scope.isStringField = function(f) {
                return typeof(f) == 'string' ? true : false;
            };
            $scope.modalTitle = appState.getReportTitle(viewInfo.model ? $scope.modalEditor : $scope.fullModelName);
        },
        link: function(scope, element) {
            $(element).on('shown.bs.modal', function() {
                if (! scope.isReadOnly)
                    $('#' + scope.editorId + ' .form-control').first().select();
                if (scope.parentController && scope.parentController.handleModalShown)
                    scope.parentController.handleModalShown(scope.modelName, $(element));
            });
            $(element).on('hidden.bs.modal', function(e) {
                // ensure that a dismissed modal doesn't keep changes
                // ok processing will have already saved data before the modal is hidden
                appState.cancelChanges(scope.fullModelName);
                scope.$apply();
            });
            scope.$on('$destroy', function() {
                // release modal data to prevent memory leak
                $(element).off();
                $('.modal').modal('hide').removeData('bs.modal');
            });
        },
    };
});

app.directive('numberToString', function() {
    return {
        restrict: 'A',
        require: 'ngModel',
        link: function(scope, element, attrs, ngModel) {
            ngModel.$parsers.push(function(value) {
                if (ngModel.$isEmpty(value))
                    return null;
                return '' + value;
            });
            ngModel.$formatters.push(function(value) {
                if (ngModel.$isEmpty(value))
                    return value;
                return value.toString();
            });
        }
    };
});

app.directive('panelHeading', function(panelState, appState, requestSender, frameCache, $http) {
    return {
        restrict: 'A',
        scope: {
            panelHeading: '@',
            modelName: '@',
            editorId: '@',
            allowFullScreen: '@',
        },
        template: [
            '<span class="lead">{{ panelHeading }}</span>',
            '<div class="srw-panel-options pull-right">',
              '<a href data-ng-show="showAdvancedEditor" data-ng-click="showEditor()" title="Edit"><span class="lead glyphicon glyphicon-pencil"></span></a> ',
              '<div data-ng-if="allowFullScreen" data-ng-show="hasData()" class="dropdown" style="display: inline-block">',
                '<a href class="dropdown-toggle" data-toggle="dropdown" title="Download"> <span class="lead glyphicon glyphicon-cloud-download" style="margin-bottom: 0"></span></a> ',
                '<ul class="dropdown-menu dropdown-menu-right">',
                  '<li class="dropdown-header">Download Report</li>',
                  '<li><a href data-ng-click="downloadImage(480)">PNG - Small</a></li>',
                  '<li><a href data-ng-click="downloadImage(720)">PNG - Medium</a></li>',
                  '<li><a href data-ng-click="downloadImage(1080)">PNG - Large</a></li>',
                  '<li role="separator" class="divider"></li>',
                  '<li><a data-ng-href="{{ dataFileURL() }}" target="_blank">Raw Data File</a></li>',
                '</ul>',
              '</div>',
              //'<a href data-ng-show="allowFullScreen" title="Full screen"><span class="lead glyphicon glyphicon-fullscreen"></span></a> ',
              '<a href data-ng-click="panelState.toggleHidden(modelName)" data-ng-hide="panelState.isHidden(modelName)" title="Hide"><span class="lead glyphicon glyphicon-triangle-top"></span></a> ',
              '<a href data-ng-click="panelState.toggleHidden(modelName)" data-ng-show="panelState.isHidden(modelName)" title="Show"><span class="lead glyphicon glyphicon-triangle-bottom"></span></a>',
            '</div>',
        ].join(''),
        controller: function($scope) {

            function downloadPlot(svg, height, plot3dCanvas) {
                var canvas = document.createElement('canvas');
                var context = canvas.getContext("2d");
                var scale = height / parseInt(svg.getAttribute('height'));
                canvas.width = parseInt(svg.getAttribute('width')) * scale;
                canvas.height = parseInt(svg.getAttribute('height')) * scale;
                context.fillStyle = '#FFFFFF';
                context.fillRect(0, 0, canvas.width, canvas.height);
                context.fillStyle = '#000000';

                if (plot3dCanvas) {
                    var el = $(plot3dCanvas);
                    context.drawImage(
                        plot3dCanvas, pxToInteger(el.css('left')) * scale, pxToInteger(el.css('top')) * scale,
                        pxToInteger(el.css('width')) * scale, pxToInteger(el.css('height')) * scale);
                }
                var svgString = svg.parentNode.innerHTML;
                context.drawSvg(svgString, 0, 0, canvas.width, canvas.height);
                canvas.toBlob(function(blob) {
                    var fileName = $scope.panelHeading.replace(/(\_|\W|\s)+/g, '-') + '.png'
                    saveAs(blob, fileName);
                });
            }

            function pxToInteger(value) {
                value = value.replace(/px/, '');
                return parseInt(value);
            }

            $scope.panelState = panelState;
            $scope.dataFileURL = function() {
                if (appState.isLoaded()) {
                    return requestSender.formatUrl('downloadDataFile', {
                        '<simulation_id>': appState.models.simulation.simulationId,
                        '<simulation_type>': APP_SCHEMA.simulationType,
                        '<model_or_frame>':  appState.isAnimationModelName($scope.modelName)
                            ? frameCache.getCurrentFrame($scope.modelName)
                            : $scope.modelName,
                    });
                }
                return '';
            },
            $scope.downloadImage = function(height) {
                var svg = $scope.reportPanel.find('svg')[0];
                if (! svg)
                    return;
                var plot3dCanvas = $scope.reportPanel.find('canvas')[0];
                // embed sirepo.css style within SVG for first download, css file is cached by browser
                $http.get('/static/css/sirepo.css?' + SIREPO_APP_VERSION)
                    .success(function(data) {
                        if (svg.firstChild.nodeName != 'STYLE') {
                            var css = document.createElement('style');
                            css.type = 'text/css';
                            css.appendChild(document.createTextNode(data));
                            svg.insertBefore(css, svg.firstChild);
                        }
                        downloadPlot(svg, height, plot3dCanvas);
                    });
            };
            $scope.hasData = function() {
                if (appState.isLoaded()) {
                    if (appState.isAnimationModelName($scope.modelName))
                        return frameCache.frameCount > 0;
                    return ! panelState.isLoading($scope.modelName);
                }
                return false;
            };
            $scope.showEditor = function() {
                $('#' + $scope.editorId).modal('show');
            };
            $scope.showAdvancedEditor = appState.viewInfo($scope.modelName)
                && appState.viewInfo($scope.modelName).advanced.length == 0 ? false : true;
        },
        link: function(scope, element) {
            scope.reportPanel = element.next();
        },
    };
});

app.directive('reportContent', function(panelState) {
    return {
        restrict: 'A',
        scope: {
            reportContent: '@',
            fullModelName: '@',
        },
        template: [
            '<div data-ng-class="{\'srw-panel-loading\': panelState.isLoading(fullModelName), \'srw-panel-error\': panelState.getError(fullModelName)}" class="panel-body cssFade" data-ng-hide="panelState.isHidden(fullModelName)">',
              '<div data-ng-show="panelState.isLoading(fullModelName)" class="lead srw-panel-wait"><span class="glyphicon glyphicon-hourglass"></span> Simulating...</div>',
              '<div data-ng-show="panelState.getError(fullModelName)" class="lead srw-panel-wait"><span class="glyphicon glyphicon-exclamation-sign"></span> {{ panelState.getError(fullModelName) }}</div>',
              '<div data-ng-switch="reportContent" class="{{ panelState.getError(fullModelName) ? \'srw-hide-report\' : \'\' }}">',
                '<div data-ng-switch-when="2d" data-plot2d="" class="srw-plot" data-model-name="{{ fullModelName }}"></div>',
                '<div data-ng-switch-when="3d" data-plot3d="" class="srw-plot" data-model-name="{{ fullModelName }}"></div>',
                '<div data-ng-switch-when="heatmap" data-heatmap="" class="srw-plot" data-model-name="{{ fullModelName }}"></div>',
              '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            $scope.panelState = panelState;
        },
    };
});

app.directive('reportPanel', function(appState, panelState) {
    return {
        restrict: 'A',
        scope: {
            reportPanel: '@',
            modelName: '@',
            // optional, for watch reports
            itemId: '@',
        },
        template: [
            '<div class="panel panel-info">',
              '<div class="panel-heading" data-panel-heading="{{ appState.getReportTitle(fullModelName) }}" data-model-name="{{ fullModelName }}" data-editor-id="{{ editorId }}" data-allow-full-screen="1"></div>',
              '<div data-report-content="{{ reportPanel }}" data-full-model-name="{{ fullModelName }}"></div>',
            '</div>',
        ].join(''),
        controller: function($scope) {
            var itemId = $scope.itemId ? $scope.itemId : '';
            $scope.appState = appState;
            $scope.panelState = panelState;
            $scope.fullModelName = $scope.modelName + itemId;
            $scope.editorId = 'srw-' + $scope.fullModelName + '-editor';
        },
    };
});

app.directive('appHeaderLeft', function() {
    return {
        restrict: 'A',
        scope: {
            nav: '=appHeaderLeft',
        },
        template: [
            '<ul class="nav navbar-nav">',
              '<li data-ng-class="{active: nav.isActive(\'simulations\')}"><a href data-ng-click="nav.openSection(\'simulations\')"><span class="glyphicon glyphicon-th-list"></span> Simulations</a></li>',
            '</ul>',
            '<div class="navbar-text"><a href data-target="#srw-simulation-editor" data-toggle="modal"><span ng-if="nav.sectionTitle()" class="glyphicon glyphicon-pencil"></span> <strong data-ng-bind="nav.sectionTitle()"></strong></a></div>',
        ].join(''),
    };
});

app.directive('stringToNumber', function() {
    var NUMBER_REGEXP = /^\s*(\-|\+)?(\d+|(\d*(\.\d*)))([eE][+-]?\d+)?\s*$/;
    return {
        restrict: 'A',
        require: 'ngModel',
        scope: {
            numberType: '@stringToNumber',
        },
        link: function(scope, element, attrs, ngModel) {
            ngModel.$parsers.push(function(value) {
                if (ngModel.$isEmpty(value))
                    return null;
                if (NUMBER_REGEXP.test(value)) {
                    if (scope.numberType == 'integer') {
                        var v = parseInt(value);
                        if (v != value) {
                            ngModel.$setViewValue(v);
                            ngModel.$render();
                        }
                        return v;
                    }
                    return parseFloat(value);
                }
                return undefined;
            });
            ngModel.$formatters.push(function(value) {
                if (ngModel.$isEmpty(value))
                    return value;
                return value.toString();
            });
        }
    };
});

app.directive('fileModel', ['$parse', function ($parse) {
    return {
        restrict: 'A',
        link: function(scope, element, attrs) {
            var model = $parse(attrs.fileModel);
            var modelSetter = model.assign;
            element.bind('change', function(){
                scope.$apply(function(){
                    modelSetter(scope, element[0].files[0]);
                });
            });
        }
    };
}]);

app.service('fileUpload', ['$http', function ($http) {
    this.uploadFileToUrl = function(file, uploadUrl, callback){
        var fd = new FormData();
        fd.append('file', file);
        $http.post(uploadUrl, fd, {
            transformRequest: angular.identity,
            headers: {'Content-Type': undefined}
        })
            .success(callback)
            .error(function(){
                //TODO(pjm): error handling
                console.log('file upload failed');
            });
    }
}]);
