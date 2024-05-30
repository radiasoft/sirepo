'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.appDefaultSimulationValues.simulation.beamAxis = 'z';
    SIREPO.appDefaultSimulationValues.simulation.coordinateSystem = 'standard';
    SIREPO.appDefaultSimulationValues.simulation.enableKickMaps = '0';
    SIREPO.appDefaultSimulationValues.simulation.heightAxis = 'y';
    SIREPO.appDefaultSimulationValues.simulation.magnetType = 'freehand';
    SIREPO.appDefaultSimulationValues.simulation.dipoleType = 'dipoleBasic';
    SIREPO.appDefaultSimulationValues.simulation.undulatorType = 'undulatorBasic';
    SIREPO.appDefaultSimulationValues.simulation.freehandType = 'freehand';
    SIREPO.SINGLE_FRAME_ANIMATION = ['solverAnimation', 'optimizerAnimation'];
    SIREPO.appFieldEditors += `
        <div data-ng-switch-when="BevelEdge" class="col-sm-12">
          <div data-bevel-edge="" data-model="model" data-model-name="modelName" data-field="field"></div>
        </div>
        <div data-ng-switch-when="FieldPaths" class="col-sm-7">
          <select class="form-control" data-ng-model="model.fieldPath" data-ng-options="p as p.name for p in appState.models.fieldPaths.paths track by p.name"></select>
        </div>
        <div data-ng-switch-when="FloatArray" class="col-sm-7">
            <div data-num-array="" data-model="model" data-field-name="field" data-field="model[field]" data-info="info" data-num-type="Float"></div>
        </div>
        <div data-ng-switch-when="Group" class="col-sm-12">
            <div data-group-editor="" data-field="model[field]" data-model="model"></div>
        </div>
        <div data-ng-switch-when="HBFile" data-ng-class="fieldClass">
            <div data-file-field="field" data-form="form" data-model="model" data-model-name="modelName"  data-selection-required="false" data-empty-selection-text="No File Selected" data-file-type="h-m"></div>
        </div>
        <div data-ng-switch-when="IntArray" class="col-sm-7">
            <div data-num-array="" data-model="model" data-field-name="field" data-field="model[field]" data-info="info" data-num-type="Int"></div>
        </div>
        <div data-ng-switch-when="ObjectType" class="col-sm-7">
            <div data-shape-selector="" data-model-name="modelName" data-model="model" data-field="model[field]" data-field-class="fieldClass" data-parent-controller="parentController" data-view-name="viewName" data-object="viewLogic.getBaseObject()"></div>
        </div>
        <div data-ng-switch-when="ObjectOptimizerField" class="col-sm-12">
          <div data-object-optimizer-field="" data-model-name="modelName" data-model="model" data-field="model[field]"></div>
        </div>
        <div data-ng-switch-when="MaterialFormula" data-ng-class="fieldClass">
            <div data-material-formula="" data-model="model" data-field-name="field" data-field="model[field]" data-info="info"></div>
        </div>
        <div data-ng-switch-when="MaterialType" data-ng-class="fieldClass">
          <select number-to-string class="form-control" data-ng-model="model[field]" data-ng-options="item[0] as item[1] for item in enum[info[1]]"></select>
            <div class="sr-input-warning">
            </div>
        </div>
        <div data-ng-switch-when="ModelArrayTable" class="col-sm-12">
          <div data-model-array-table="" data-field="model[field]" data-field-name="field" data-model="model" data-model-name="modelName" data-item-class="Modification" data-models="info[4]"></div>
        </div>
        <div data-ng-switch-when="PtsFile" data-ng-class="fieldClass">
          <input id="radia-pts-file-import" type="file" data-file-model="model[field]" accept=".dat,.txt,.csv"/>
        </div>
        <div data-ng-switch-when="Points" data-ng-class="fieldClass">
          <div data-points-table="" data-field="model[field]" data-model="model"></div>
        </div>
        <div data-ng-switch-when="ScriptableField">
            <div data-scriptable-field="" data-model-name="modelName" data-model="model" data-field-name="field" data-field="model[field]" data-info="info"></div>
        </div>
        <div data-ng-switch-when="ScriptableArray" class="col-sm-7">
            <div data-scriptable-array="" data-model-name="modelName" data-model="model" data-field-name="field" data-field="model[field]" data-info="info"></div>
        </div>
        <div data-ng-switch-when="ShapeButton" class="col-sm-7">
          <div data-shape-button="" data-model-name="modelName" data-field-class="fieldClass"></div>
        </div>
        <div data-ng-switch-when="TerminationTable" class="col-sm-12">
          <div data-termination-table="" data-field="model[field]" data-field-name="field" data-model="model" data-model-name="modelName"></div>
        </div>
    `;
    SIREPO.appReportTypes = `
        <div data-ng-switch-when="fieldIntegrals" data-field-integral-table="" data-model-name="{{ modelKey }}" class="sr-plot sr-screenshot"></div>
    `;
});

SIREPO.app.factory('radiaOptimizationService', function(appState, radiaService, radiaVariableService) {
    let self = {};

    //TODO(mvk): other types such as FloatArray
    const OPTIMIZABLE_TYPES = ['Float', 'ScriptableField'];

    self.optimizableObjects = (types=OPTIMIZABLE_TYPES) =>
        radiaVariableService.addressableObjects(OPTIMIZABLE_TYPES);

    return self;
});

SIREPO.app.factory('radiaService', function(appState, fileUpload, geometry, panelState, requestSender, rpnService, validationService) {
    let self = {};

    const POST_SIM_REPORTS = ['electronTrajectoryReport', 'fieldIntegralReport', 'kickMapReport',];

    self.computeModel = analysisModel => analysisModel;

    appState.setAppService(self);

    self.axes = ['x', 'y', 'z'];
    self.isEditing = false;
    self.objBounds = null;
    self.pointFieldTypes = appState.enumVals('FieldType').slice(1);

    self.selectedObject = null;

    self.alphaDelegate = function() {
        const m = 'magnetDisplay';
        const f = 'alpha';
        const d = panelState.getFieldDelegate(m, f);
        d.range = function() {
            return {
                min: appState.fieldProperties(m, f).min,
                max: appState.fieldProperties(m, f).max,
                step: 0.01
            };
        };
        d.readout = function() {
            return appState.modelInfo(m)[f][SIREPO.INFO_INDEX_LABEL];
        };
        d.update = function() {};
        d.watchFields = [];
        return d;
    };

    self.axisIndex = axis => SIREPO.GEOMETRY.GeometryUtils.BASIS().indexOf(axis);

    self.buildShapePoints = (o, callback, errorCallback) => {
        // once the points file has been read, no need to fetch it again
        if (o.type === 'extrudedPoints' && (o.points || []).length) {
            callback(o);
            return;
        }
        requestSender.sendStatelessCompute(
            appState,
            callback,
            {
                method: 'build_shape_points',
                args: {
                    object: o,
                    rpnVariables: appState.models.rpnVariables,
                }
            },
            {
                onError: res => {
                    if (errorCallback) {
                        errorCallback(res);
                    }
                }
            }
        );
    };

    self.calcWidthAxis = (depthAxis, heightAxis) => {
        return self.axes.filter((a) => {
            return a !== depthAxis && a !== heightAxis;
        })[0];
    };

    self.centerExtrudedPoints = o =>  {
        const idx = [self.axisIndex(o.widthAxis), self.axisIndex(o.heightAxis)];
        if (o.isNew) {
            o.isNew = false;
            if (o.preservePointsOnImport === "1") {
                o.preservePointsOnImport = "0";
                o.points = o.referencePoints.slice();
                idx.forEach(i => {
                    o.center[i] = SIREPO.UTILS.minForIndex(o.referencePoints, i) + o.size[i] / 2.0;
                });
                return;
            }
        }
        o.points = o.referencePoints.map(
            p => p.map(
                (x, i) => p[i] + o.center[idx[i]] - (
                    SIREPO.UTILS.minForIndex(o.referencePoints, i) + o.size[idx[i]] / 2.0
                )
            )
        );
    };

    self.deleteObject = o => {
        const i = appState.models.geometryReport.objects.indexOf(o);
        if (i < 0) {
            return;
        }
        // if object was a group, ungroup its members
        for (const mId of (o.members || [])) {
            self.getObject(mId).groupId = '';
        }
        // if object was in a group, remove from that group
        removeFromGroup(o);
        appState.models.geometryReport.objects.splice(i, 1);
    };

    self.getAxisIndices = function() {
        const sim = appState.models.simulation;
        return {
            width: self.axes.indexOf(sim.widthAxis),
            height: self.axes.indexOf(sim.heightAxis),
            depth: self.axes.indexOf(sim.beamAxis)
        };
    };

    self.getGeomDirections = function (depthAxis, heightAxis) {
        return {
            depth: geometry.basisVectors[depthAxis],
            height: geometry.basisVectors[heightAxis],
            width: geometry.basisVectors[self.calcWidthAxis(depthAxis, heightAxis)],
        };
    };

    self.getObject = function(id, array=appState.models.geometryReport.objects) {
        return self.getObjectByAttribute('id', id, array);
    };

    self.getObjectByAttribute = function(attr, val, array) {
        let objs = array || [];
        for (const o of objs) {
            if (o[attr] === val) {
                return o;
            }
        }
        return null;
    };

    self.getObjectByName = function(name, array=appState.models.geometryReport.objects) {
        return self.getObjectByAttribute('name', name, array);
    };

    self.getObjects = function() {
        return appState.models.geometryReport.objects || [];
    };

    self.getSelectedObject = function() {
        return self.selectedObject;
    };

    self.isLinearPath = p => p.type === 'axisPath' || p.type === 'linePath';

    // In order to associate VTK objects in the viewer with Radia objects, we need a mapping between them.
    // When we create objects on the client side we don't yet know the Radia id so we cannot use it directly.
    // Instead, generate an id here and map it when the Radia object is created. A random string is good enough
    self.generateId = () => SIREPO.UTILS.randomString(16);

    self.hasPaths = (types=[]) => {
        return (appState.applicationState().fieldPaths.paths || [])
            .filter(x => types.length ? types.includes(x.type) : true)
            .length;
    };

    self.isGroup = o => o.members !== undefined;

    self.saveGeometry = function(doGenerate, isQuiet, callback) {
        appState.models.geometryReport.lastModified = Date.now();
        appState.models.geometryReport.doGenerate = doGenerate ? '1': '0';
        if (isQuiet) {
            appState.saveQuietly('geometryReport');
        }
        else {
            appState.saveChanges('geometryReport', callback);
        }
        self.syncReports();
    };

    self.setWidthAxis = function() {
        const sim = appState.models.simulation;
        sim.widthAxis = self.calcWidthAxis(sim.beamAxis, sim.heightAxis);
    };

    self.setSelectedObject = function(o) {
        self.selectedObject = o;
    };

    self.scaledArray = function (arr=SIREPO.ZERO_ARR) {
        return arr.map(x => SIREPO.APP_SCHEMA.constants.objectScale * x);
    };

    self.syncReports = () => {
        const now = Date.now();
        const t0 = appState.models.geometryReport.lastModified;
        const t = now > t0 ? now : t0;
        POST_SIM_REPORTS.forEach(r => {
            appState.models[r].lastModified = t;
        });
        appState.saveChanges(POST_SIM_REPORTS);
    };

    self.updateCylinder = o => {
        const k = SIREPO.GEOMETRY.GeometryUtils.axisIndex(o.extrusionAxis);
        for (const j of [0, 1]) {
            o.size[(k + j + 1) % 3] = 2.0 * o.radius;
        }
    };

    self.updateExtruded = (o, callback) => {
        o.layoutShape = 'polygon';
        o.widthAxis = SIREPO.GEOMETRY.GeometryUtils.nextAxis(o.extrusionAxis);
        o.heightAxis = SIREPO.GEOMETRY.GeometryUtils.nextAxis(o.widthAxis);
        if (o.referencePoints && o.referencePoints.length) {
            self.updateExtrudedSize(o);
            self.centerExtrudedPoints(o);
            if (callback) {
                callback(o);
            }
            return;
        }
        self.buildShapePoints(o, d => {
            o.points = d.points;
            if (callback) {
                callback(d);
            }
        });
    };

    self.updateExtrudedSize = o => {
        [o.widthAxis, o.heightAxis].forEach((dim, i) => {
            const p = o.referencePoints.map(x => x[i]);
            o.size[self.axisIndex(dim)] = Math.abs(SIREPO.UTILS.arrayMax(p) - SIREPO.UTILS.arrayMin(p));
        });
    };

    // update models so that editors see the correct values
    // for now assign the entire object
    self.updateModelAndSuperClasses = (modelName, model) => {
        const s = [modelName, ...appState.superClasses(modelName)];
        for (const c of s) {
            appState.models[c] = model;
        }
        return s;
    };

    self.updateObject = o => (self[`update${SIREPO.UTILS.capitalize(o.type)}`] || (() => {}))(o);

    self.updateRaceTrack = o => {
        const s = [0, 0, 0];
        const i = SIREPO.GEOMETRY.GeometryUtils.axisIndex(o.axis);
        s[i] = o.height;
        const d = 2.0 * o.radii[1];
        for (const j of [0, 1]) {
            const k = (i + j + 1) % 3;
            const side = o.sides[j];

            // handle scripted sides - note do not use parseFloat!
            if (isNaN(Number(side))) {
                s[k] = side + ` + ${d}`;
            }
            else {
                s[k] = side + d;
            }
        }
        o.size = s;
    };

    self.upload = function(inputFile) {
        upload(inputFile);
    };

    self.validateMagnetization = (magnetization, material) => {
        const mag = Math.hypot(...(magnetization || SIREPO.ZERO_ARR));
        validationService.validateField(
            'geomObject',
            'material',
            'select',
            ! SIREPO.APP_SCHEMA.constants.anisotropicMaterials.includes(material) || mag > 0,
            'Anisotropic materials require non-zero magnetization'
        );
    };

    function removeFromGroup(o) {
        const gId = o.groupId;
        if (gId !== 0 && (! gId || gId === '')) {
            return;
        }
        let g = self.getObject(gId);
        g.members.splice(g.members.indexOf(o.id), 1);
        appState.models.geomGroup = g;
        appState.saveQuietly('geomGroup');
    }

    function upload(inputFile, type=SIREPO.APP_SCHEMA.constants.fileTypePathPts) {
        fileUpload.uploadFileToUrl(
            inputFile,
            {},
            requestSender.formatUrl(
                'uploadLibFile',
                {
                    '<simulation_id>': appState.models.simulation.simulationId,
                    '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                    '<file_type>': type,
                }),
            function(d) {
            }, function (err) {
                throw new Error(inputFile + ': Error during upload ' + err);
            });
    }

    return self;
});

