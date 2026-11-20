'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(() => {
    SIREPO.SINGLE_FRAME_ANIMATION = ['plotAnimation'];
    SIREPO.FILE_UPLOAD_TYPE = {
        'plotAnimation-experimentalFile': '.csv,.xlsx',
    };
    SIREPO.appFieldEditors += `
        <div data-ng-switch-when="ParameterArray">
          <div data-parameter-array="" data-model="model" data-field="field"></div>
        </div>
    `;
});

SIREPO.app.factory('tmap8Service', function(appDataService, appState, $rootScope) {
    const self = {};
    // display state of the parameter table, shared by tmap8ParameterToolbar
    // and parameterArray, which builds the groups
    self.parameterFilter = {
        changedOnly: false,
        text: '',
    };
    self.parameterGroups = [];
    // simulations come from Import, not New Simulation, but may be copied
    appDataService.canCopy = () => true;

    self.clearParameterFilter = () => {
        self.parameterFilter.changedOnly = false;
        self.parameterFilter.text = '';
    };

    self.computeModel = () => 'animation';

    // ex. "Normal" -> "normalDistribution", matching the model names in tmap8-schema.json
    self.distributionModelName = (distributionType) => {
        return distributionType.charAt(0).toLowerCase() + distributionType.slice(1) + 'Distribution';
    };

    // from the saved state, so the Monte Carlo fields appear once an uncertainty is saved
    self.hasUncertainty = () => {
        return ((appState.applicationState() || {}).rpnVariables || []).some(
            (v) => v.uncertaintyDistribution,
        );
    };

    // the Simulation Status editor only has the Monte Carlo fields
    self.isEditorShown = (viewName) => {
        return viewName !== 'simulationStatus' || self.hasUncertainty();
    };

    self.isParameterFiltering = () => {
        return Boolean((self.parameterFilter.text || '').trim() || self.parameterFilter.changedOnly);
    };

    // a rpnVariable's uncertainty: the default fields of its distribution's model
    self.uncertaintyDefaults = (distributionType) => {
        const res = {};
        if (distributionType) {
            appState.setModelDefaults(res, self.distributionModelName(distributionType));
        }
        return res;
    };

    // the service outlives a simulation, so don't carry a filter to the next one
    $rootScope.$on('modelsLoaded', self.clearParameterFilter);
    appState.setAppService(self);
    return self;
});

SIREPO.app.directive('appFooter', function() {
    return {
        restrict: 'A',
        scope: {
            nav: '=appFooter',
        },
        template: `
            <div data-common-footer="nav"></div>
            <div data-tmap8-import-dialog=""></div>
        `,
    };
});

SIREPO.app.directive('appHeader', function(tmap8Service) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appHeader',
        },
        template: `
            <div data-app-header-brand="nav"></div>
            <div data-app-header-left="nav"></div>
            <div data-app-header-right="nav">
              <app-settings></app-settings>
              <app-header-right-sim-list>
                <ul class="nav navbar-nav sr-navbar-right">
                  <li>
                    <a href data-ng-click="nav.showImportModal()">
                      <span class="glyphicon glyphicon-cloud-upload"></span> Import
                    </a>
                  </li>
                </ul>
              </app-header-right-sim-list>
            </div>
        `,
    };
});