SIREPO.app.factory('radiaVariableService', function(appState, radiaService, rpnService) {
    let self = {};

    self.addressableObjects = (types) => {

        function optFieldsOfModelAndSupers(modelName) {

            function optFieldsOfModel(modelName) {
                const info = appState.modelInfo(modelName);
                return Object.keys(info).filter(
                    x => types.includes(info[x][SIREPO.INFO_INDEX_TYPE])
                );
            }

            const s = new Set();
            for (const m of [modelName, ...appState.superClasses(modelName)]) {
                for (const f of optFieldsOfModel(m)) {
                    s.add(f);
                }
            }
            return s;
        }

        function objectOptFields(o) {
            if (! o.type) {
                return {};
            }
            const obj = {};
            obj[o.name] = {
                name: o.name,
                id: o.id,
                fields: [],
                type: o.type,
            };
            for (const f of Object.keys(o).filter(x => optFieldsOfModelAndSupers(o.type).has(x))) {
                obj[o.name].fields.push(f);
            }
            return obj;
        }

        let objs = {};
        for (const o of radiaService.getObjects()) {
            const name = o.name;
            objs = {...objs, ...objectOptFields(o, name)};
            if (! objs[name]) {
                continue;
            }

            for (const mod of (o.modifications || [])) {
                if (! objs[name].modifications) {
                    objs[name].modifications = [];
                }
                objs[name].modifications.push(objectOptFields(mod, mod.type));
            }
            if (! objs[name].fields.length) {
                delete objs[name];
            }
        }
        return objs;
    };

    self.isScriptable = (o, f) => {
        const objs = self.scriptableObjects();
        return Object.keys(objs).includes(o.name) && objs[o.name].fields.includes(f);
    };

    self.isScripted = (o, f) => {
        if (! self.isScriptable(o, f)) {
            return false;
        }
        return isNaN(Number(o[f]));
    };

    self.scriptableObjects = () => self.addressableObjects(['Float', 'FloatArray', 'ScriptableField', 'ScriptableArray']);

    self.scriptedObject = o => {
        const s = {};
        for (const f of Object.keys(o)) {
            s[f] = self.isScripted(o, f) ? rpnService.getRpnValueForField(o, f) : window.structuredClone(o[f]);
        }
        return s;
    };

    self.searchableVariables = () => appState.models.rpnVariables.map(x => {
        return {
            label: x.name,
            value: x.value,
        };
    });

    self.updateCacheForVar = (name, value, rpnCache) => {
        var recomputeRequired = false;
        var re = new RegExp("\\b" + name + "\\b");
        for (var k in rpnCache) {
            if (k == name) {
                rpnCache[k] = value;
            }
            else if (k.match(re)) {
                recomputeRequired = true;
            }
        }
        return recomputeRequired;
    };

    // {varName0: value0, ...}
    self.updateCacheForVars = (vars, rpnCache) => {
        var recomputeRequired = false;
        for (const name in vars) {
            recomputeRequired = self.updateCacheForVar(name, vars[name], rpnCache);
        }
        return recomputeRequired;
    };

    self.updateRPNVars = (callback) => {
        if (! appState.models.rpnVariables) {
            appState.models.rpnVariables = [];
        }
        const rpns = appState.models.rpnVariables;
        const rpnNames = rpns.map(x => x.name);
        const objs = self.scriptableObjects();
        const oNames = [];
        let doSave = false;
        // add
        for (const name in objs) {
            const o = objs[name];
            for (const f of o.fields) {
                const vName = `${o.name}.${f}`;
                const v = radiaService.getObject(o.id)[f];
                oNames.push(vName);
                if (rpnNames.includes(vName)) {
                    const rpn = radiaService.getObjectByName(vName, rpns);
                    if (rpn.value !== v) {
                        rpnService.recomputeCache(vName, v);
                        rpn.value = v;
                        doSave = true;
                    }
                    continue;
                }
                rpns.push({
                    name: vName,
                    value: v,
                });
                rpnService.recomputeCache(vName, v);
                doSave = true;
            }
        }
        // remove
        for (let i = rpns.length - 1; i >= 0; --i) {
            const rpn = rpns[i];
            if (! oNames.includes(rpn.name)) {
                rpns.splice(i, 1);
                doSave = true;
            }
        }
        if (doSave) {
            appState.saveChanges(['rpnVariables', 'rpnCache'], callback);
        }
        else if (callback) {
            callback();
        }
    };

    return self;
});

SIREPO.app.controller('RadiaSourceController', function (appState, panelState, radiaService, radiaVariableService, rpnService, vtkPlotting, $rootScope, $scope) {
    //TODO(mvk): a lot of this is specific to freehand magnets and should be moved to a directive

    let self = this;

    const watchedModels = [
        'geomObject',
        'geomGroup',
        'racetrack',
        'radiaObject',
    ];

    self.axes = ['x', 'y', 'z'];
    self.builderCfg = {
        fixedDomain: false,
        fullZoom: true,
        initDomian: {
            x: [-0.025, 0.025],
            y: [-0.025, 0.025],
            z: [-0.025, 0.025],
        },
        preserveShape: true,
    };

    self.dropEnabled = true;
    self.selectedObject = null;
    self.shapes = [];
    self.toolbarSections = SIREPO.APP_SCHEMA.constants.toolbarItems.filter(function (item) {
        return item.name !== 'In Progress' && item.name.indexOf('Transforms') < 0;
    });
    self.views = [];


    self.alignLeft = (o, ref, axesInds) => {
        const i = axesInds[0];
        o.center[i] = ref.center[i] + 0.5 * (o.size[i] - ref.size[i]);
    };

    self.alignRight = (o, ref, axesInds) => {
        const i = axesInds[0];
        o.center[i] = ref.center[i] - 0.5 * (o.size[i] - ref.size[i]);
    };

    self.alignTop = (o, ref, axesInds) => {
        const i = axesInds[1];
        o.center[i] = ref.center[i] - 0.5 * (o.size[i] - ref.size[i]);
    };

    self.alignBottom = (o, ref, axesInds) => {
        const i = axesInds[1];
        o.center[i] = ref.center[i] + 0.5 * (o.size[i] - ref.size[i]);
    };

    self.centerX = (o, ref, axesInds) => {
        const i = axesInds[0];
        o.center[i] = ref.center[i];
    };

    self.centerY = (o, ref, axesInds) => {
        const i = axesInds[1];
        o.center[i] = ref.center[i];
    };

    self.align = (group, alignType, axesInds) => {

        function getFirstNotInGroup(arr) {
            let m0 = null;
            let i = 0;
            for (i = 0; i < arr.length; ++i) {
                const m = self.getObject(arr[i]);
                if (self.isGroup(m)) {
                    continue;
                }
                m0 = m;
                break;
            }
            return [i + 1, m0];
        }

        const d = getDescendents(group);
        if (d.length <= 1) {
            return;
        }
        const [start, m0] = getFirstNotInGroup(d);
        if (! m0) {
            return;
        }
        for (let i = start; i < d.length; ++i) {
            const m = self.getObject(d[i]);
            self[alignType](m, m0, axesInds);
            self.saveObject(m.id);
        }
        radiaService.saveGeometry(true);
    };

    self.copyObject = o => {
        const copy = appState.clone(o);
        copy.name = newObjectName(copy);
        copy.id = radiaService.generateId();
        copy.groupId = '';
        addObject(copy);
        self.editObject(copy);
    };

    self.decorateLabelWithIcon = (element, iconName, title) => {
        $(element)
        .closest('div[data-ng-switch]')
        .siblings('.control-label')
        .find('label')
        .append(`<span class="glyphicon glyphicon-${iconName}" title="${title}"></span>`);
    };

    self.editTool = tool => {
        if (tool.isInactive) {
            return;
        }
        panelState.showModalEditor(tool.model);
    };

    self.deleteObject = o => {
        radiaService.deleteObject(o);
        loadObjectViews();
    };

    self.dipoleTitle = () => {
        return ({
            dipoleBasic: 'Basic',
            dipoleC: 'C-Bend',
            dipoleH: 'H-Bend',
        }[self.getDipoleType()] || '') + ' Dipole';
    };

    self.editItem = o => {
        self.editObject(o);
    };

    self.editObjectWithId = id => {
        const o = self.getObject(id);
        if (! o) {
            return;
        }
        self.editObject(o);
    };

    self.editObject = o => {
        self.selectObject(o);
        panelState.showModalEditor(o.type);
    };

    self.getDipoleType = () => {
        if (self.getMagnetType() !== 'dipole') {
            return null;
        }
        return appState.models.simulation.dipoleType;
    };

    self.getGroup = o => self.getObject(o.groupId);

    self.getMagnetType = () => appState.models.simulation.magnetType;

    self.getMemberObjects = o => (self.getMembers(o) || []).map(mId => self.getObject(mId));

    self.getMembers = o => o.members;

    self.getObject = radiaService.getObject;

    self.getObjects = radiaService.getObjects;

    self.getShape = id => {
        return self.shapes.filter(s => s.id === id)[0];
    };

    self.getShapes = elevation => {
        if (! elevation) {
            return [];
        }
        let s = [];
        for (const v of self.views) {
            s = s.concat(v.allViews(elevation));
        }
        return self.shapes.concat(s);
    };

    self.getObjectView = id => self.views.filter(s => s.id === id)[0];

    self.getObjectViews = () => self.views;

    self.getUndulatorType = () => {
        if (self.getMagnetType() !== 'undulator') {
            return null;
        }
        return appState.models.simulation.undulatorType;
    };

    self.getView = () => `${appState.models.simulation[`${self.getMagnetType()}Type`]}`;

    self.isInGroup = o => ! ! o.groupId;

    self.isDropEnabled = () => self.dropEnabled;

    self.isGroup = radiaService.isGroup;

    self.loadObjectViews = loadObjectViews;

    self.moveObject = (direction, o) => {
        const objects = self.isInGroup(o) ? self.getMembers(self.getObject(o.groupId)) : self.getObjects();
        let i = objects.indexOf(self.isInGroup(o) ? o.id : o);
        const j = i + direction;
        if (j >= 0 && j < objects.length) {
            objects.splice(j, 0, objects.splice(i, 1)[0]);
            radiaService.saveGeometry(false, true);
        }
    };

    self.objectsOfType = type => appState.models.geometryReport.objects.filter(o => o.type === type);

    self.objectTypes = () => {
        const t = [];
        appState.models.geometryReport.objects.forEach(o =>  {
            if (! t.includes(o.type)) {
                t.push(o.type);
            }
        });
        return t.sort();
    };

    self.saveObject = function(id, callback) {

        function save(modelAndSupers) {
            appState.saveChanges(modelAndSupers, d => {
                self.selectedObject = null;
                radiaService.setSelectedObject(null);
                if (callback) {
                    callback(d);
                }
            });
        }

        const o = self.selectObjectWithId(id);
        if (! o) {
            return;
        }
        const s = [o.type, ...appState.superClasses(o.type)];
        if (o.layoutShape === 'polygon') {
            radiaService.updateExtruded(o, () => {
                save(s);
            });
        }
        else {
            save(s);
        }
    };

    self.selectObject = o => {
        if (o) {
            self.selectedObject = o;
            radiaService.setSelectedObject(o);
            appState.models[panelState.getBaseModelKey(o.type)] = o;
        }
        return o;
    };

    self.selectObjectWithId = id => self.selectObject(self.getObject(id));

    self.shapeBounds = elevation => shapesBounds(self.getShapes(elevation));

    self.showDesigner = () => {
        return appState.models.simulation.magnetType === 'freehand';
    };

    self.showParams = () => {
        return appState.models.simulation.magnetType !== 'freehand';
    };

    self.viewShadow = o => self.viewsForObject(appState.setModelDefaults({}, 'cuboid'));

    self.viewsForObject = obj => {
        const o = radiaVariableService.scriptedObject(obj);
        const supers = appState.superClasses(o.type);
        let center = o.center;
        let size = o.size;
        const isGroup = self.isGroup(o);
        const scale = SIREPO.APP_SCHEMA.constants.objectScale;

        if (isGroup) {
            const b = groupBounds(o.members.map(id => self.getObject(id)));
            center = b.map(c => (c[0] + c[1]) / 2);
            size = b.map(c => Math.abs(c[1] - c[0]));
        }

        let view;
        if (supers.includes('extrudedPoly')) {
            if (! o.points.length) {
                return null;
            }
            view = new SIREPO.VTK.ExtrudedPolyViews(o.id, o.name, center, size, o.extrusionAxis, o.points, scale);
        }
        else if (o.type === 'cylinder') {
            view = new SIREPO.VTK.CylinderViews(o.id, o.name, center, size, o.extrusionAxis, o.numSides, scale);
        }
        else if (o.type === 'racetrack') {
            view = new SIREPO.VTK.RacetrackViews(o.id, o.name, center, size, o.axis, o.numSegments, o.radii[1], scale);
        }
        else {
            view = new SIREPO.VTK.CuboidViews(o.id, o.name, center, size, scale);
        }

        view.setShapeProperties(
            {
                alpha: 0.3,
                color: o.color,
            }
        );
        if (isGroup) {
            view.setShapeProperties(
                {
                    fillStyle: null,
                    strokeStyle: 'dashed',
                    outlineOffset: 5.0,
                    strokeWidth: 0.75,
                    draggable: false,
                }
            );
        }
        return view;
    };

    self.viewTitle = () => {
        return {
            dipole: (
                {
                    dipoleBasic: 'Basic',
                    dipoleC: 'C-Bend',
                    dipoleH: 'H-Bend',
                }[self.getDipoleType()] || ''
            ) + ' Dipole',
            undulator: (
                {
                    undulatorBasic: 'Basic',
                    undulatorHybrid: 'Hybrid',
                }[self.getUndulatorType()] || ''
            ) + ' Undulator',
        }[self.getMagnetType()];
    };

    function addBeamAxis() {
        const axis = appState.models.simulation.beamAxis;
        for (const p in vtkPlotting.COORDINATE_PLANES) {
            if (p.indexOf(axis) < 0) {
                continue;
            }
            let p1 = new SIREPO.GEOMETRY.Point();
            p1[axis] = -1;
            let p2 = new SIREPO.GEOMETRY.Point();
            p2[axis] = 1;
            let pl = vtkPlotting.plotLine(
                `beamAxis-${appState.models.simulation.beamAxis}-${p}`,
                `beamAxis-${appState.models.simulation.beamAxis}`,
                new SIREPO.GEOMETRY.Line(p1, p2),
                '#000000', 1.0, 'dashed', "4,4"
            );
            pl.coordPlane = p;
            pl.endMark = 'arrow';
            self.shapes.push(pl);
        }
    }

    function addObject(o) {
        appState.models.geometryReport.objects.push(o);
        // for groups, set the group id of all members
        (o.members || []).forEach(oId => {
            self.getObject(oId).groupId = o.id;
        });
        addViewsForObject(o);
    }

    function addViewsForObject(o) {

        function applyMatrixToGroup(g, m) {
            for (const m_id of g.members) {
                let v = self.getObjectView(m_id);
                const member = self.getObject(m_id);
                if (! v) {
                    v = self.viewsForObject(member);
                    self.views.push(v);
                }
                v.addCopyingTransform(m);
                if (self.isGroup(member)) {
                    applyMatrixToGroup(member, m);
                }
            }
        }

        let baseViews = self.getObjectView(o.id);
        if (! baseViews) {
            baseViews = self.viewsForObject(o);
            if (! baseViews) {
                return;
            }
            self.views.push(baseViews);
        }

        //TODO(mvk): the view knows about the scale and should apply it to transforms
        // rather than using radiaService.scaledArray here
        for (const xform of o.transforms) {
            const t = xform.type;
            if (t === 'rotate') {
                baseViews.addTransform(
                    new SIREPO.GEOMETRY.RotationMatrix(
                        xform.axis,
                        radiaService.scaledArray(xform.useObjectCenter === "1" ? o.center : xform.center),
                        SIREPO.GEOMETRY.GeometryUtils.toRadians(parseFloat(xform.angle))
                    )
                );
                continue;
            }
            if (t === 'symmetryTransform') {
                const plane = new SIREPO.GEOMETRY.Plane(
                    xform.symmetryPlane,
                    new SIREPO.GEOMETRY.Point(...radiaService.scaledArray(xform.symmetryPoint))
                );
                //TODO(mvk): symmetry plane shapes
                const r = new SIREPO.GEOMETRY.ReflectionMatrix(plane);
                baseViews.addCopyingTransform(r);
                if (self.isGroup(o)) {
                    applyMatrixToGroup(o, r);
                }
                continue;
            }
            if (t === 'cloneTransform') {
                let xf = new SIREPO.GEOMETRY.AffineMatrix();
                for (const cloneXform of xform.transforms) {
                    const ct = cloneXform.type;
                    if (ct === 'translate') {
                        xf = xf.multiplyAffine(
                            new SIREPO.GEOMETRY.TranslationMatrix(radiaService.scaledArray(cloneXform.distance))
                        );
                    }
                    else if (cloneXform.type === 'rotate') {
                        xf = xf.multiplyAffine(
                            new SIREPO.GEOMETRY.RotationMatrix(
                                cloneXform.axis,
                                radiaService.scaledArray(cloneXform.useObjectCenter === "1" ? o.center : cloneXform.center),
                                SIREPO.GEOMETRY.GeometryUtils.toRadians(parseFloat(cloneXform.angle))
                            )
                        );
                    }
                    else {
                        continue;
                    }
                }
                baseViews.addCopyingTransform(xf, xform.numCopies);
            }
        }
    }

    function getDescendents(group) {
        let d = [];
        for (const m of (group.members || [])) {
            d.push(m);
            const o = self.getObject(m);
            if (self.isGroup(o)) {
                d = d.concat(getDescendents(o));
            }
        }
        return d;
    }

    function groupBounds(objs) {
        const b = [
            [Number.MAX_VALUE, -Number.MAX_VALUE],
            [Number.MAX_VALUE, -Number.MAX_VALUE],
            [Number.MAX_VALUE, -Number.MAX_VALUE]
        ];
        b.forEach(function (c, i) {
            (objs || appState.models.geometryReport.objects || []).forEach(obj => {
                const o = radiaVariableService.scriptedObject(obj);
                if ((o.members || []).length) {
                    const g = groupBounds(o.members.map(mId => radiaVariableService.scriptedObject(self.getObject(mId))));
                    c[0] = Math.min(c[0], g[i][0]);
                    c[1] = Math.max(c[1], g[i][1]);
                    return;
                }
                c[0] = Math.min(c[0], o.center[i] - o.size[i] / 2);
                c[1] = Math.max(c[1], o.center[i] + o.size[i] / 2);
            });
        });
        return b;
    }

    function loadObjectViews() {
        self.views = [];
        self.shapes = [];
        if (! self.showDesigner()) {
            return;
        }
        appState.models.geometryReport.objects.forEach(addViewsForObject);
        addBeamAxis();
        $rootScope.$broadcast('shapes.loaded');
    }

    function newObjectName(o) {
        return appState.uniqueName(appState.models.geometryReport.objects, 'name', o.name + '_{}');
    }

    function shapesBounds(shapes) {
        let b = {
            x: [Number.MAX_VALUE, -Number.MAX_VALUE],
            y: [Number.MAX_VALUE, -Number.MAX_VALUE],
        };
        shapes.forEach(s => {
            const sb = s.bounds ? s.bounds() : {x: [0, 0], y: [0, 0]};
            for (const dim in b) {
                b[dim] = [
                    Math.min(b[dim][0], sb[dim][0]),
                    Math.max(b[dim][1], sb[dim][1])
                ];
            }
        });
        for (const dim in b) {
            if (b[dim].some(x => Math.abs(x) === Number.MAX_VALUE)) {
                return b;
            }
        }
        return SIREPO.GEOMETRY.GeometryUtils.boundsRadius(b);
    }

    // initial setup
    if (! appState.models.geometryReport.objects) {
        appState.models.geometryReport.objects = [];
    }
    radiaVariableService.updateRPNVars();
    loadObjectViews();


    $scope.$on('cancelChanges', function(e, name) {
        if (name === 'geometryReport') {
            radiaVariableService.updateRPNVars();
            loadObjectViews();
        }
    });

    $scope.$on('modelChanged', function(e, modelName) {
        if (! watchedModels.includes(modelName)) {
            return;
        }
        let o = self.selectedObject;
        if (o) {

            if (! radiaService.getObject(o.id)) {
                // catch unrelated saved objects
                if (o.type === modelName || panelState.getBaseModelKey(o.type) === modelName) {
                    addObject(o);
                }
                else {
                    self.selectedObject = null;
                }
            }
            if (o.type === 'racetrack') {
                radiaService.updateRaceTrack(o);
            }
            if (o.type === 'cylinder') {
                radiaService.updateCylinder(o);
            }
            if (o.materialFile) {
                o.hmFileName = o.materialFile.name;
                radiaService.upload(o.materialFile, SIREPO.APP_SCHEMA.constants.fileTypeHM);
            }
        }
        radiaService.saveGeometry(true, false, () => {
            if (self.selectedObject) {
                radiaVariableService.updateRPNVars();
                loadObjectViews();
            }
        });
    });

    $scope.$on('layout.object.dropped', function (e, lo) {
        const m = appState.setModelDefaults({}, lo.type);
        m.isNew = true;
        m.center = lo.center;
        m.name = lo.type;
        m.name = newObjectName(m);
        self.editObject(m);
    });

    $scope.$on('drop.target.enabled', function (e, val) {
        self.dropEnabled = val;
    });
});

SIREPO.app.controller('RadiaVisualizationController', function (appState, radiaService) {
    let self = this;

    self.enableKickMaps = function() {
        return appState.isLoaded() && appState.models.simulation.enableKickMaps === '1';
    };

    self.hasPaths = radiaService.hasPaths;

    self.isSolvable = function() {
        return appState.isLoaded() && appState.models.geometryReport.isSolvable == '1';
    };
});

SIREPO.app.controller('RadiaOptimizationController', function (appState, frameCache, persistentSimulation, radiaService, radiaVariableService, requestSender, $scope) {
    const self = this;
    self.simScope = $scope;
    self.simAnalysisModel = 'optimizerAnimation';
    self.summaryData = {};

    self.computeModel = m => m;

    self.hasOptFields = () => {
        if (! appState.isLoaded()) {
            return false;
        }
        return (appState.applicationState().optimizer.parameters || []).length > 0;
    };

    self.simState = persistentSimulation.initSimulationState(self);

    self.simState.errorMessage = () => self.errorMessage;

    self.simState.logFileURL = () => requestSender.formatUrl('downloadRunFile', {
        '<simulation_id>': appState.models.simulation.simulationId,
        '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
        '<model>': self.simState.model,
        '<frame>': SIREPO.nonDataFileFrame,
        '<suffix>': 'out',
    });


    self.newSimFromResults = () => {
        function applyResults(objects) {
            const modified = new Set();
            for (const p in self.summaryData) {
                const modelField = p.split('.');
                const o = radiaService.getObjectByName(modelField[0], objects);
                o[modelField[1]] = self.summaryData[p];
                modified.add(o);
            }
            modified.forEach(radiaService.updateObject);
        }

        appState.copySimulation(
            appState.models.simulation.simulationId,
            data => {
                applyResults(data.models.geometryReport.objects);
                for (const p in self.summaryData) {
                    radiaService.getObjectByName(p, data.models.rpnVariables).value = self.summaryData[p];
                }
                if (radiaVariableService.updateCacheForVars(self.summaryData, data.models.rpnCache)) {
                    requestSender.sendStatefulCompute(
                        appState,
                        d =>  {
                            data.models.rpnCache = d.cache;
                            requestSender.sendRequest(
                                'saveSimulationData',
                                () => {
                                    requestSender.localRedirectHome(data.models.simulation.simulationId);
                                },
                                data,
                                err => {
                                    throw new Error('Simulation creation failed: ' + err);
                                }
                            );
                        },
                        {
                            method: 'recompute_rpn_cache_values',
                            cache: data.models.rpnCache,
                            variables: data.models.rpnVariables,
                        }
                    );
                }
            },
            `${appState.models.simulation.name} (optimized)`,
            appState.models.simulation.folder
        );
    };


    self.simState.runningMessage = () => {
        return 'Completed run: ' + self.simState.getFrameCount();
    };

    self.simHandleStatus = data => {
        self.errorMessage = data.error;
        if ('frameCount' in data && ! data.error) {
            // single step means the optimizer never actually ran but is returning the initial
            // parameter values
            if (data.frameCount === 1) {
                self.errorMessage = 'Optimizer failed to run';
                frameCache.setFrameCount(0);
                return;
            }
            frameCache.setFrameCount(data.frameCount);
        }
    };

    $scope.startSimulation = () => {
        self.summaryData = {};
        self.simState.runSimulation();
    };

    $scope.$on(`${self.simAnalysisModel}.summaryData`, (e, d) => {
        self.summaryData = d;
    });

});


SIREPO.app.directive('appFooter', function() {
    return {
        restrict: 'A',
        scope: {
            nav: '=appFooter',
        },
        template: `
            <div data-common-footer="nav"></div>
            <div data-dmp-import-dialog="" data-title="Import File" data-description="Select Radia dump (.dat) or ${SIREPO.APP_SCHEMA.productInfo.shortName} Export (.zip)"></div>
        `,
    };
});

SIREPO.app.directive('appHeader', function(activeSection, appState, panelState, requestSender) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appHeader',
        },
        template: `
            <div data-app-header-brand="nav"></div>
            <div data-app-header-left="nav"></div>
            <div data-app-header-right="nav">
              <app-header-right-sim-loaded>
                <div data-sim-sections="">
                  <li data-ng-if="! isImported()" class="sim-section" data-ng-class="{active: nav.isActive('source')}"><a href data-ng-click="nav.openSection('source')"><span class="glyphicon glyphicon-magnet"></span> Design</a></li>
                  <li class="sim-section" data-ng-class="{active: nav.isActive('visualization')}"><a href data-ng-click="nav.openSection('visualization')"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>
                  <li class="sim-section" data-ng-class="{active: nav.isActive('optimization')}"><a href data-ng-click="nav.openSection('optimization')"><span class="glyphicon glyphicon-time"></span> Optimization</a></li>
                </div>
              </app-header-right-sim-loaded>
              <app-settings>
                    <li><a data-ng-href="{{ exportDmpUrl() }}"><span class="glyphicon glyphicon-cloud-download"></span> Export Radia Dump</a></li>
              </app-settings>
              <app-header-right-sim-list>
                <ul class="nav navbar-nav sr-navbar-right">
                  <li><a href data-ng-click="showImportModal()"><span class="glyphicon glyphicon-cloud-upload"></span> Import</a></li>
                </ul>
              </app-header-right-sim-list>
            </div>
        `,
        controller: function($scope) {

            $scope.exportDmpUrl = () => {
                if (! appState.isLoaded()) {
                    return null;
                }
                return requestSender.formatUrl('downloadRunFile', {
                    '<simulation_id>': appState.models.simulation.simulationId,
                    '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                    '<frame>': SIREPO.nonDataFileFrame,
                    '<model>': 'geometryReport',
                    '<suffix>': '.dat'
                });
            };

            $scope.isImported = () => (appState.models.simulation || {}).dmpImportFile;

            $scope.showImportModal = () => {
                $('#simulation-import').modal('show');
            };

            $scope.simulationId = () => appState.isLoaded() ? appState.models.simulation.simulationId : null;
        }
    };
});

SIREPO.app.directive('bevelEdge', function(appState, panelState, radiaService, utilities) {

    return {
        restrict: 'A',
        scope: {
            field: '=',
            model: '=',
            modelName: '=',
        },
        template: `
          <select class="form-control" data-ng-model="model[field]" data-ng-options="item[0] as cornerLabel(item[0]) for item in enum[info[1]]"></select>
        `,
        controller: function($scope) {
            $scope.enum = SIREPO.APP_SCHEMA.enum;
            $scope.info = appState.modelInfo($scope.modelName)[$scope.field];

            $scope.cornerLabel = index => {
                const signs = [['-', '+'], ['+', '+'], ['+', '-'], ['-', '-']][parseInt(index)];
                const axes = SIREPO.GEOMETRY.GeometryUtils.nextAxes($scope.model.cutAxis);
                return `(${signs[0]}${axes[0]}, ${signs[1]}${axes[1]})`;
            };
        },
    };
});