SIREPO.app.controller('VizController', function(appState, frameCache, panelState, persistentSimulation, $scope) {
    const self = this;
    self.simScope = $scope;
    self.errorMessage = '';
    self.reportTitle = SIREPO.APP_SCHEMA.view.plotAnimation.title;

    const valueListFields = (modelName) => {
        const r = [];
        for (const [f, d] of Object.entries(SIREPO.APP_SCHEMA.model[modelName])) {
            if (d[1] === 'ValueList') {
                r.push(f);
            }
        }
        return r;
    };

    const initModel = (info) => {
        panelState.setError(info.modelKey, null);
        if (! appState.models[info.modelKey]) {
            appState.models[info.modelKey] = {};
        }
        const m = appState.setModelDefaults(appState.models[info.modelKey], info.modelKey);
        m.valueList = {};
        for (const f of valueListFields(info.modelKey)) {
            m.valueList[f] = info.columns;
        }
        const cols = info.columns.filter((c) => c !== 'None');
        if (! m.x) {
            m.x = cols[0] || 'None';
        }
        if (! m.y1) {
            m.y1 = cols[1] || cols[0] || 'None';
        }
        appState.saveQuietly(info.modelKey);
        self.reportTitle = info.name;
    };

    self.simHandleStatus = (resp) => {
        self.errorMessage = resp.error;
        if (resp.reports && resp.reports.length) {
            resp.reports.forEach((info) => {
                initModel(info);
                //frameCache.setFrameCount(info.frameCount, info.modelKey);
            });
        }
        frameCache.setFrameCount(resp.frameCount || 0);
    };

    self.startSimulation = function() {
        // simulationSettings has the Monte Carlo samples and seed
        self.simState.saveAndRunSimulation(['rpnVariables', 'simulationSettings']);
    };

    self.simState = persistentSimulation.initSimulationState(self);
});

SIREPO.app.directive('rpnUncertainty', function(tmap8Service) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        // one row: the distribution and its parameters, each with its label above
        template: `
            <div class="sr-tmap8-uncertainty">
              <div class="sr-tmap8-uncertainty-field">
                <div class="form-group" data-field-editor="'uncertaintyDistribution'" data-field-size="12"
                  data-label-size="12" data-model-name="'rpnVariable'" data-model="model"></div>
              </div>
              <div class="sr-tmap8-uncertainty-field" data-ng-repeat="v in viewFields track by v.track">
                <div class="form-group" data-field-editor="v.field" data-field-size="12" data-label-size="12"
                  data-model-name="modelName" data-model="model[field]"></div>
              </div>
            </div>
        `,
        controller: function($scope) {

            function setView() {
                const t = $scope.model.uncertaintyDistribution;
                if (t) {
                    $scope.modelName = tmap8Service.distributionModelName(t);
                    $scope.viewFields = SIREPO.APP_SCHEMA.view[$scope.modelName].advanced
                        .map((f) => {
                            return {
                                field: f,
                                track: $scope.modelName + f,
                            };
                        });
                }
                else {
                    $scope.viewFields = null;
                }
            }

            $scope.$watch('model.uncertaintyDistribution', (newValue, oldValue) => {
                if (! $scope.model) {
                    return;
                }
                if (newValue !== oldValue) {
                    $scope.model[$scope.field] = tmap8Service.uncertaintyDefaults(newValue);
                }
                setView();
            });
        },
    };
});