SIREPO.app.directive('dmpImportDialog', function(appState, fileManager, fileUpload, requestSender) {

    const RADIA_IMPORT_FORMATS = ['.dat',];
    const IMPORT_FORMATS = RADIA_IMPORT_FORMATS.concat(['.zip',]);

    return {
        restrict: 'A',
        scope: {
            description: '@',
            title: '@',
        },
        template: `
            <div class="modal fade" id="simulation-import" tabindex="-1" role="dialog">
              <div class="modal-dialog modal-lg">
                <div class="modal-content">
                  <div class="modal-header bg-info">
                    <button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>
                    <div data-help-button="{{ title }}"></div>
                    <span class="lead modal-title text-info">{{ title }}</span>
                  </div>
                  <div class="modal-body">
                    <div class="container-fluid">
                        <form>
                        <div data-file-chooser="" data-input-file="inputFile" data-title="title" data-description="description" data-file-formats="${IMPORT_FORMATS.join(',')}"></div>
                          <div class="text-warning"><strong>{{ fileUploadError }}</strong></div>
                          <div class="col-sm-6 pull-right">
                            <button data-ng-click="importDmpFile(inputFile)" class="btn btn-primary" data-ng-class="{'disabled': isMissingImportFile() }">Import File</button>
                             <button data-dismiss="modal" class="btn btn-default">Cancel</button>
                          </div>
                        </form>
                    </div>
                  </div>
                </div>
              </div>
            </div>
        `,
        controller: function($scope) {
            $scope.inputFile = null;
            $scope.isMissingImportFile = function() {
                return ! $scope.inputFile;
            };
            $scope.fileUploadError = '';
            $scope.isUploading = false;
            $scope.importDmpFile = function(inputFile) {
                if (! inputFile) {
                    return;
                }
                fileUpload.uploadFileToUrl(
                    inputFile,
                    {
                        folder: fileManager.getActiveFolderPath(),
                        arguments: '',
                    },
                    requestSender.formatUrl(
                        'importFile',
                        {simulation_type: SIREPO.APP_SCHEMA.simulationType},
                    ),
                    function(d) {
                        if (d.error) {
                            $scope.fileUploadError = d.error;
                            return;
                        }
                        $('#simulation-import').modal('hide');
                        requestSender.localRedirect(
                            'visualization',
                            {'simulationId': d.models.simulation.simulationId}
                        );
                    },
                    function (err) {
                        $scope.fileUploadError = err;
                    },
                );
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
    };
});

//TODO(pjm): this is a copy of the kickMapReport directive
SIREPO.app.directive('electronTrajectoryReport', function(appState, panelState) {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <div class="col-md-6">
                <div data-ng-if="! dataCleared" data-report-panel="parameter" data-request-priority="0" data-model-name="electronTrajectoryReport"></div>
            </div>
        `,
        controller: function($scope) {
            $scope.dataCleared = true;
            $scope.$on('radiaViewer.loaded', () => {
                $scope.dataCleared = false;
            });
        },
    };
});

SIREPO.app.directive('fieldLineoutAnimation', function(appState, frameCache, persistentSimulation, radiaService, requestSender) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        template: `
            <div class="col-md-6">
              <div data-ng-if="showFieldLineoutPanel()" data-report-panel="parameter" data-model-name="fieldLineoutAnimation">
                <div data-sim-status-panel="simState"></div>
                <div data-ng-if="::canExport" class="col-sm-6 pull-right" style="padding-top: 8px;">
                    <button data-ng-disabled="! isExportEnabled()" class="btn btn-default" data-ng-click="createSRWSimulation()">Open in SRW</button>
                </div>
              </div>
            </div>
        `,
        controller: function($scope) {
            const modelName = $scope.modelName;
            const simId = appState.models.simulation.simulationId;
            const simName = appState.models.simulation.name;
            const simType = SIREPO.APP_SCHEMA.simulationType;

            $scope.model = appState.models[modelName];
            $scope.simScope = $scope;
            $scope.simComputeModel = modelName;

            $scope.canExport = appState.models.simulation.magnetType === 'undulator';

            $scope.createSRWSimulation = () => {
                const uName = `Radia Undulator ${simName}`;
                requestSender.sendRequest(
                    'newSimulation',
                    data => {
                        requestSender.openSimulation(
                            'srw',
                            'source',
                            data.models.simulation.simulationId
                        );
                    },
                    {
                        electronBeamPosition: {
                            drift: SIREPO.APP_SCHEMA.constants.objectScale *
                                appState.models[modelName].fieldPath.begin[radiaService.getAxisIndices().depth],
                        },
                        folder: '/',
                        name: simName,
                        simulation: {
                            notes: 'Tabulated undulator from radia',
                        },
                        simulationType: 'srw',
                        sourceSimId: simId,
                        sourceSimType: simType,
                        sourceType: 't',
                        tabulatedUndulator: {
                            gap: appState.models[appState.models.simulation.undulatorType].gap,
                            indexFileName: `${modelName}_sum.txt`,
                            magneticFile: `${modelName}.zip`,
                            name: uName,
                            undulatorSelector: uName,
                            undulatorType: 'u_t',
                        }
                    },
                    err => {
                        throw new Error('Simulation creation failed: ' + err);
                    }
                );
            };

            $scope.isExportEnabled = () => {
                return $scope.canExport &&
                    $scope.simState.isStateCompleted() &&
                    frameCache.getFrameCount() > 0;
            };

            $scope.simHandleStatus = data => {
                if (data.computeModel === 'fieldLineoutAnimation' && data.state === "completed") {
                    frameCache.setFrameCount(1);
                }
            };

            function getPath(id) {
                for (const p of appState.models.fieldPaths.paths) {
                    if (p.id === id) {
                        return p;
                    }
                }
                return null;
            }

            function runSimulation() {
                if ($scope.showFieldLineoutPanel()) {
                    // Don't run automatically for sbatch or nersc
                    if (['sequential', 'parallel'].includes(appState.models.fieldLineoutAnimation.jobRunMode)) {
                        if (! $scope.simState.isProcessing()) {
                            $scope.simState.runSimulation();
                        }
                    }
                }
            }

            function setPath(p) {
                if (! p) {
                    return;
                }
                appState.models[modelName].lastModified = Date.now();
                appState.models[modelName].fieldPath = p;
                if (p.axis) {
                    appState.models[modelName].plotAxis = p.axis;
                }
                appState.saveChanges(modelName);
            }

            function updatePath() {
                const currentPath = appState.models[modelName].fieldPath;
                const p = getPath((currentPath || {}).id);
                if (! p) {
                    delete appState.models[modelName].fieldPath;
                    setPath(appState.models.fieldPaths.paths[0]);
                }
                else {
                    if (! appState.deepEquals(p, currentPath)) {
                        setPath(p);
                    }
                }
            }

            $scope.hasPaths = radiaService.hasPaths;

            $scope.showFieldLineoutPanel = () => $scope.hasPaths();

            $scope.$on('fieldLineoutAnimation.saved', runSimulation);
            $scope.$on('fieldPaths.saved', updatePath);
            $scope.$on('solve.complete', runSimulation);

            appState.watchModelFields($scope, [`${modelName}.fieldPath`],  () => {
                if (appState.models[modelName].fieldPath.axis) {
                    appState.models[modelName].plotAxis = appState.models[modelName].fieldPath.axis;
                }
            });

            updatePath();
            $scope.simState = persistentSimulation.initSimulationState($scope);
        },
    };
});

SIREPO.app.directive('fieldIntegralTable', function(appState, panelState, plotting, radiaService, utilities) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        template: `
            <table data-ng-if="hasPaths()" style="width: 100%; table-layout: fixed; margin-bottom: 10px" class="table radia-table-hover">
                <colgroup>
                    <col style="width: 20ex">
                    <col>
                    <col>
                </colgroup>
                <thead>
                <tr>
                    <th data-ng-repeat="h in HEADING">{{ h }}</th>
                </tr>
                </thead>
                <tbody>
                <tr data-ng-repeat="path in linePaths() track by path.id">
                    <td>{{ path.name }}</td>
                    <td>{{ path.begin }} &#x2192; {{ path.end }}</td>
                    <td>
                    <div data-ng-repeat="t in INTEGRABLE_FIELD_TYPES"><span style="font-weight: bold">{{ t }}:</span> </span><span>{{ format(integrals[path.name][t]) }}</span></div>
                    </td>
                </tr>
                </tbody>
            </table>
        `,
        controller: function($scope) {
            const lineTypes = ['axisPath', 'linePath'];

            plotting.setTextOnlyReport($scope);

            $scope.HEADING = ['Line', 'Endpoints', 'Fields'];
            $scope.INTEGRABLE_FIELD_TYPES = ['B', 'H'];
            $scope.integrals = {};
            $scope.model = appState.models.fieldPaths;

            $scope.hasPaths = () => radiaService.hasPaths(lineTypes);

            $scope.format = vals => (vals || []).map(v => utilities.roundToPlaces(v, 4));

            $scope.isLine = p => lineTypes.includes(p.type);

            $scope.linePaths = () => ((appState.applicationState().fieldPaths || {}).paths || []).filter($scope.isLine);

            $scope.load = json => {
                $scope.integrals = json;
            };

            $scope.$on('fieldPaths.changed', setLastModified);

            function setLastModified() {
                appState.models[$scope.modelName].lastModified = Date.now();
                appState.saveChanges($scope.modelName);
            }
        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});

SIREPO.app.directive('groupEditor', function(appState, radiaService) {
    return {
        restrict: 'A',
        scope: {
            field: '=',
            model: '=',
        },
        template: `
            <div style="border-style: solid; border-width: 1px; border-color: #00a2c5;">
            <table style="table-layout: fixed;" class="table table-striped table-condensed radia-table-dialog">
                <tr style="background-color: lightgray;" data-ng-show="field.length > 0">
                  <th>Members</th>
                  <th></th>
                </tr>
                <tr data-ng-repeat="mId in field track by $index">
                    <td style="padding-left: 1em"><span style="font-size: large; color: {{ getObject(mId).color }};">■</span> <span>{{ getObject(mId).name }}</span></td>
                    <td style="text-align: right">&nbsp;<div class="sr-button-bar-parent"><div class="sr-button-bar">  <button data-ng-click="ungroupObject(mId)" class="btn btn-danger btn-xs"><span class="glyphicon glyphicon-remove"></span></button></div><div></td>
                </tr>
                <tr style="background-color: lightgray;">
                  <th>Ungrouped</th>
                  <th></th>
                </tr>
                <tr data-ng-repeat="oId in getIds() | filter:hasNoGroup track by $index">
                  <td style="padding-left: 1em"><span style="font-size: large; color: {{ getObject(oId).color }};">■</span> <span>{{ getObject(oId).name }}</span></td>
                  <td style="text-align: right">&nbsp;<div class="sr-button-bar-parent"><div class="sr-button-bar"><button class="btn btn-info btn-xs sr-hover-button" data-ng-click="addObject(oId)"><span class="glyphicon glyphicon-plus"></span></button> </div><div></td>
                </tr>
            </table>
            </div>
        `,
        controller: function($scope) {
            $scope.objects = appState.models.geometryReport.objects;
            if (! $scope.field) {
                $scope.field = [];
            }

            $scope.addObject = oId => {
                let o = $scope.getObject(oId);
                o.groupId = $scope.model.id;
                $scope.field.push(o.id);
            };

            $scope.getIds = () => $scope.objects.map(o => o.id);

            $scope.getObject = oId => radiaService.getObject(oId);

            $scope.hasNoGroup = oId => {
                if ($scope.field.includes(oId)) {
                    return false;
                }
                if (groupedObjects(oId).indexOf($scope.model.id) >= 0) {
                    return false;
                }
                const o = $scope.getObject(oId);
                return oId !== $scope.model.id && (! o.groupId || o.groupId === '');
            };

            $scope.ungroupObject = oId => {
                $scope.getObject(oId).groupId = '';
                const oIdx = $scope.field.indexOf(oId);
                if (oIdx < 0) {
                    return;
                }
                $scope.field.splice(oIdx, 1);
            };

            function groupedObjects(oId) {
                const o = $scope.getObject(oId);
                if (! o) {
                    return [];
                }
                let objs = [];
                for (const mId of (o.members || [])) {
                    objs.push(mId);
                    objs = objs.concat(groupedObjects(mId));
                }
                return objs;
            }
        },
    };
});

SIREPO.app.directive('kickMapReport', function(appState, panelState, plotting, radiaService, requestSender, utilities) {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <div class="col-md-6">
                <div data-ng-if="! dataCleared" data-report-panel="3d" data-panel-title="Kick Map" data-model-name="kickMapReport"></div>
            </div>
        `,
        controller: function($scope) {
            $scope.dataCleared = true;
            $scope.$on('radiaViewer.loaded', () => {
                $scope.dataCleared = false;
            });
        },
    };
});

SIREPO.app.directive('modelArrayTable', function(appState, panelState, radiaService, $rootScope) {
    return {
        restrict: 'A',
        scope: {
            field: '=',
            fieldName: '=',
            itemClass: '@',
            model: '=',
            models: '=',
            modelName: '=',
        },
        template: `
            <div>
              <div style="border-style: solid; border-width: 1px; border-color: #00a2c5;">
              <table class="table table-striped table-condensed radia-table-dialog">
                <thead></thead>
                <tbody>
                <tr data-ng-repeat="item in field track by $index">
                  <td style="display: inline-flex; flex-wrap: wrap;">
                    <div class="item-name">
                      <span class="glyphicon glyphicon-chevron-down" data-ng-show="isExpanded(item)" data-ng-click="toggleExpand($index)"></span>
                      <span class="glyphicon glyphicon-chevron-up" data-ng-show="! isExpanded(item)" data-ng-click="toggleExpand($index)"></span>
                      <label>{{ title(item.type) }}</label>
                    </div>
                    <div data-ng-show="isExpanded(item)" data-ng-repeat="f in modelFields($index)" style="padding-left: 6px; min-width: {{ fieldMinWidth(item.type, f) }}">
                      <div data-field-editor="f" data-label-size="12" data-field-size="fieldSize(item.type, f)" data-model-name="item.type" data-model="item"></div>
                    </div>
                    <div data-ng-show="! isExpanded(item)">...</div>
                    </td>
                    <td>
                      <div class="sr-button-bar-parent">
                        <div class="sr-button-bar">
                          <button class="btn btn-info btn-xs"  data-ng-disabled="$index == 0" data-ng-click="moveItem(-1, item)"><span class="glyphicon glyphicon-arrow-up"></span></button> <button class="btn btn-info btn-xs" data-ng-disabled="$index == field.length - 1" data-ng-click="moveItem(1, item)"><span class="glyphicon glyphicon-arrow-down"></span></button>  <button data-ng-click="deleteItem($index)" class="btn btn-danger btn-xs"><span class="glyphicon glyphicon-remove"></span></button>
                        </div>
                      </div>
                    </td>
                </tr>
                <tr>
                  <td colspan="100%">
                    <select class="form-control" data-ng-model="selectedItem" data-ng-options="title(m) for m in models" data-ng-change="addItem()">
                      <option value="" disabled selected>add</option>
                    </select>
                  </td>
               </tr>
               </tbody>
              </table>
            </div>
            </div>
        `,
        controller: function($scope, $element) {
            const doSaveGeom = appState.superClasses($scope.modelName).includes('radiaObject');
            let expanded = {};
            for (const i in $scope.field) {
                expanded[i] = false;
            }

            let watchedModels = [$scope.modelName].concat($scope.models);

            $scope.selectedItem = null;

            function itemIndex(data) {
                return $scope.field.indexOf(data);
            }

            function info(modelName, field) {
                return appState.modelInfo(modelName)[field];
            }

            $scope.addItem = () => {
                if (! $scope.selectedItem) {
                    return;
                }
                const m = appState.setModelDefaults({}, $scope.selectedItem);
                $scope.field.push(m);
                expanded[$scope.field.length - 1] = true;
                $scope.selectedItem = null;
            };

            $scope.deleteItem = index => {
                $scope.field.splice(index, 1);
                delete expanded[index];
                if (doSaveGeom) {
                   radiaService.saveGeometry(true);
                }
            };

            $scope.fieldLabel = (modelName, field) => info(modelName, field)[SIREPO.INFO_INDEX_LABEL];

            $scope.fieldMinWidth = (modelName, field) => {
                return info(modelName, field)[SIREPO.INFO_INDEX_TYPE] === 'ModelArrayTable' ? '900px' : '0';
            };

            $scope.fieldSize = (modelName, field) => {
                return info(modelName, field)[SIREPO.INFO_INDEX_TYPE] === 'String' ? 8 : null;
            };

            $scope.isExpanded = item => expanded[itemIndex(item)];

            $scope.modelFields = index => {
                return SIREPO.APP_SCHEMA.view[$scope.field[index].type].advanced;
            };

            $scope.moveItem = (direction, item) => {
                const d = direction === 0 ? 0 : (direction > 0 ? 1 : -1);
                const currentIndex = itemIndex(item);
                const newIndex = currentIndex + d;
                if (newIndex >= 0 && newIndex < $scope.field.length) {
                    const tmp = $scope.field[newIndex];
                    $scope.field[newIndex] = item;
                    $scope.field[currentIndex] = tmp;
                }
            };

            $scope.title = modelName => SIREPO.APP_SCHEMA.view[modelName].title;

            $scope.toggleExpand = index => {
                expanded[index] = ! expanded[index];
            };

            $scope.$on('modelChanged', (e, modelName) => {
                if (! watchedModels.includes(modelName)) {
                    return;
                }
                $scope.selectedItem = null;
                if (doSaveGeom) {
                    radiaService.saveGeometry(true, false);
                }
            });

            $scope.$on('cancelChanges', (e, name) => {
                if (name === 'geometryReport') {
                    return;
                }
                if (! watchedModels.includes(name)) {
                    return;
                }
                appState.cancelChanges('geometryReport');
            });

        },
    };
});

SIREPO.app.directive('objectOptimizerField', function(appState, panelState, radiaService, radiaOptimizationService, validationService) {
    return {
        restrict: 'A',
        scope: {
            field: '=',
            model: '=',
            modelName: '=',
        },
        template: `
            <div>
              <div style="border-style: solid; border-width: 1px; border-color: #00a2c5;">
              <table class="table table-striped table-condensed">
                <thead>
                  <th>Object</th>
                  <th>Field</th>
                  <th>Min</th>
                  <th>Max</th>
                  <th>Start</th>
                  <th></th>
                </thead>
                <tbody>
                <tr data-ng-repeat="item in field track by $index">
                  <td style="display: inline-flex; flex-wrap: wrap;">
                    {{ item.object }}
                  </td>
                  <td>
                    <select class="form-control" data-ng-model="item.field" data-ng-options="f for f in fieldsForObject(item.object)">
                      <option value="" disabled selected>select field</option>
                    </select>
                  </td>
                  <td data-ng-repeat="attr in ['min', 'max']" class="rsopt-minmax">
                    <input data-ng-if="item.field" data-string-to-number="" data-min="fieldMin(item)" data-max="fieldMax(item)" data-ng-model="item[attr]" class="form-control" style="text-align: right" data-lpignore="true" required />
                    </td>
                  <td class="rsopt-start">
                    <input data-ng-if="item.field" data-string-to-number="" data-min="fieldMin(item)" data-max="fieldMax(item)" data-ng-model="item.start" class="form-control" style="text-align: right" data-lpignore="true" required />
                    <div class="sr-input-warning"></div>
                  </td>
                  <td>
                    <button title="delete" data-ng-click="deleteItem($index)" class="btn btn-danger btn-xs"><span class="glyphicon glyphicon-remove"></span></button>
                  </td>
                </tr>
                <tr>
                  <td colspan="100%">
                    <select class="form-control" data-ng-model="selectedItem" data-ng-options="o.name for o in optimizableObjects" data-ng-change="addItem()">
                      <option value="" disabled selected>select object</option>
                    </select>
                  </td>
               </tr>
               </tbody>
              </table>
            </div>
            </div>
        `,
        controller: function($scope, $element) {

            $scope.addItem = () => {
                if (! $scope.selectedItem) {
                    return;
                }
                const m = {
                    object: $scope.selectedItem.name,
                    field: null,
                    min: -1,
                    max: 1,
                    start: 0,
                };
                $scope.field.push(m);
                $scope.selectedItem = null;
            };

            $scope.deleteItem = index => {
                $scope.field.splice(index, 1);
            };

            $scope.fieldsForObject = name => $scope.optimizableObjects[name].fields;

            $scope.fieldMin = item => {
                return appState.modelInfo(
                    $scope.optimizableObjects[item.object].type
                )[item.field][SIREPO.INFO_INDEX_MIN];
            };

            $scope.fieldMax = item => {
                return appState.modelInfo(
                    $scope.optimizableObjects[item.object].type
                )[item.field][SIREPO.INFO_INDEX_MAX];
            };

            $scope.hasUnusedFields = name => {
                const f = $scope.field.filter(x => x.name === name).map(x => x.field);
                return $scope.optimizableObjects[name].fields.filter(x => ! f.includes(x)).length;
            };

            $scope.validate = (input, item) => {
                validationService.validateInputSelector(
                    $('.rsopt-start input').eq($scope.field.indexOf(item)),
                    item.min < item.start && item.start < item.max,
                    `start must be between ${item.min} and ${item.max}`
                );
            };

            function validateItems() {
                for (const item of $scope.field) {
                    $scope.validate(null, item);
                }
            }

            $scope.$watch('field', validateItems, true);

            $scope.optimizableObjects = radiaOptimizationService.optimizableObjects();
        },
    };
});

SIREPO.app.directive('materialFormula', function(appState, panelState, plotting, radiaService, requestSender, utilities) {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
            fieldName: '=',
            info: '=',
        },
        template: `
            <div data-num-array="" data-model="model" data-field-name="fieldName" data-field="subfields" data-info="info" data-num-type="Float"></div>
        `,
        controller: function($scope) {
            const f = $scope.field;
            $scope.subfields = [
                [f[0], f[1]],
                [f[2], f[3]],
                [f[4], f[5]],
            ];
        },
    };
});

SIREPO.app.directive('pointsTable', function() {
    return {
        restrict: 'A',
        scope: {
            field: '=',
            model: '=',
        },
        template: `
          <div class="col-sm-12">
              <table class="table-condensed table-striped table-bordered">
                <thead>
                  <tr>
                    <th scope="col" data-ng-show="isExpanded">
                      <span title="click to collapse" class="glyphicon glyphicon-chevron-down" data-ng-click="toggleExpand()"></span>
                    </th>
                    <th scope="col" data-ng-hide="isExpanded">
                      <span title="click to expand" class="glyphicon glyphicon-chevron-up" data-ng-click="toggleExpand()"></span>
                    </th>
                  </tr>
                  <tr data-ng-show="isExpanded">
                    <th scope="col" style="text-align: left;">{{ model.widthAxis }}</th>
                    <th scope="col" style="text-align: left;">{{ model.heightAxis }}</th>
                  </tr>
                </thead>
                <tbody>
                <tr data-ng-show="isExpanded" data-ng-repeat="p in field">
                  <td data-ng-repeat="e in p track by $index">{{ e }}</td>
                </tr>
                </tbody>
              </table>
          </div>
        `,
        controller: function($scope) {
            $scope.isExpanded = false;
            $scope.toggleExpand = () => {
                $scope.isExpanded = ! $scope.isExpanded;
            };
        },
    };
});

SIREPO.app.directive('radiaFieldPaths', function(appState, panelState, radiaService) {

    return {
        restrict: 'A',
        scope: {
            form: '=',
            modelName: '@',
        },
        template: `
            <div class="col-md-6">
              <div data-basic-editor-panel="" data-view-name="fieldPaths"></div>
            </div>
        `,
    };
});

SIREPO.app.directive('radiaSolver', function(appState, errorService, frameCache, geometry, layoutService, panelState, persistentSimulation, radiaService, utilities, $rootScope) {

    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        template: `
            <div class="col-md-6">
                <div data-basic-editor-panel="" data-view-name="solverAnimation">
                        <div data-sim-status-panel="simState" data-start-function="startSimulation()"></div>
                        <div data-ng-show="solution">
                                <div><strong>Time:</strong> {{ solution.time }}ms</div>
                                <div><strong>Step Count:</strong> {{ solution.steps }}</div>
                                <div><strong>Max |M|: </strong> {{ solution.maxM }} A/m</div>
                                <div><strong>Max |H|: </strong> {{ solution.maxH }} A/m</div>
                        </div>
                        <div data-ng-hide="solution">No solution found</div>
                        <div class="col-sm-6 pull-right" style="padding-top: 8px;">
                            <button class="btn btn-default" data-ng-click="resetSimulation()">Reset</button>
                        </div>
                    </div>
                </div>
            </div>
        `,
        controller: function($scope) {
            let solving = false;
            $scope.simScope = $scope;
            $scope.solution = null;
            $scope.simComputeModel = $scope.modelName;
            $scope.simState = persistentSimulation.initSimulationState($scope);

            $scope.mpiCores = 0;

            $scope.model = appState.models[$scope.modelName];

            $scope.resetSimulation = () => {
                $scope.startSimulation('reset');
            };

            $scope.simHandleStatus = data => {
                if (data.error) {
                    solving = false;
                }
                if ('percentComplete' in data && ! data.error) {
                    if (data.percentComplete === 100 && ! $scope.simState.isProcessing()) {
                        $scope.solution = solutionValidForGeom() ? formatSolution(data.solution) : null;
                        if (solving) {
                            $rootScope.$broadcast('solve.complete');
                            radiaService.syncReports();
                        }
                        solving = false;
                    }
                }
            };

            $scope.startSimulation = (mode='solve') => {
                $scope.solution = null;
                appState.models[$scope.modelName].mode = mode;
                appState.models[$scope.modelName].objects = appState.clone(appState.models.geometryReport.objects);
                solving = true;
                $scope.simState.saveAndRunSimulation([$scope.modelName, 'simulation']);
            };

            function formatSolution(s) {
                if (! s) {
                    return null;
                }
                return {
                    time: utilities.roundToPlaces(1000 * s.time, 3),
                    steps: s.steps,
                    maxM: utilities.roundToPlaces(s.maxM, 4),
                    maxH: utilities.roundToPlaces(s.maxH, 4),
                };
            }

            function solutionValidForGeom() {
                return appState.deepEquals(
                    appState.models[$scope.modelName].objects,
                    appState.models.geometryReport.objects
                );
            }
        },
    };
});

SIREPO.app.directive('radiaViewer', function(panelState, utilities) {
    return {
        restrict: 'A',
        transclude: true,
        scope: {
            modelName: '@',
            viz: '<',
        },
        template: `
            <div class="col-md-6">
                <div class="panel panel-info" id="sr-magnetDisplay-basicEditor">
                    <div class="panel-heading clearfix" data-panel-heading="Magnet Viewer" data-view-name="{{ modelName }}" data-is-report="true" data-model-key="modelName"></div>
                    <div class="panel-body" data-ng-if="! panelState.isHidden(modelName)">
                        <div data-radia-viewer-content="" data-model-name="{{ modelName }}" data-viz="viz"></div>
                    </div>
                </div>
            </div>
        `,
        controller: function($scope) {
            $scope.panelState = panelState;
        },
    };
});