SIREPO.app.directive('parameterArray', function(appState, mathRendering, rpnService, tmap8Service, $sce) {
    // with more parameters than this, groups start collapsed
    const OPEN_ALL_MAX = 30;

    return {
        restrict: 'A',
        // the panel's form, to show Save/Cancel after a reset or uncertainty toggle
        require: '^^form',
        scope: {
            model: '=',
            field: '=',
        },
        template: `
            <div data-ng-if="appState.models.rpnVariables">
              <div data-ng-if="isFiltering()" class="text-muted sr-tmap8-filter-count">
                {{ visibleCount() }} of {{ appState.models.rpnVariables.length }} parameters
              </div>
              <table class="table table-condensed sr-tmap8-params">
                <colgroup>
                  <col style="width: 30%">
                  <col style="width: 40%">
                  <col>
                  <!-- fits the reset and uncertainty buttons; table-layout: fixed doesn't
                    size a column to its content, so a smaller width lets them overflow
                    the cell, where they aren't fully clickable -->
                  <col style="width: 4.5em">
                </colgroup>
                <thead>
                  <tr>
                    <th>Parameter Name</th>
                    <th>Value</th>
                    <th> </th>
                    <th> </th>
                  </tr>
                </thead>
                <tbody data-ng-repeat="g in groups" data-ng-show="showGroup(g)">
                  <tr data-ng-if="g.name" class="sr-tmap8-group" data-ng-click="g.open = ! g.open">
                    <th colspan="4" title="{{ g.name }}">
                      <span class="glyphicon" data-ng-class="isFiltering() || g.open ? 'glyphicon-chevron-down' : 'glyphicon-chevron-right'"></span>
                      {{ g.name }} <span class="text-muted">({{ g.vars.length }})</span>
                    </th>
                  </tr>
                  <tr data-ng-repeat-start="v in g.vars" data-ng-show="showRow(g, v)">
                    <td class="sr-tmap8-param-name">
                      <strong><span data-ng-repeat="p in nameParts[v.name] track by $index">{{ p }}<wbr></span></strong>
                      <span data-ng-if="v.unitMath" class="sr-tmap8-unit" data-ng-bind-html="mathHTML(v.unitMath)"></span>
                      <span data-ng-if="v.unit && ! v.unitMath" class="sr-tmap8-unit">{{ v.unit }}</span>
                      <br data-ng-if="v.comment" />
                      <em data-ng-if="v.commentMath"># <span data-ng-bind-html="mathHTML(v.commentMath)"></span></em>
                      <em data-ng-if="v.comment && ! v.commentMath"># {{ v.comment }}</em>
                    </td>
                    <td>
                      <div class="row" data-field-editor="'value'" data-field-size="12" data-label-size="0" data-model-name="'rpnVariable'" data-model="v"></div>
                    </td>
                    <td>
                      <div class="col-sm-12" data-rpn-static="" data-model="v" data-field="'value'"></div>
                    </td>
                    <td>
                      <div class="sr-tmap8-button-cell">
                        <button data-ng-if="isValueChanged(v)" class="btn btn-default btn-xs" type="button"
                          title="Reset to default: {{ v.defaultValue }}" data-ng-click="resetValue(v)">
                          <span class="glyphicon glyphicon-repeat"></span>
                        </button>
                        <button class="btn btn-xs sr-tmap8-uncertainty-button" type="button"
                          data-ng-class="v.uncertaintyDistribution ? 'btn-primary active' : 'btn-default'"
                          data-ng-attr-aria-pressed="{{ v.uncertaintyDistribution ? 'true' : 'false' }}"
                          data-ng-click="toggleUncertainty(v)" data-ng-attr-title="{{ v.uncertaintyDistribution ? 'Remove uncertainty' : 'Add uncertainty' }}">&plusmn;</button>
                      </div>
                    </td>
                  </tr>
                  <tr data-ng-repeat-end="" data-ng-if="v.uncertaintyDistribution" data-ng-show="showRow(g, v)" class="sr-tmap8-uncertainty-row">
                    <td></td>
                    <td colspan="3">
                      <div data-rpn-uncertainty="" data-model="v" data-field="'uncertainty'"></div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
        `,
        controller: function($scope) {
            $scope.appState = appState;
            $scope.groups = [];
            // parameter name split after each "_", so long names can wrap
            $scope.nameParts = {};
            // mathHTML() by text, stable across digests
            const trustedMath = {};

            const buildGroups = () => {
                const vars = appState.models.rpnVariables || [];
                const byName = {};
                const res = [];
                $scope.nameParts = {};
                for (const v of vars) {
                    const n = v.group || '';
                    if (! (n in byName)) {
                        byName[n] = {
                            name: n,
                            open: true,
                            vars: [],
                        };
                        res.push(byName[n]);
                    }
                    byName[n].vars.push(v);
                    $scope.nameParts[v.name] = v.name.split('_').map(
                        (p, i, a) => i < a.length - 1 ? p + '_' : p,
                    );
                }
                // parameters without a heading first, otherwise in file order
                res.sort((a, b) => (a.name ? 1 : 0) - (b.name ? 1 : 0));
                const isMany = vars.length > OPEN_ALL_MAX;
                for (const g of res) {
                    g.open = ! isMany || g.vars.some(isChanged);
                }
                $scope.groups = res;
                tmap8Service.parameterGroups = res;
            };

            const isChanged = (v) => {
                return Boolean(v.uncertaintyDistribution) || $scope.isValueChanged(v);
            };

            const matches = (g, v) => {
                const f = tmap8Service.parameterFilter;
                if (f.changedOnly && ! isChanged(v)) {
                    return false;
                }
                const t = (f.text || '').trim().toLowerCase();
                if (! t) {
                    return true;
                }
                return [v.name, v.comment || '', g.name].some(
                    (s) => s.toLowerCase().includes(t),
                );
            };

            $scope.isFiltering = tmap8Service.isParameterFiltering;

            $scope.isValueChanged = (v) => {
                return String(v.value) !== String(v.defaultValue);
            };

            // math prepared by the server (commentMath, unitMath); not
            // data-text-with-math, which would $interpolate the comment text
            $scope.mathHTML = (text) => {
                if (! (text in trustedMath)) {
                    trustedMath[text] = $sce.trustAsHtml(mathRendering.mathAsHTML(text));
                }
                return trustedMath[text];
            };

            $scope.resetValue = (v) => {
                v.value = v.defaultValue;
                // a programmatic change skips rpnValue's parsers, which update the cache
                if (typeof v.value === 'number') {
                    rpnService.recomputeCache(v.name, v.value);
                }
                else {
                    rpnService.computeRpnValue(v.value, (value, err) => {
                        if (! err) {
                            rpnService.recomputeCache(v.name, value);
                        }
                    });
                }
                setDirty();
            };

            $scope.showGroup = (g) => {
                return ! $scope.isFiltering() || g.vars.some((v) => matches(g, v));
            };

            $scope.showRow = (g, v) => {
                if ($scope.isFiltering()) {
                    return matches(g, v);
                }
                return ! g.name || g.open;
            };

            const setDirty = () => {
                // rpnVariables isn't a field of the panel's view, so it isn't
                // seen by appState.areFieldsDirty()
                if ($scope.form) {
                    $scope.form.$setDirty();
                }
            };

            $scope.toggleUncertainty = (v) => {
                if (v.uncertaintyDistribution) {
                    delete v.uncertaintyDistribution;
                    delete v.uncertainty;
                }
                else {
                    v.uncertaintyDistribution = SIREPO.APP_SCHEMA.enum.Distribution[0][0];
                    v.uncertainty = tmap8Service.uncertaintyDefaults(v.uncertaintyDistribution);
                }
                setDirty();
            };

            $scope.visibleCount = () => {
                let res = 0;
                for (const g of $scope.groups) {
                    res += g.vars.filter((v) => matches(g, v)).length;
                }
                return res;
            };

            $scope.$on('simulationSettings.changed', () => {
                if (appState.models.rpnVariables) {
                    appState.saveQuietly('rpnVariables');
                }
            });

            // rebuilt when the parameters are replaced, e.g. a model load or cancel
            $scope.$watch(() => appState.models.rpnVariables, buildGroups);
        },
        link: function(scope, element, attrs, form) {
            scope.form = form;
        },
    };
});