SIREPO.app.directive('radiaViewerContent', function(appState, geometry, panelState, plotting, plotToPNG, radiaService, radiaVtkUtils, utilities, vtkUtils, $rootScope) {

    return {
        restrict: 'A',
        transclude: true,
        scope: {
            modelName: '@',
        },
        template: `
            <div data-advanced-editor-pane="" data-view-name="modelName" data-want-buttons="true" data-field-def="basic" data-model-data="modelData" data-parent-controller="parentController"></div>
            <div data-ng-transclude="">
                <div data-vtk-display="" class="vtk-display" data-ng-class="{'col-sm-11': isViewTypeFields()}" style="padding-right: 0" data-show-border="true" data-model-name="{{ modelName }}" data-event-handlers="eventHandlers" data-enable-axes="true" data-axis-cfg="axisCfg" data-axis-obj="axisObj" data-enable-selection="true" data-reset-side="x"></div>
                <div class="col-sm-1" style="padding-left: 0" data-ng-if="isViewTypeFields()">
                    <div class="colorbar"></div>
                </div>
            </div>
        `,
        controller: function($scope, $element) {
            $scope.axisObj = null;
            $scope.defaultColor = "#ff0000";
            $scope.mode = null;

            $scope.isViewTypeFields = () =>
                (appState.models.magnetDisplay || {}).viewType === SIREPO.APP_SCHEMA.constants.viewTypeFields;

            $scope.isViewTypeObjects = () =>
                (appState.models.magnetDisplay || {}).viewType === SIREPO.APP_SCHEMA.constants.viewTypeObjects;

            const LINEAR_SCALE_ARRAY = 'linear';
            const LOG_SCALE_ARRAY = 'log';
            const ORIENTATION_ARRAY = 'orientation';
            const FIELD_ATTR_ARRAYS = [LINEAR_SCALE_ARRAY, LOG_SCALE_ARRAY, ORIENTATION_ARRAY];

            const PICKABLE_TYPES = [
                SIREPO.APP_SCHEMA.constants.geomTypePolys,
                SIREPO.APP_SCHEMA.constants.geomTypeVectors
            ];

            const SCALAR_ARRAY = 'scalars';

            let actorInfo = {};
            const alphaDelegate = radiaService.alphaDelegate();
            alphaDelegate.update = setAlpha;
            let cm = new SIREPO.VTK.CoordMapper();
            let colorbar = null;
            let colorbarPtr = null;
            let colorScale = null;
            let cPicker = null;
            const displayFields = [
                'fieldPaths.paths',
                'magnetDisplay.viewType',
                'magnetDisplay.fieldType',
            ];
            let cachedDisplayVals = appState.clone(getDisplayVals());
            const fieldDisplayModelFields = {
                'fieldDisplay': ['colorMap', 'scaling'],
            };
            const fieldDisplayFields = fieldDisplayModelFields.fieldDisplay.map(f => `fieldDisplay.${f}`);

            let initDone = false;
            let ptPicker = null;
            let renderer = null;
            let savedObj = null;
            let selectedColor = [];
            let selectedInfo = null;
            let selectedObj = null;
            let selectedOutline = null;
            let selectedPointId = -1;
            let sceneData = {};


            const vectInArrays = [{
                location: vtk.Common.DataModel.vtkDataSet.FieldDataTypes.COORDINATE,
            }];

            const vectOutArrays = [{
                    location: vtk.Common.DataModel.vtkDataSet.FieldDataTypes.POINT,
                    name: SCALAR_ARRAY,
                    dataType: 'Uint8Array',
                    attribute: vtk.Common.DataModel.vtkDataSetAttributes.AttributeTypes.SCALARS,
                    numberOfComponents: 3,
                },
            ];

            // these objects are used to set various vector properties
            const vectArrays = {
                input: vectInArrays,
                output: vectOutArrays,
            };
            let vtkSelection = {};
            const watchFields = displayFields.concat(fieldDisplayFields);

            FIELD_ATTR_ARRAYS.forEach(n => {
                vectOutArrays.push({
                    location: vtk.Common.DataModel.vtkDataSet.FieldDataTypes.POINT,
                    name: n,
                    dataType: 'Float32Array',
                    numberOfComponents: 3,
                });
            });

            // stash the actor and associated info to avoid recalculation
            function addActor(id, group, actor, geomType, pickable) {
                const pData = actor.getMapper().getInputData();
                const info = {
                    actor: actor,
                    colorIndices: [],
                    group: group || 0,
                    id: id,
                    pData: pData,
                    scalars: pData.getCellData().getScalars(),
                    type: geomType,
                };

                if (info.scalars) {
                    info.colorIndices = utilities.indexArray(numColors(pData, geomType)).map(i => 4 * i);
                }
                actorInfo[id] = info;

                $scope.vtkScene.addActor(actor);
                if (pickable) {
                    ptPicker.addPickList(actor);
                }
                return info;
            }

            function vectorScaleFactor(bounds) {
                return 0.035 * Math.max(
                    Math.abs(bounds[1] - bounds[0]),
                    Math.abs(bounds[3] - bounds[2]),
                    Math.abs(bounds[5] - bounds[4])
                );
            }

            function buildScene() {
                // scene -> multiple data -> multiple actors
                let name = sceneData.name;
                let data = sceneData.data;

                $scope.vtkScene.removeActors();
                let didModifyGeom = false;
                for (let i = 0; i < data.length; ++i) {

                    // gName is for selection display purposes
                    const gName = `${name}.${i}`;
                    let sceneDatum = data[i];
                    let radiaId = sceneDatum.id;
                    let objId = (sceneData.idMap || {})[radiaId] || radiaId;

                    // trying a separation into an actor for each data type, to better facilitate selection
                    for (const t of radiaVtkUtils.GEOM_TYPES) {
                        const d = sceneDatum[t];
                        if (! d || ! d.vertices || ! d.vertices.length) {
                            continue;
                        }
                        const isPoly = t === SIREPO.APP_SCHEMA.constants.geomTypePolys;
                        const isLine = t === SIREPO.APP_SCHEMA.constants.geomTypeLines;
                        let gObj = radiaService.getObject(objId) || {};
                        let gColor = gObj.color ? vtk.Common.Core.vtkMath.hex2float(gObj.color) : null;
                        // use black for edges
                        //TODO(mvk): possibly use high contrast so dark objects have white edges
                        if (gColor && isLine) {
                            gColor = [0, 0, 0];
                        }
                        // use colors from Radia for groups
                        if (gObj.members) {
                            gColor = null;
                        }

                        const pData = radiaVtkUtils.objToPolyData(sceneDatum, [t], gColor).data;
                        let bundle = null;
                        if (radiaVtkUtils.GEOM_OBJ_TYPES.includes(t)) {
                            bundle = cm.buildActorBundle();
                            bundle.mapper.setInputData(pData);
                        }
                        else {
                            const vectorCalc = vtk.Filters.General.vtkCalculator.newInstance();
                            vectorCalc.setFormula(getVectFormula(d, appState.models.fieldDisplay.colorMap));
                            vectorCalc.setInputData(pData);

                            const mapper = vtk.Rendering.Core.vtkGlyph3DMapper.newInstance();
                            mapper.setInputConnection(vectorCalc.getOutputPort(), 0);
                            mapper.setInputConnection(
                                vtk.Filters.Sources.vtkArrowSource.newInstance().getOutputPort(), 1
                            );
                            mapper.setOrientationArray(ORIENTATION_ARRAY);

                            // this scales by a constant - the default is to use scalar data
                            mapper.setScaleFactor(vectorScaleFactor(sceneData.bounds));
                            mapper.setScaleModeToScaleByConstant();
                            mapper.setColorModeToDefault();
                            bundle = cm.buildActorBundle();
                            bundle.setMapper(mapper);
                        }
                        bundle.actor.getProperty().setEdgeVisibility(isPoly);
                        bundle.actor.getProperty().setLighting(isPoly);
                        let info = addActor(objId, gName, bundle.actor, t, PICKABLE_TYPES.includes(t));
                        gColor = getColor(info);
                        if (! gObj.center || ! gObj.size) {
                            const b = bundle.actor.getBounds();
                            gObj.center = [0.5 * (b[1] + b[0]), 0.5 * (b[3] + b[2]), 0.5 * (b[5] + b[4])];
                            gObj.size = [Math.abs(b[1] - b[0]), Math.abs(b[3] - b[2]), Math.abs(b[5] - b[4])];
                            didModifyGeom = true;
                        }
                        if (
                            t === SIREPO.APP_SCHEMA.constants.geomTypeLines &&
                            appState.models.magnetDisplay.viewType === SIREPO.APP_SCHEMA.constants.viewTypeFields
                        ) {
                            setEdgeColor(info, [216, 216, 216]);
                        }
                    }
                }

                const boundsBox = $scope.vtkScene.sceneBoundingBox();
                const bounds = boundsBox.actor.getBounds();
                $scope.vtkScene.addActor(boundsBox.actor);
                $scope.axisObj = new SIREPO.VTK.ViewPortBox(boundsBox.source, $scope.vtkScene.renderer);

                radiaService.objBounds = bounds;

                const acfg = {};
                const scale = SIREPO.APP_SCHEMA.constants.objectScale;
                geometry.basis.forEach(function (dim, i) {
                    acfg[dim] = {};
                    acfg[dim].dimLabel = dim;
                    acfg[dim].label = dim + ' [m]';
                    acfg[dim].max = scale * bounds[2 * i + 1];
                    acfg[dim].min = scale * bounds[2 * i];
                    acfg[dim].numPoints = 2;
                    acfg[dim].screenDim = dim === 'z' ? 'y' : 'x';
                    acfg[dim].showCentral = true;
                });
                $scope.axisCfg = acfg;

                if (didModifyGeom) {
                    appState.saveQuietly('geometryReport');
                }
                updateLayout();
                setAlpha();
                setBgColor();
                enableWatchFields(true);
            }

            function didDisplayValsChange() {
                const v = getDisplayVals();
                for (let i = 0; i < v.length; ++i) {
                    if (! appState.deepEquals(v[i], cachedDisplayVals[i])) {
                        return true;
                    }
                }
                return false;
            }

            function enableWatchFields(doEnable) {
                watchFields.forEach(wf=> {
                    const mf = appState.parseModelField(wf);
                    panelState.enableField(mf[0], mf[1], doEnable);
                });
            }

            function getDisplayVals() {
                return displayFields.map(f => {
                    const m = appState.parseModelField(f);
                    return appState.models[m[0]][m[1]];
                });
            }

            function getActor(id) {
                return (getActorInfo(id) || {}).actor;
            }

            function getActorInfo(id) {
                return actorInfo[id];
            }

            function getActorInfoOfType(typeName) {
                return Object.keys(actorInfo)
                    .filter(id => getActorInfo(id).type === typeName)
                    .map(id => getActorInfo(id));
            }

            function getActorsOfType(typeName) {
                return getActorInfoOfType(typeName).map(info => info.actor);
            }

            function getColor(info) {
                const s = info.scalars;
                if (! s) {
                    return null;
                }
                const inds = info.colorIndices;
                if (! inds) {
                    return null;
                }
                return s.getData().slice(inds[0], inds[0] + 3);
            }

            function getInfoForActor(actor) {
                for (const n in actorInfo) {
                    if (getActor(n) === actor) {
                        return getActorInfo(n);
                    }
                }
            }

            // used to create array of arrows (or other objects) for vector fields
            // change to use magnitudes and color locally
            function getVectFormula(vectors, colorMapName) {
                const cmap = plotting.colorMapOrDefault(
                    colorMapName,
                    appState.fieldProperties('fieldDisplay', 'colorMap').default
                );
                const norms = utilities.normalize(vectors.magnitudes);
                let logMags = vectors.magnitudes.map(function (n) {
                    return Math.log(n);
                });

                // get log values back into the original range, so that the extremes have the same
                // size as a linear scale
                const minLogMag = utilities.arrayMin(logMags);
                const maxLogMag = utilities.arrayMax(logMags);
                const minMag = utilities.arrayMin(vectors.magnitudes);
                const maxMag = utilities.arrayMax(vectors.magnitudes);
                colorScale = plotting.colorScale(minMag, maxMag, cmap);

                logMags = logMags.map(n => minMag + (n - minLogMag) * (maxMag - minMag) / (maxLogMag - minLogMag));

                return {
                    getArrays: inputDataSets => vectArrays,
                    evaluate: (arraysIn, arraysOut) => {
                        const coords = arraysIn.map(d => d.getData())[0];
                        const o = arraysOut.map(d => d.getData());
                        // note these arrays already have the correct length, so we need to set elements, not append
                        const orientation = o[getVectOutIndex(ORIENTATION_ARRAY)];
                        const linScale = o[getVectOutIndex(LINEAR_SCALE_ARRAY)].fill(1.0);
                        const logScale = o[getVectOutIndex(LOG_SCALE_ARRAY)].fill(1.0);
                        const scalars = o[getVectOutIndex(SCALAR_ARRAY)];

                        for (let i = 0; i < coords.length / 3; ++i) {
                            let c = [0, 0, 0];
                            if (cmap.length) {
                                const rgb = d3.rgb(colorScale(norms[i]));
                                c = [rgb.r, rgb.g, rgb.b];
                            }
                            // scale arrow length (object-local x-direction) only
                            // this can stretch/squish the arrowhead though so the actor may have to adjust the ratio
                            linScale[3 * i] = vectors.magnitudes[i];
                            logScale[3 * i] = logMags[i];
                            for (let j = 0; j < 3; ++j) {
                                const k = 3 * i + j;
                                orientation[k] = vectors.directions[k];
                                scalars[k] = c[j];
                            }
                        }

                        arraysOut.forEach(x => {
                            x.modified();
                        });
                    },
                };
            }

            function getVectOutIndex(name) {
                for (const vIdx in vectArrays.output) {
                    if (vectArrays.output[vIdx].name === name) {
                        return vIdx;
                    }
                }
                throw new Error('No vector array named ' + name  + ': ' + vectArrays.output);
            }

            function getVectorInfo(point, vect, units) {
                const pt = [];
                point.forEach(c => {
                    pt.push(utilities.roundToPlaces(c, 2));
                });
                const val = Math.hypot(vect[0], vect[1], vect[2]);
                const theta = 180 * Math.acos(vect[2] / (val || 1)) / Math.PI;
                const phi = 180 * Math.atan2(vect[1], vect[0]) / Math.PI;
                return isNaN(val) ?
                    '--' :
                    utilities.roundToPlaces(val, 4) + units +
                    '  θ ' + utilities.roundToPlaces(theta, 2) +
                    '°  φ ' + utilities.roundToPlaces(phi, 2) +
                    '°  at (' + pt + ')';
            }

            function handlePick(callData) {

                function getClosestActor(pickedActors) {
                    for (const a of pickedActors) {
                        const i = getInfoForActor(a);
                        if (i) {
                            return [a, i];
                        }
                    }
                    return [null, null];
                }

                if (renderer !== callData.pokedRenderer) {
                    return;
                }

                // regular clicks are generated when spinning the scene - we'll select/deselect with ctrl-click
                if (! callData.controlKey) {
                    return;
                }

                const pos = callData.position;
                const point = [pos.x, pos.y, 0.0];
                ptPicker.pick(point, renderer);
                cPicker.pick(point, renderer);
                const pid = ptPicker.getPointId();

                // cell id is "closest cell within tolerance", meaning a single value, though
                // we may get multiple actors
                const cid = cPicker.getCellId();

                let picker = null;
                if (appState.models.magnetDisplay.viewType === SIREPO.APP_SCHEMA.constants.viewTypeObjects && cid >= 0) {
                    picker = cPicker;
                }
                else if (appState.models.magnetDisplay.viewType === SIREPO.APP_SCHEMA.constants.viewTypeFields && pid >= 0) {
                    picker = ptPicker;
                }
                if (! picker) {
                    return;
                }

                let selectedValue = Number.NaN;
                let highlightVectColor = [255, 0, 0];

                vtkSelection = {};
                const [actor, info] = getClosestActor(picker.getActors());
                selectedInfo = info;
                if (! info || ! info.pData) {
                    return;
                }

                const pts = info.pData.getPoints();

                // TODO(mvk): attach pick functions to actor info?
                // vectors
                if (info.type === SIREPO.APP_SCHEMA.constants.geomTypeVectors) {
                    const n = pts.getNumberOfComponents();
                    const f = actor.getMapper().getInputConnection(0).filter;
                    const linArr = f.getOutputData().getPointData().getArrayByName(LINEAR_SCALE_ARRAY);
                    if (! linArr) {
                        return;
                    }
                    selectedValue = linArr.getData()[pid * linArr.getNumberOfComponents()];

                    const oArr = f.getOutputData().getPointData().getArrayByName(ORIENTATION_ARRAY);
                    const oid = pid * oArr.getNumberOfComponents();
                    const o = oArr.getData().slice(oid, oid + oArr.getNumberOfComponents());
                    let v = o.map(dir => selectedValue * dir);

                    const sArr = f.getOutputData().getPointData().getArrayByName(SCALAR_ARRAY);
                    const ns = sArr.getNumberOfComponents();
                    const sid = pid * ns;
                    const sc = sArr.getData().slice(sid, sid + ns);

                    selectedColor.forEach(function (c, i) {
                        sArr.getData()[selectedPointId * ns + i] = c;
                    });
                    if (pid === selectedPointId) {
                        selectedPointId = -1;
                        selectedColor = [];
                        selectedValue = utilities.arrayMin(linArr.getData());
                        v = [];
                    }
                    else {
                        highlightVectColor.forEach(function (c, i) {
                            sArr.getData()[sid + i] = c;
                        });
                        selectedPointId = pid;
                        selectedColor = sc;
                    }
                    info.pData.modified();

                    vtkSelection = {
                        info: getVectorInfo(point, v, sceneData.data[0].vectors.units),
                    };
                    colorbarPtr.pointTo(selectedValue);
                }

                // objects
                else if (info.type === SIREPO.APP_SCHEMA.constants.geomTypePolys) {
                    const j = info.colorIndices[cid];
                    selectedColor = info.scalars.getData().slice(j, j + 3);

                    const g = radiaService.getObject(info.id);
                    if (selectedObj === g) {
                        selectedObj = null;
                        savedObj = null;
                    }
                    else {
                        selectedObj = g;
                        savedObj = appState.clone(g);
                        selectedOutline = vtk.Filters.General.vtkOutlineFilter.newInstance();
                    }

                    for (const id in actorInfo) {
                        setEdgeColor(
                            getActorInfo(id),
                            selectedObj && sharesGroup(getActor(id), actor) ? selectedColor.map(c =>  255 - c) : [0, 0, 0]
                        );
                    }

                    $scope.radiaObject = selectedObj;
                    vtkSelection = {
                        info: selectedObj ? selectedObj.name : '--',
                        model: selectedObj ? {
                            getData: function () {
                                return selectedObj;
                            },
                            modelKey: 'radiaObject',
                        } : null,
                    };
                }

                // for some reason scope changes are not immediately propagating, so we'll force the issue -
                // apply() or digest() cause infinite digest loops
                $scope.$broadcast('vtk.selected', vtkSelection);
            }

            function hasPaths() {
                return appState.models.fieldPaths.paths && appState.models.fieldPaths.paths.length;
            }

            function init() {
                $scope.$broadcast('sliderParent.ready', appState.models.magnetDisplay);
                if (! renderer) {
                    throw new Error('No renderer!');
                }

                const t = 30;
                colorbar = Colorbar()
                    .margin({top: 5, right: t + 10, bottom: 0, left: 0})
                    .thickness(t)
                    .orient('vertical')
                    .barlength($('.vtk-canvas-holder').height())
                    .origin([0, 0]);

                const ca = vtk.Rendering.Core.vtkAnnotatedCubeActor.newInstance();
                vtk.Rendering.Core.vtkAnnotatedCubeActor.Presets.applyPreset('default', ca);
                const df = ca.getDefaultStyle();
                df.fontFamily = 'Arial';
                df.faceRotation = 45;
                ca.setDefaultStyle(df);

                $scope.vtkScene.setMarker(
                    SIREPO.VTK.VTKUtils.buildOrientationMarker(
                        ca,
                        $scope.vtkScene.renderWindow.getInteractor(),
                        vtk.Interaction.Widgets.vtkOrientationMarkerWidget.Corners.TOP_RIGHT
                    )
                );
                updateViewer();
                updateLayout();
            }

            function numColors(polyData, type) {
                if (radiaVtkUtils.GEOM_OBJ_TYPES.indexOf(type) < 0) {
                    return 0;
                }
                if (type === SIREPO.APP_SCHEMA.constants.geomTypeLines) {
                    return numDataColors(polyData.getLines().getData());
                }
                if (type === SIREPO.APP_SCHEMA.constants.geomTypePolys) {
                    return numDataColors(polyData.getPolys().getData());
                }
            }

            // lines and poly data arrays look like:
            //    [<num vertices for obj 0>, <vertex 0, 0>, ...,]
            function numDataColors(data) {
                let i = 0;
                let j = 0;
                while (i < data.length) {
                    i += (data[i] + 1);
                    ++j;
                }
                return j;
            }

            function setAlpha() {
                if (! renderer) {
                    return;
                }
                const alpha = appState.models[$scope.modelName].alpha;
                for (const id in actorInfo) {
                    let info = actorInfo[id];
                    if (! info.scalars) {
                        info.actor.getProperty().setOpacity(alpha);
                        continue;
                    }
                    setColor(
                        info,
                        SIREPO.APP_SCHEMA.constants.geomTypePolys,
                        null,
                        Math.floor(255 * alpha)
                    );
                }
                $scope.vtkScene.render();
            }

            function setBgColor() {
                $scope.vtkScene.setBgColor(appState.models.magnetDisplay.bgColor);
            }

            function setColor(info, type, color, alpha) {
                if (angular.isUndefined(alpha)) {
                    alpha = 255;
                }
                const s = info.scalars;
                if (! s) {
                    return;
                }
                if (type !== info.type) {
                    return;
                }
                const colors = s.getData();
                const nc = s.getNumberOfComponents();
                let i = 0;
                const inds = info.colorIndices || [];
                for (let j = 0; j < inds.length && i < s.getNumberOfValues(); ++j) {
                    if (color) {
                        for (let k = 0; k < nc - 1; ++k) {
                            colors[inds[j] + k] = color[k];
                        }
                    }
                    colors[inds[j] + nc - 1] = alpha;
                    i += nc;
                }
                info.pData.modified();
            }

            function setColorMap() {
                getActorsOfType(SIREPO.APP_SCHEMA.constants.geomTypeVectors).forEach(actor => {
                    actor.getMapper().getInputConnection(0).filter
                        .setFormula(getVectFormula(
                            sceneData.data[0].vectors,
                            appState.models.fieldDisplay.colorMap
                        ));
                });
                if (colorScale) {
                    colorbar.scale(colorScale);
                    colorbarPtr = d3.select('.colorbar').call(colorbar);
                }
                $scope.vtkScene.render();
            }

            function setEdgeColor(info, color) {
                if (! info ) {
                    return;
                }
                if (! renderer) {
                    return;
                }
                info.actor.getProperty().setEdgeColor(...color);
                setColor(info, SIREPO.APP_SCHEMA.constants.geomTypeLines, color);
                $scope.vtkScene.render();
            }

            function setScaling() {
                getActorsOfType(SIREPO.APP_SCHEMA.constants.geomTypeVectors).forEach(actor => {
                    const mapper = actor.getMapper();
                    mapper.setScaleFactor(vectorScaleFactor(renderer.computeVisiblePropBounds()));
                    const vs = appState.models.fieldDisplay.scaling;
                    if (vs === 'uniform') {
                        mapper.setScaleModeToScaleByConstant();
                    }
                    if (vs === 'linear') {
                        mapper.setScaleArray(LINEAR_SCALE_ARRAY);
                        mapper.setScaleModeToScaleByComponents();
                    }
                    if (vs === 'log') {
                        mapper.setScaleArray(LOG_SCALE_ARRAY);
                        mapper.setScaleModeToScaleByComponents();
                    }
                });
                $scope.vtkScene.render();
            }

            function setupSceneData(data) {
                radiaService.saveGeometry(false, true);
                cachedDisplayVals = appState.clone(getDisplayVals());
                $rootScope.$broadcast('radiaViewer.loaded');
                $rootScope.$broadcast('vtk.hideLoader');
                sceneData = data;
                buildScene();
                if (! initDone) {
                    initDone = true;
                    $scope.vtkScene.setCam();
                }
            }

            function sharesGroup(actor1, actor2) {
                if (! actor1 || ! actor2) {
                    return false;
                }
                return getInfoForActor(actor1).group === getInfoForActor(actor2).group;
            }

            function updateLayout() {
                if ($scope.isViewTypeObjects())  {
                    d3.select('svg.colorbar').remove();
                }
                if ($scope.isViewTypeFields())  {
                    setColorMap();
                    setScaling();
                }
                panelState.showField(
                    'magnetDisplay',
                    'fieldType',
                    $scope.isViewTypeFields()
                );
                panelState.showField(
                    'magnetDisplay',
                    'alpha',
                    $scope.isViewTypeObjects()
                );
                radiaService.pointFieldTypes.forEach(ft => {
                    panelState.showEnum('magnetDisplay', 'fieldType', ft, hasPaths());
                });
                fieldDisplayFields.forEach(function (f) {
                    const mf = appState.parseModelField(f);
                    panelState.showField(mf[0], mf[1], $scope.isViewTypeFields());
                });
            }

            function updateMarker() {
                $scope.vtkScene.isMarkerEnabled = appState.models.magnetDisplay.showMarker === '1';
                $scope.vtkScene.refreshMarker();
            }

            function updateViewer(doShowLoader=false) {
                const c = didDisplayValsChange();
                sceneData = {};
                actorInfo = {};
                radiaService.objBounds = null;
                if (doShowLoader || c || ! initDone) {
                    $rootScope.$broadcast('vtk.showLoader');
                }
                panelState.clear('geometryReport');
                panelState.requestData('geometryReport', setupSceneData, c);
            }

            $scope.eventHandlers = {
                keypress: function (evt) {
                    // do nothing?  Stops vtk from changing render based on key presses
                },
            };

            appState.whenModelsLoaded($scope, function () {
                $scope.model = appState.models[$scope.modelName];
                appState.watchModelFields($scope, watchFields, updateLayout);
                appState.watchModelFields($scope, ['magnetDisplay.bgColor'], setBgColor);
                appState.watchModelFields($scope, ['magnetDisplay.showMarker'], updateMarker);
                panelState.enableField('geometryReport', 'name', ! appState.models.simulation.isExample);
            });

            $scope.$on('vtk-init', (e, d) => {
                $scope.vtkScene = d;
                renderer = $scope.vtkScene.renderer;
                cPicker = vtk.Rendering.Core.vtkCellPicker.newInstance();
                cPicker.setPickFromList(false);
                ptPicker = vtk.Rendering.Core.vtkPointPicker.newInstance();
                ptPicker.setPickFromList(true);
                ptPicker.initializePickList();
                $scope.vtkScene.renderWindow.getInteractor().onLeftButtonPress(handlePick);
                init();
                plotToPNG.initVTK($element, $scope.vtkScene.renderer);
            });

            $scope.$on('radiaObject.changed', function(e) {
                radiaService.saveGeometry(true, false);
            });

            $scope.$on('fieldPaths.saved', () => {
                if (appState.models.magnetDisplay.viewType === 'fields') {
                    updateViewer(true);
                }
            });

            $scope.$watch('radiaObject.color', (color) => {
                if(! color) {
                    return;
                }
                setColor(
                    selectedInfo,
                    SIREPO.APP_SCHEMA.constants.geomTypePolys,
                    vtkUtils.floatToRGB((SIREPO.VTK.VTKUtils.colorToFloat(color)))
                );
                setAlpha();
            });

            // must handle this separately
            $scope.$on('cancelChanges', (e, d) => {
                if (d !== 'radiaObject') {
                    return;
                }
                if (savedObj) {
                    $scope.radiaObject.color = savedObj.color;
                    $scope.radiaObject.name = savedObj.name;
                }
            });

            $scope.$on('magnetDisplay.saved', () => {
                if (didDisplayValsChange()) {
                    updateViewer();
                }
            });

            $scope.$on('solve.complete', (e, d) => {
                if (! initDone) {
                    return;
                }
                if (appState.models.magnetDisplay.viewType === 'fields') {
                    updateViewer(true);
                }
            });

            $scope.$on('$destroy', () => {
                $element.off();
            });

        },
    };
});

SIREPO.app.directive('scriptableArray', function(appState, panelState, radiaVariableService, utilities) {
    return {
        restrict: 'A',
        scope: {
            field: '=',
            fieldName: '=',
            info: '=',
            model: '=',
            modelName: '=',
        },
        template: `
            <div>
                <div data-ng-repeat="v in model[fieldName] track by $index" style="display: inline-block;">
                    <label data-text-with-math="info[4][$index]" data-is-dynamic="isDynamic(info[4][$index])" style="margin-right: 1ex"></label>
                    <input data-rpn-value="" data-ng-model="field[$index]" class="form-control sr-number-list {{ scriptableClass($index) }}"  style="text-align: right" data-lpignore="true" data-ng-required="true" />
                </div>
                <div data-rpn-static="" data-model="model" data-field="fieldName" data-is-busy="isBusy" data-is-error="isError"></div>
            </div>
        `,
        controller: ($scope, $element) => {
            $scope.isDynamic = label => ! ! label.match(/{{\s*.+\s*}}/);
            $scope.list = radiaVariableService.searchableVariables();

            $scope.scriptableClass = index => `${$scope.modelName}-${$scope.fieldName}-${index}-scriptable`;

            let search = [];
            panelState.waitForUI(() => {
                $scope.field.forEach((f, i) => {
                    search.push(utilities.buildSearch($scope, $element, $scope.scriptableClass(i), true));
                });
            });
        },
        link: (scope, element) => {
            // add an icon to the label
            angular.element($('div[data-ng-controller]').eq(0))
                .controller('ngController')
                .decorateLabelWithIcon(element, 'list-alt', 'scriptable');

            // adjust the computed display to line up with the first label
            $(element).find('div[data-rpn-static] > div').css('margin-left', 0);
        },
    };
});

SIREPO.app.directive('scriptableField', function(appState, panelState, radiaVariableService, utilities) {
    return {
        restrict: 'A',
        scope: {
            field: '=',
            fieldName: '<',
            info: '<',
            model: '=',
            modelName: '<',
        },
        template: `
            <div class="col-sm-3">
                <input data-rpn-value="" data-is-error="isError" data-ng-model="model[fieldName]" class="{{ scriptableClass() }} form-control" style="text-align: right"  data-ng-required="true" />
            </div>
            <div class="col-sm-2">
                <span data-rpn-static="" data-model="model" data-field="fieldName" data-is-busy="isBusy" data-is-error="isError"></span>
            </div>
        `,
        controller: ($scope, $element) => {
            $scope.list = radiaVariableService.searchableVariables();

            $scope.isDynamic = label => ! ! label.match(/{{\s*.+\s*}}/);

            $scope.scriptableClass = () => `${$scope.modelName}-${$scope.fieldName}-scriptable`;

            let search = null;
            panelState.waitForUI(() => {
                search = utilities.buildSearch($scope, $element, $scope.scriptableClass(), true);
            });

        },
        link: (scope, element) => {
            // add an icon to the label
            angular.element($('div[data-ng-controller]').eq(0))
                .controller('ngController')
                .decorateLabelWithIcon(element, 'list-alt', 'scriptable with python expression');
        },
    };
});

SIREPO.app.factory('radiaVtkUtils', function(utilities) {

    const self = {};

    self.GEOM_OBJ_TYPES = [
        SIREPO.APP_SCHEMA.constants.geomTypeLines,
        SIREPO.APP_SCHEMA.constants.geomTypePolys,
    ];
    self.GEOM_TYPES = [
        SIREPO.APP_SCHEMA.constants.geomTypeLines,
        SIREPO.APP_SCHEMA.constants.geomTypePolys,
        SIREPO.APP_SCHEMA.constants.geomTypeVectors,
    ];

    self.objBounds = json => {
        const mins = [Number.MAX_VALUE, Number.MAX_VALUE, Number.MAX_VALUE];
        const maxs = [-Number.MAX_VALUE, -Number.MAX_VALUE, -Number.MAX_VALUE];

        self.GEOM_TYPES.forEach(type => {
            if (! json[type]) {
                return;
            }
            const pts = json[type].vertices;

            function modf(j) {
                return (p, i) => i % 3 === j;
            }

            for (let j = 0; j < 3; ++j) {
                const c = pts.filter(modf(j));
                mins[j] =  Math.min(mins[j], utilities.arrayMin(c));
                maxs[j] =  Math.max(maxs[j], utilities.arrayMax(c));
            }
        });

        return [mins[0], maxs[0], mins[1], maxs[1], mins[2], maxs[2]];
    };

    self.objToPolyData = (json, includeTypes, color) => {

        const colors = [];
        let points = [];
        const tData = {};

        if (! includeTypes || includeTypes.length === 0) {
            includeTypes = self.GEOM_TYPES;
        }

        const typeInfo = {};
        self.GEOM_TYPES.forEach(type => {
            typeInfo[type] = {};
            if (! includeTypes.includes(type)) {
                return;
            }

            const t = json[type];
            if (! t || json[type].vertices.length === 0) {
                return;
            }

            // may not always be colors in the data
            const c = t.colors || [];
            for (let i = 0; i < c.length; ++i) {
                let cc = (color || [])[i % 3];
                if (! cc && cc !== 0) {
                    cc = c[i];
                }
                colors.push(Math.floor(255 * cc));
                if (i % 3 === 2) {
                    colors.push(255);
                }
            }

            const tArr = [];
            const tOffset = points.length / 3;
            typeInfo[type].offset = tOffset;
            points = points.concat(t.vertices);
            let tInd = 0;
            const tInds = utilities.indexArray(t.vertices.length / 3);
            t.lengths.forEach(len => {
                tArr.push(len);
                for (let j = 0; j < len; ++j) {
                    tArr.push(tInds[tInd++] + tOffset);
                }
            });
            if (tArr.length) {
                tData[type] = new window.Uint32Array(tArr);
            }

        });

        points = new window.Float32Array(points);

        const pd = vtk.Common.DataModel.vtkPolyData.newInstance();
        pd.getPoints().setData(points, 3);

        if (tData.lines) {
            pd.getLines().setData(tData.lines);
        }
        if (tData.polygons) {
            pd.getPolys().setData(tData.polygons, 1);
        }

        pd.getCellData().setScalars(vtk.Common.Core.vtkDataArray.newInstance({
            numberOfComponents: 4,
            values: colors,
            dataType: vtk.Common.Core.vtkDataArray.VtkDataTypes.UNSIGNED_CHAR
        }));

        pd.buildCells();

        return {data: pd, typeInfo: typeInfo};
    };

    self.vectorsToPolyData = json => {
        const pd = vtk.Common.DataModel.vtkPolyData.newInstance();
        pd.getPoints().setData(new window.Float32Array(json.vectors.vertices), 3);
        return pd;
    };

    return self;
});

SIREPO.app.directive('shapeButton', function(appState, geometry, panelState, plotting, radiaService, utilities) {

    const inset = 1;

    let shapes = {};
    let w = 0;
    let h = 0;
    for (const name in SIREPO.APP_SCHEMA.constants.geomObjShapes) {
        const s = SIREPO.APP_SCHEMA.constants.geomObjShapes[name];
        let b = geometry.coordBounds(s.points);
        w = Math.max(w, Math.abs(b[0].max - b[0].min));
        h = Math.max(h, Math.abs(b[1].max - b[1].min));
        shapes[name] = new SIREPO.DOM.SVGPath(name, s.points, [inset, inset], s.doClose, s.stroke, s.fill);
    }
    let btn = new SIREPO.DOM.SVGShapeButton('sr-shape-edit-btn', (Math.max(w, h) + 2 * inset), 'editShape');
    btn.addAttribute('title', 'Click to edit');

    return {
        restrict: 'A',
        scope: {
            modelName: '=',
            fieldClass: '=',
        },
        template: `
          <div data-ng-class="fieldClass">
            ${btn.toTemplate()}
          </div>
        `,
        controller: function($scope, $element) {
            plotting.setupSelector($scope, $element);

            $scope.editShape = () => {
                panelState.showModalEditor('objectShape');
            };

            function loadImage() {
                btn.setShape(updateShape());
            }

            function updateShape() {
                const o = appState.models[$scope.modelName];
                const s = shapes[o.type] || shapes.cuboid;
                s.setFill(o.color);
                const inds = radiaService.getAxisIndices();
                const ar = o.size[inds.width] / o.size[inds.height];
                s.setScales([
                    ar >= 1 ? ar : 1.0,
                    ar >= 1 ? 1.0 : ar
                ]);
                s.update();
                return s;
            }

            $scope.$on(`${$scope.modelName}.changed`, loadImage);

            loadImage();
        },
    };
});

SIREPO.app.directive('shapeSelector', function(appState, panelState, plotting, radiaService, utilities) {

    const availableShapes = ['cuboid', 'cylinder', 'ell', 'cee', 'jay', 'extrudedPoints', 'stl'];
    const sel = new SIREPO.DOM.UISelect('', [
        new SIREPO.DOM.UIAttribute('data-ng-model', 'field'),
    ]);
    sel.addClasses('form-control');
    sel.addOptions(SIREPO.APP_SCHEMA.enum.ObjectType
        .filter(o => availableShapes.indexOf(o[0]) >= 0)
        .map(o => new SIREPO.DOM.UIEnumOption('', o))
    );

    return {
        restrict: 'A',
        scope: {
            modelName: '=',
            model: '=',
            field: '=',
            fieldClass: '=',
            parentController: '=',
            viewName: '=',
            object: '=',
        },
        template: `
          <div data-ng-class="fieldClass">
            ${sel.toTemplate()}
          </div>
        `,
        controller: function($scope, $element) {
            plotting.setupSelector($scope, $element);
        },
    };
});

SIREPO.app.directive('terminationTable', function(appState, panelState, radiaService, validationService) {
    return {
        restrict: 'A',
        scope: {
            field: '=',
            fieldName: '=',
            itemClass: '@',
            model: '=',
            modelName: '=',
            parentController: '=',
            object: '=',
        },

        template: `
            <table class="table radia-table-hover">
              <colgroup>
                <col style="width: 20ex">
                <col style="width: 20ex">
                <col style="width: 20ex">
              </colgroup>
              <thead>
                <tr>
                  <th>Object</th>
                  <th>Air Gap [mm]</th>
                  <th>Gap Offset [mm]</th>
                  <th></th>
                </tr>
              </thead>
             <tbody>
            <tr>
            </tr>
                <tr data-ng-repeat="item in field track by $index">
                    <td>{{ item.object.name }}</td>
                    <td>{{ item.airGap }}</td>
                    <td>{{ item.gapOffset }}</td>
                  <td style="text-align: right">
                    <div class="sr-button-bar-parent">
                        <div class="sr-button-bar" data-ng-class="sr-button-bar-active" >
                             <button data-ng-click="editItem(item)" class="btn btn-info btn-xs sr-hover-button">Edit</button>
                             <button data-ng-click="deleteItem(item, $index)" class="btn btn-danger btn-xs"><span class="glyphicon glyphicon-remove"></span></button>
                        </div>
                    <div>
                  </td>
                </tr>
            </tbody>
            </table>
            <button data-ng-click="addItem()" id="sr-new-termination" class="btn btn-info btn-xs pull-right">New Termination Object <span class="glyphicon glyphicon-plus"></span></button>
        `,
        controller: function($scope, $element) {
            let isEditing = false;

            const editorFields = [
                'geomObject.magnetization',
                'geomObject.material',
            ];

            const itemModel = 'termination';
            const groupModel = 'terminationGroup';
            let selectedItem =  null;
            let watchedModels = [itemModel];


            function itemIndex(data) {
                return $scope.field.indexOf(data);
            }

            $scope.addItem = () => {
                const item = appState.setModelDefaults({}, itemModel);
                item.object.id = radiaService.generateId();
                item.object.groupId = $scope.model[groupModel].id;
                $scope.editItem(item, true);
            };

            $scope.deleteItem = item => {
                radiaService.deleteObject(radiaService.getObject(item.object.id));
                const i = itemIndex(item);
                $scope.field.splice(i, 1);
                $scope.model[groupModel].members.splice(i, 1);
                appState.saveChanges([$scope.modelName, 'geometryReport']);
            };

            $scope.editItem = (item, isNew) => {
                isEditing = ! isNew;
                selectedItem = item;
                appState.models[itemModel] = item;
                appState.models.geomObject = item.object;
                panelState.showModalEditor(itemModel);
            };

            $scope.$on('modelChanged', (e, modelName) => {
                if (! watchedModels.includes(modelName)) {
                    return;
                }
                if (! isEditing) {
                    const item = appState.models[modelName];
                    $scope.field.push(item);
                    $scope.model[groupModel].members.push(item.object.id);
                    radiaService.getObject(item.object.groupId).members.push(item.object.id);
                    appState.models.geometryReport.objects.push(item.object);
                    isEditing = true;
                }
                for (const item of $scope.field) {
                    appState.models.geometryReport.objects[
                        appState.models.geometryReport.objects.indexOf(
                            radiaService.getObject(item.object.id)
                        )
                    ] = item.object;
                }
                selectedItem = null;
                appState.saveChanges('geometryReport');
            });

            $scope.$on('cancelChanges', (e, name) => {
                if (! watchedModels.includes(name)) {
                    return;
                }
                appState.removeModel(name);
            });

            appState.watchModelFields($scope, editorFields, () => {
                if (! selectedItem) {
                    return;
                }
                const o = selectedItem.object;
                radiaService.validateMagnetization(o.magnetization, o.material);
            }, true);

        },
    };
});

SIREPO.viewLogic('fieldPathsView', function(appState, $scope) {

    appState.watchModelFields(
        $scope,
        ['fieldPaths.paths'],
        updateAxisPaths,
        true
    );

    function updateAxisPath(path) {
        path.name = `${path.axis.toUpperCase()}-Axis`;
        const v = SIREPO.GEOMETRY.GeometryUtils.BASIS_VECTORS()[path.axis];
        path.begin = v.map(x => path.start * x);
        path.end = v.map(x => path.stop * x);
    }

    function updateAxisPaths() {
        for (const p of appState.models[$scope.modelName].paths.filter(x => x.type === 'axisPath')) {
            updateAxisPath(p);
         }
    }
});