SIREPO.app.directive('tmap8ImportDialog', function(fileManager, fileUpload, requestSender) {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <div class="modal fade" data-backdrop="static" id="simulation-import" tabindex="-1" role="dialog">
              <div class="modal-dialog modal-lg">
                <div class="modal-content">
                  <div class="modal-header bg-info">
                    <button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>
                    <span class="lead modal-title text-info">Import TMAP8 File</span>
                  </div>
                  <div class="modal-body">
                    <div class="container-fluid">
                      <form class="form-horizontal" name="importForm">
                        <div data-ng-show="inputFile && missingFiles" class="form-group">
                          <label class="col-xs-4 control-label">Importing file</label>
                          <div class="col-xs-8">
                            <p class="form-control-static">{{ inputFile.name }}</p>
                          </div>
                        </div>
                        <div data-ng-show="! missingFiles" class="form-group">
                          <label>Select TMAP8 Input File (.i) or ${SIREPO.APP_SCHEMA.productInfo.shortName} Export (.zip)</label>
                          <input id="sr-tmap8-file-import" type="file" data-file-model="inputFile" accept=".i,.zip" />
                        </div>
                        <div data-ng-show="missingFiles">
                          <p>Please upload the files below which are referenced by the TMAP8 input file.</p>
                          <div class="form-group" data-ng-repeat="item in missingFiles">
                            <div class="col-sm-11 col-sm-offset-1">
                              <span data-ng-if="item.file && isCorrectFile(item)" class="glyphicon glyphicon-ok"></span>
                              <span data-ng-if="item.file && ! isCorrectFile(item)" class="glyphicon glyphicon-flag text-danger"></span>
                              <span data-ng-if="item.file && ! isCorrectFile(item)" class="text-danger">Filename: <b>{{ item.file.name }}</b> does not match, expected: </span>
                              <label>{{ item.filename }}</label>
                              <input type="file" data-file-model="item.file" />
                            </div>
                          </div>
                        </div>
                        <div class="text-warning"><strong>{{ fileUploadError }}</strong></div>
                        <div data-ng-if="isUploading" class="col-sm-6 pull-right">Please Wait...</div>
                        <div class="clearfix"></div>
                        <div class="col-sm-6 pull-right">
                          <button data-ng-click="importFile()" class="btn btn-primary" data-ng-disabled="! canImport()">Import File{{ missingFiles.length > 1 ? 's' : '' }}</button>
                          <button data-dismiss="modal" class="btn btn-default" data-ng-disabled="isUploading">Cancel</button>
                        </div>
                      </form>
                    </div>
                  </div>
                </div>
              </div>
            </div>
        `,
        controller: function($element, $scope) {
            // basename: base64 contents of the included and data files collected so far
            let files = {};

            const readFile = (file) => {
                return new Promise((resolve, reject) => {
                    const r = new FileReader();
                    // a data url is "data:<type>;base64,<contents>"
                    r.onload = () => resolve(r.result.substring(r.result.indexOf(',') + 1));
                    r.onerror = () => reject(r.error);
                    r.readAsDataURL(file);
                });
            };

            const upload = () => {
                const args = {
                    folder: fileManager.getActiveFolderPath(),
                };
                if (Object.keys(files).length) {
                    args.arguments = JSON.stringify({files});
                }
                fileUpload.uploadFileToUrl(
                    $scope.inputFile,
                    args,
                    requestSender.formatUrl(
                        'importFile',
                        {
                            '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                        },
                    ),
                    (data) => {
                        $scope.isUploading = false;
                        if (data.error) {
                            $scope.fileUploadError = data.error;
                            return;
                        }
                        if (data.importState === 'missingFiles') {
                            // included files may include more files
                            $scope.missingFiles = data.missingFiles.map((f) => {
                                return {
                                    filename: f,
                                    file: null,
                                };
                            });
                            return;
                        }
                        $('#simulation-import').modal('hide');
                        requestSender.localRedirectHome(data.models.simulation.simulationId);
                    },
                );
            };

            $scope.canImport = () => {
                if ($scope.isUploading || ! $scope.inputFile) {
                    return false;
                }
                return ! $scope.missingFiles || $scope.missingFiles.every($scope.isCorrectFile);
            };

            $scope.importFile = () => {
                $scope.isUploading = true;
                $scope.fileUploadError = '';
                if (! $scope.missingFiles) {
                    upload();
                    return;
                }
                Promise.all($scope.missingFiles.map((item) => readFile(item.file))).then(
                    (contents) => {
                        $scope.$applyAsync(() => {
                            $scope.missingFiles.forEach((item, i) => {
                                files[item.filename] = contents[i];
                            });
                            upload();
                        });
                    },
                    (error) => {
                        $scope.$applyAsync(() => {
                            $scope.isUploading = false;
                            $scope.fileUploadError = 'Failed to read file: ' + error;
                        });
                    },
                );
            };

            $scope.isCorrectFile = (item) => {
                return item.file && item.file.name === item.filename;
            };

            $scope.resetState = () => {
                files = {};
                $scope.fileUploadError = '';
                $scope.inputFile = null;
                $scope.isUploading = false;
                $scope.missingFiles = null;
            };

            $scope.resetState();
        },
        link: function(scope, element) {
            $(element).on('show.bs.modal', () => {
                $('#sr-tmap8-file-import').val(null);
                scope.$applyAsync(scope.resetState);
            });
            scope.$on('$destroy', () => $(element).off());
        },
    };
});

// Filter and expand/collapse controls for parameterArray, outside the panel's
// form so they don't show its Save/Cancel
SIREPO.app.directive('tmap8ParameterToolbar', function(appState, panelState, tmap8Service) {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <div data-ng-if="isShown()" class="sr-tmap8-param-toolbar">
              <div class="input-group input-group-sm sr-tmap8-filter">
                <input class="form-control" type="text" placeholder="Filter parameters"
                  data-ng-model="tmap8Service.parameterFilter.text" data-ng-model-options="{debounce: 200}" />
                <span class="input-group-btn">
                  <button class="btn btn-default" type="button" title="Clear filter"
                    data-ng-click="tmap8Service.clearParameterFilter()" data-ng-disabled="! isFiltering()">&times;</button>
                </span>
              </div>
              <button class="btn btn-sm sr-tmap8-changed-only" type="button"
                data-ng-class="tmap8Service.parameterFilter.changedOnly ? 'btn-primary active' : 'btn-default'"
                data-ng-attr-aria-pressed="{{ tmap8Service.parameterFilter.changedOnly }}"
                title="Show only parameters changed from their default or with uncertainty"
                data-ng-click="tmap8Service.parameterFilter.changedOnly = ! tmap8Service.parameterFilter.changedOnly">Changed only</button>
              <!-- disabled, not hidden, while filtering, so the toolbar doesn't shift -->
              <div data-ng-if="tmap8Service.parameterGroups.length > 1" class="btn-group btn-group-sm sr-tmap8-group-buttons">
                <button class="btn btn-default" type="button" title="Expand all groups" data-ng-disabled="isFiltering()" data-ng-click="setAllOpen(true)">
                  <span class="glyphicon glyphicon-collapse-down"></span>
                </button>
                <button class="btn btn-default" type="button" title="Collapse all groups" data-ng-disabled="isFiltering()" data-ng-click="setAllOpen(false)">
                  <span class="glyphicon glyphicon-collapse-up"></span>
                </button>
              </div>
            </div>
        `,
        controller: function($scope) {
            $scope.tmap8Service = tmap8Service;
            $scope.isFiltering = tmap8Service.isParameterFiltering;

            $scope.isShown = () => {
                return Boolean(appState.models.rpnVariables?.length)
                    && ! panelState.isHidden('simulationSettings');
            };

            $scope.setAllOpen = (isOpen) => {
                for (const g of tmap8Service.parameterGroups) {
                    g.open = isOpen;
                }
            };
        },
    };
});

SIREPO.viewLogic('plotAnimationView', function(appState, panelState, $scope) {
    function updateExperimentalFields() {
        panelState.showFields('plotAnimation', [
            [
                'experimentalLabel', 'experimentalPosition', 'experimentalXOffset',
                'experimentalXScale', 'experimentalYOffset', 'experimentalYScale',
            ], !! appState.models.plotAnimation.experimentalFile,
        ]);
    }

    $scope.whenSelected = updateExperimentalFields;
    $scope.watchFields = [
        ['plotAnimation.experimentalFile'], updateExperimentalFields,
    ];
});

SIREPO.viewLogic('simulationStatusView', function(panelState, tmap8Service, $scope) {
    // the samples and seed are only used by a Monte Carlo run
    const updateMonteCarloFields = () => {
        panelState.showFields('simulationSettings', [
            ['numSamples', 'seed'], tmap8Service.hasUncertainty(),
        ]);
    };

    $scope.whenSelected = updateMonteCarloFields;
    $scope.$watch(tmap8Service.hasUncertainty, updateMonteCarloFields);
});