SIREPO.viewLogic('geomObjectView', function(appState, panelState, radiaService, radiaVariableService, requestSender, $rootScope, $scope) {

    const builtinExtruded = ['cee', 'ell', 'jay'];
    const ctl = angular.element($('div[data-ng-controller]').eq(0)).controller('ngController');
    let editedModels = [];
    const materialFields = ['geomObject.magnetization', 'geomObject.material'];
    const parent = $scope.$parent;

    $scope.watchFields = [
        [
            'geomObject.type', 'geomObject.segmentation', 'geomObject.segmentationCylUseObjectCenter', 'geomObject.segmentationCylAxis',
            'cylinder.radius',
            'extrudedPoints.preservePointsOnImport',
            'extrudedPoly.extrusionAxisSegments', 'extrudedPoly.triangulationLevel',
            'extrudedObject.extrusionAxis',
            'stemmed.armHeight', 'stemmed.armPosition', 'stemmed.stemWidth', 'stemmed.stemPosition',
            'jay.hookHeight', 'jay.hookWidth',
            'stl.preserveVerticesOnImport',
        ], updateEditor
    ];

    $scope.whenSelected = () => {
        $scope.modelData = appState.models[$scope.modelName];
        editedModels = radiaService.updateModelAndSuperClasses($scope.modelData.type, $scope.modelData);
        updateEditor();
    };

    $scope.$on('modelChanged', (e, modelName) => {
        if (! editedModels.includes(modelName)) {
            return;
        }
        if (modelName === 'extrudedPoly') {
            if (editedModels.includes('extrudedPoints')) {
                loadPoints();
            }
            else {
                updateShapes();
            }
        }
        if (modelName === 'stl') {
            loadSTLSize();
        }
    });

    function buildTriangulationLevelDelegate() {
        const m = 'extrudedPoly';
        const f = 'triangulationLevel';
        let d = panelState.getFieldDelegate(m, f);
        d.range = () => {
            return {
                min: appState.fieldProperties(m, f).min,
                max: appState.fieldProperties(m, f).max,
                step: 0.01
            };
        };
        d.readout = () => {
            return appState.modelInfo(m)[f][SIREPO.INFO_INDEX_LABEL];
        };
        d.update = () => {};
        $scope.fieldDelegate = d;
    }

    function hasPoints() {
        return ($scope.modelData.referencePoints || []).length;
    }

    function loadPoints() {
        if (! $scope.modelData.pointsFile) {
            $scope.modelData.points = [];
            $scope.modelData.referencePoints = [];
            return;
        }
        radiaVariableService.updateRPNVars(() => {
            radiaService.buildShapePoints($scope.modelData, setPoints, res => {
                radiaService.deleteObject($scope.modelData);
                // The filename in the error is encumbered with model and field which is nonsense to the
                // average user, so replace it with the original file name
                throw new Error(res.error.replace(
                    new RegExp(/file \".*\"/, 'i'), `file "${$scope.modelData.pointsFile}"`
                ));
            });
        });
    }

    function loadSTLSize()  {
        requestSender.sendStatelessCompute(
            appState,
            setSTLSize,
            {
                method: 'stl_size',
                args: {
                    file: $scope.modelData.file,
                }
            },
            {
                onError: res => {
                    if (res.error.includes('does not exist')) {
                        throw new Error('STL file ' + $scope.modelData.file + ' does not exist');
                    }
                    throw new Error(res.error);
                }
            }
        );
    }

    function modelField(f) {
        const m = appState.parseModelField(f);
        return m ? m : [parent.modelName, f];
    }

    function updateShapes() {
        radiaService.updateExtruded($scope.modelData, () => {
            ctl.loadObjectViews();
            radiaService.saveGeometry(true);
        });
    }

    function setPoints(data) {
        $scope.modelData.referencePoints = data.points;
        updateShapes();
    }

    function setSTLSize(data) {
        if ($scope.modelData.isNew && $scope.modelData.preserveVerticesOnImport === "1") {
            $scope.modelData.center = data.center;
        }
        $scope.modelData.isNew = false;
        $scope.modelData.preserveVerticesOnImport = "0";
        $scope.modelData.size = data.size;
        appState.saveQuietly(editedModels);
    }

    function updateEditor() {
        const o = $scope.modelData;
        if (! o) {
            return;
        }

        const axes = SIREPO.GEOMETRY.GeometryUtils.BASIS();
        const modelType = o.type;
        parent.activePage.items.forEach((f) => {
            const m = modelField(f);
            const hasField = SIREPO.APP_SCHEMA.model[modelType][m[1]] !== undefined;
            panelState.showField(
                m[0],
                m[1],
                hasField || appState.isSubclass(modelType, m[0])
            );
        });

        panelState.showField('geomObject', 'materialFile', o.material === 'custom');
        panelState.showField('geomObject', 'materialFormula', o.material === 'nonlinear');
        panelState.enableField('geomObject', 'size', true);
        panelState.showField('geomObject', 'segments', editedModels.includes('cylinder') || ! editedModels.includes('extrudedObject'));

        const isSegCyl = o.segmentation === 'cyl';
        const segCylFields = [
            'segmentationCylAxis',
            'segmentationCylPoint',
            'segmentationCylRadius',
            'segmentationCylRatio',
            'segmentationCylUseObjectCenter',
        ];
        segCylFields.forEach(f => {
            panelState.showField('geomObject', f, isSegCyl);
        });
        panelState.showArrayField('geomObject', 'segments', 0, ! isSegCyl);
        [
            appState.models.geomObject.segmentationCylAxisMinor,
            appState.models.geomObject.segmentationCylAxisMajor,
        ] = SIREPO.GEOMETRY.GeometryUtils.nextAxes(appState.models.geomObject.segmentationCylAxis);


        if (o.segmentationCylUseObjectCenter === '1') {
            o.segmentationCylPoint = o.center.slice();
            panelState.enableField('geomObject', 'segmentationCylPoint', false);
        }
        else {
            panelState.enableField('geomObject', 'segmentationCylPoint', true);
        }

        if (modelType === 'stl') {
            panelState.enableField('geomObject', 'size', false);
            panelState.showField('stl', 'preserveVerticesOnImport', o.isNew);
            panelState.enableField('geomObject', 'center', o.preserveVerticesOnImport === '0');
            return;
        }

        if (! appState.isSubclass(modelType, 'extrudedObject') || builtinExtruded.includes(modelType)) {
            return;
        }

        for (const i in axes) {
            panelState.enableArrayField('geomObject', 'size', i, axes[i] === o.extrusionAxis);
        }

        if (modelType === 'cylinder') {
            radiaService.updateCylinder(o);
        }

        if (modelType !== 'extrudedPoints') {
            return;
        }

        panelState.showField('extrudedPoints', 'referencePoints', hasPoints());
        panelState.enableField('extrudedPoints', 'pointsFile', ! hasPoints());
        panelState.showField('extrudedPoints', 'preservePointsOnImport', o.isNew);
        panelState.enableField('geomObject', 'center', o.preservePointsOnImport === '0');
    }

    appState.watchModelFields($scope, materialFields, () => {
        updateEditor();
        radiaService.validateMagnetization($scope.modelData.magnetization, $scope.modelData.material);
    }, true);

    buildTriangulationLevelDelegate();
    const self = {};
    self.getBaseObject = () => $scope.modelData;
    return self;
});

SIREPO.viewLogic('objectShapeView', function(appState, panelState, radiaService, requestSender, utilities, $element, $scope) {
    let modelType = null;
    let editedModels = [];
    const parent = $scope.$parent;

    $scope.watchFields = [
        [
            'geomObject.type',
            "extrudedPoly.extrusionAxisSegments", "extrudedPoly.triangulationLevel",
            'stemmed.armHeight', 'stemmed.armPosition', 'stemmed.stemWidth', 'stemmed.stemPosition',
            'jay.hookHeight', 'jay.hookWidth',
        ], updateShapeEditor,
    ];

    $scope.whenSelected = () => {
        modelType = appState.models.geomObject.type;
        $scope.modelData = appState.models[$scope.modelName];
        editedModels = radiaService.updateModelAndSuperClasses(modelType, $scope.modelData);
        updateShapeEditor();
    };

    $scope.$on('extrudedPoly.changed', loadPoints);
    $scope.$on('stl.changed', loadSTLSize);

    function setPoints(data) {
        $scope.modelData.referencePoints = data.points;
        radiaService.updateExtruded($scope.modelData, () => {
            appState.saveChanges(editedModels);
            updateShapeEditor();
        });
    }

    function setSTLSize(data) {
        $scope.modelData.size = data.size;
        appState.saveQuietly(editedModels);
    }

    function loadSTLSize()  {
        requestSender.sendStatelessCompute(
            appState,
            setSTLSize,
            {
                method: 'stl_size',
                args: {
                    file: $scope.modelData.file,
                }
            },
            {
                onError: res => {
                    if (res.error.includes('does not exist')) {
                        throw new Error('STL file ' + $scope.modelData.file + ' does not exist');
                    }
                    throw new Error(res.error);
                }
            }
        );
    }

    function loadPoints() {
        if (! $scope.modelData.pointsFile) {
            $scope.modelData.points = [];
            $scope.modelData.referencePoints = [];
            return;
        }
        radiaService.buildShapePoints($scope.modelData, setPoints);
    }

    function buildTriangulationLevelDelegate() {
        const m = 'extrudedPoly';
        const f = 'triangulationLevel';
        let d = panelState.getFieldDelegate(m, f);
        d.range = () => {
            return {
                min: appState.fieldProperties(m, f).min,
                max: appState.fieldProperties(m, f).max,
                step: 0.01
            };
        };
        d.readout = () => {
            return appState.modelInfo(m)[f][SIREPO.INFO_INDEX_LABEL];
        };
        d.update = () => {};
        $scope.fieldDelegate = d;
    }

    function modelField(f) {
        const m = appState.parseModelField(f);
        return m ? m : [parent.modelName, f];
    }

    function updateShapeEditor() {
        parent.showPageNamed('Point Editor', $scope.modelData.pointsFile !== undefined);
        modelType = appState.models.geomObject.type;
        parent.activePage.items.forEach((f) => {
            const m = modelField(f);
            const hasField = SIREPO.APP_SCHEMA.model[modelType][m[1]] !== undefined;
            panelState.showField(
                m[0],
                m[1],
                hasField || appState.isSubclass(modelType, m[0])
            );
        });
        // show the type but disable it
        panelState.enableField('geomObject', 'type', false);
        panelState.showField('extrudedPoints', 'referencePoints', ($scope.modelData.referencePoints || []).length > 0);
    }

    buildTriangulationLevelDelegate();
});

SIREPO.viewLogic('optimizerView', function(activeSection, appState, panelState, radiaService, utilities, $scope) {

    $scope.watchFields = [
        [
            'optimizer.objective', 'optimizer.software',
            'objectiveFunctionQuality.fieldPath', 'objectiveFunctionQuality.useFieldPath',
        ],
        updateEditor,
    ];
    $scope.objectiveFunctionUpdaters = {};


    function updateEditor() {
        updateObjectiveFunction(appState.models[$scope.modelName].objective);
        updateSoftware();
        updateInputs();
    }

    function updateInputs() {
        panelState.showField('optimizer', 'parameters', appState.models[$scope.modelName].objective !== 'none');

    }

    function updateObjectiveFunction(fn) {
        const fns = appState.enumVals('ObjectiveFunction');
        if (! fn) {
            return;
        }
        for (const f of $scope.$parent.activePage.items) {
            const md = appState.parseModelField(f);
            if (! md || ! fns.includes(md[0])) {
                continue;
            }
            panelState.showField(md[0], md[1], md[0] === fn);
        }
        updateObjectiveFunctionQuality(appState.models[fn]);
    }

    function updateSoftware() {
        panelState.showField('optimizationSoftwareDFOLS', 'components', appState.models[$scope.modelName].software.type === 'optimizationSoftwareDFOLS');
    }

    function updateObjectiveFunctionQuality(fn) {

        const pathFields = ['begin', 'end'];
        const useFieldPath = fn.useFieldPath === '1' &&
            (appState.models.fieldPaths.paths || []).filter(radiaService.isLinearPath).length;
        pathFields.forEach(f => {
            panelState.enableField(fn.type, f, ! useFieldPath);
        });
        panelState.showField(fn.type, 'fieldPaths', useFieldPath);
        const currentPath = fn.fieldPath;
        if (! currentPath) {
            return;
        }
        if (useFieldPath) {
            pathFields.forEach(f => {
                fn[f] = currentPath[f];
            });
        }
    }

    $scope.whenSelected = () => {
        $scope.modelData = appState.models[$scope.modelName];
        updateEditor();
    };

    $scope.$on(`${$scope.modelName}.changed`, () => {});

});

SIREPO.viewLogic('racetrackView', function(appState, panelState, radiaService, requestSender, $rootScope, $scope) {

    const parent = $scope.$parent;

    $scope.watchFields = [
        [
            'racetrack.axis',
            'racetrack.height',
        ], updateObjectEditor
    ];

    $scope.whenSelected = () => {
        $scope.modelData = appState.models[$scope.modelName];
        updateObjectEditor();
    };

    function modelField(f) {
        const m = appState.parseModelField(f);
        return m ? m : [parent.modelName, f];
    }

    function updateObjectEditor() {
        const o = $scope.modelData;
        if (! o) {
            return;
        }

        [appState.models[$scope.modelName].planeAxis1, appState.models[$scope.modelName].planeAxis2]  = SIREPO.GEOMETRY.GeometryUtils.nextAxes($scope.modelData.axis);
        const modelType = o.type;
        parent.activePage.items.forEach((f) => {
            const m = modelField(f);
            const hasField = SIREPO.APP_SCHEMA.model[modelType][m[1]] !== undefined;
            panelState.showField(
                m[0],
                m[1],
                hasField || appState.isSubclass(modelType, m[0])
            );
        });
        radiaService.updateRaceTrack(o);
        panelState.enableField('racetrack', 'size', false);
    }

    // appState.watchModelFields does not work with arrays
    $scope.$watchGroup(
        [
            "appState['models']['racetrack']['sides'][0]",
            "appState['models']['racetrack']['sides'][1]",
            "appState['models']['racetrack']['radii'][1]",
        ],
        updateObjectEditor
    );

    const self = {};
    self.getBaseObject = () => $scope.modelData;
    return self;
});

for(const m of ['Dipole', 'Undulator']) {
    for (const d of SIREPO.APP_SCHEMA.enum[`${m}Type`]) {
        SIREPO.viewLogic(`${d[0]}View`, function(appState, panelState, radiaService, validationService, $scope) {

            $scope.model = appState.models[$scope.modelName];
            $scope.watchFields = [
                [
                    `${$scope.modelName}.coil.height`,
                ],
                updateEditor
            ];

            let editedModels = [];
            const materialFields = ['geomObject.magnetization', 'geomObject.material'];
            let models = {};
            for (const p of $scope.$parent.advancedFields) {
                const page = p[0];
                models[page] = {};
                // supports at most one sub-model per page
                for (const f of p[1]) {
                    let m = appState.parseModelField(f);
                    if (! m) {
                        continue;
                    }
                    m = appState.parseModelField(m[1]);
                    if (! m) {
                        continue;
                    }
                    models[page] = {
                        objModelName: m[0],
                        obj: appState.models[$scope.modelName][m[0]],
                    };
                    break;
                }
            }

            $scope.$on('cancelChanges', (e, d) => {
                // geometryReport is not part of the superclass chain and needs to be handled
                // separately
                if (d !== 'geometryReport') {
                    appState.cancelChanges('geometryReport');
                }
            });

            $scope.$on(`${$scope.modelName}.changed`, () => {
                radiaService.saveGeometry(true, false);
            });

            $scope.$on('geomObject.changed', () => {
                if (! activeModelId()) {
                    return;
                }
                if (appState.models.geomObject.id === activeModelId()) {
                    appState.models[$scope.modelName][activeObjModelName()] = appState.models.geomObject;
                    appState.saveChanges($scope.modelName);
                }
            });

            $scope.whenSelected = function() {
                const o = getObjFromGeomRpt();
                if (! o ) {
                    return;
                }
                // set the object in the model to the equivalent object in the report
                // also set the base model and its superclasses
                appState.models[$scope.modelName][activeObjModelName()] = o;
                editedModels = radiaService.updateModelAndSuperClasses(o.type, o);
                appState.saveChanges([$scope.modelName, ...editedModels]);

                if (o.type === 'racetrack') {
                    watchCoil();
                    panelState.enableField('racetrack', 'size', false);
                }
            };

            function activeModelId() {
                return (models[$scope.$parent.activePage.name].obj || {}).id;
            }

            function activeObjModelName() {
                return models[$scope.$parent.activePage.name].objModelName;
            }

            function getObjFromGeomRpt() {
                return radiaService.getObject(activeModelId());
            }

            function updateEditor() {
                const o = getObjFromGeomRpt();
                if (! o) {
                    return;
                }
                if (o.type === 'racetrack') {
                    radiaService.updateRaceTrack(o);
                }
            }

            function watchCoil() {
                const coil = `appState.models['${$scope.modelName}']['coil']`;
                $scope.$watchGroup(
                    [
                        `${coil}['sides'][0]`,
                        `${coil}['sides'][1]`,
                        `${coil}['radii'][1]`,
                    ],
                    updateEditor
                );
            }

            appState.watchModelFields($scope, materialFields, () => {
                const o = getObjFromGeomRpt();
                if (! o) {
                    return;
                }
                radiaService.validateMagnetization(o.magnetization, o.material);
            }, true);

        });
    }
}

SIREPO.viewLogic('rotateView', function(appState, panelState, radiaService, requestSender, $scope) {

    $scope.watchFields = [
        [
            'rotate.useObjectCenter',
        ], updateObjectEditor
    ];

    $scope.whenSelected = () => {
        $scope.modelData = appState.models[$scope.modelName];
        updateObjectEditor();
    };

    function updateObjectEditor() {
        if (! $scope.modelData) {
            return;
        }
        panelState.showField(
            'rotate',
            'center',
            $scope.modelData.useObjectCenter !== "1"
        );
    }
});

SIREPO.viewLogic('simulationView', function(activeSection, appState, panelState, radiaService, $scope) {

    let model = null;

    function isNew() {
        return activeSection.getActiveSection() === 'simulations';
    }

    function updateHeightAxis(isEnabled) {
        for (const e of SIREPO.APP_SCHEMA.enum.BeamAxis) {
            const axis = e[SIREPO.ENUM_INDEX_VALUE];
            const isShown = axis !== model.beamAxis;
            panelState.showEnum('simulation', 'heightAxis', axis, isShown);
            if (model.heightAxis === axis && ! isShown) {
                model.heightAxis = SIREPO.APP_SCHEMA.constants.heightAxisMap[model.beamAxis];
            }
        }
        panelState.enableField($scope.modelName, 'heightAxis', isEnabled);
    }

    function updateSimEditor() {
        if (! model) {
            return;
        }
        const isDipole = model.magnetType === 'dipole';
        const isImported =  ! ! appState.models.simulation.dmpImportFile;
        const enableAxes = isImported || (isNew() && ! isDipole);
        panelState.enableField(
            $scope.modelName,
            'magnetType',
            isNew()
        );
        panelState.showField($scope.modelName, 'enableKickMaps', enableAxes);

        for(const m of ['dipole', 'undulator']) {
            const t = `${m}Type`;
            panelState.showField($scope.modelName, t, model.magnetType === m);
            panelState.enableField($scope.modelName, t, isNew() && model.magnetType === m);
        }

        //TODO(mvk): setting the beamAxis/heightAxis to anything other than x/z for dipoles causes
        // the magnet to be built incorrectly. For now set those values and disable the fields
        if (isDipole) {
            model.beamAxis = 'x';
            model.heightAxis = 'z';
        }
        panelState.enableField(
            $scope.modelName,
            'beamAxis',
            enableAxes
        );
        updateHeightAxis(enableAxes);
    }

    $scope.watchFields = [
        ['simulation.beamAxis', 'simulation.magnetType'], updateSimEditor,
        ['simulation.heightAxis'], radiaService.setWidthAxis,
    ];


    $scope.$on(`${$scope.modelName}.editor.show`, () => {
        model = appState.models[$scope.modelName];
        updateSimEditor();
    });

});
