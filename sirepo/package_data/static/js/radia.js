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
    SIREPO.SINGLE_FRAME_ANIMATION = ['solverAnimation'];
    SIREPO.appFieldEditors += `
        <div data-ng-switch-when="BevelTable" class="col-sm-12">
          <div data-bevel-table="" data-field="model[field]" data-field-name="field" data-model="model" data-model-name="modelName"></div>
        </div>
        <div data-ng-switch-when="Color" data-ng-class="fieldClass">
          <input type="color" data-ng-model="model[field]" class="sr-color-button">
        </div>
        <div data-ng-switch-when="FieldPaths" class="col-sm-7">
          <select class="form-control" data-ng-model="model.fieldPath" data-ng-options="p as p.name for p in appState.models.fieldPaths.paths track by p.name"></select>
        </div>
        <div data-ng-switch-when="FilletTable" class="col-sm-12">
          <div data-fillet-table="" data-field="model[field]" data-field-name="field" data-model="model" data-model-name="modelName"></div>
        </div>
        <div data-ng-switch-when="FloatArray" class="col-sm-7">
            <div data-num-array="" data-model="model" data-field-name="field" data-field="model[field]" data-info="info" data-num-type="Float"></div>
        </div>
        <div data-ng-switch-when="Group" class="col-sm-12">
            <div data-group-editor="" data-field="model[field]" data-model="model"></div>
        </div>
        <div data-ng-switch-when="HMFile" data-ng-class="fieldClass">
            <div data-file-field="field" data-form="form" data-model="model" data-model-name="modelName"  data-selection-required="false" data-empty-selection-text="No File Selected" data-file-type="h-m"></div>
        </div>
        <div data-ng-switch-when="IntArray" class="col-sm-7">
            <div data-num-array="" data-model="model" data-field-name="field" data-field="model[field]" data-info="info" data-num-type="Int"></div>
        </div>
        <div data-ng-switch-when="ObjectType" class="col-sm-7">
            <div data-shape-selector="" data-model-name="modelName" data-model="model" data-field="model[field]" data-field-class="fieldClass" data-parent-controller="parentController" data-view-name="viewName" data-object="viewLogic.getBaseObject()"></div>
        </div>
        <div data-ng-switch-when="MaterialType" data-ng-class="fieldClass">
          <select number-to-string class="form-control" data-ng-model="model[field]" data-ng-options="item[0] as item[1] for item in enum[info[1]]"></select>
            <div class="sr-input-warning">
            </div>
        </div>
        <div data-ng-switch-when="PtsFile" data-ng-class="fieldClass">
          <input id="radia-pts-file-import" type="file" data-file-model="model[field]" accept=".dat,.txt,.csv"/>
        </div>
        <div data-ng-switch-when="Points" data-ng-class="fieldClass">
          <label class="control-label col-sm-5" style="text-align: center">{{ model.widthAxis }}</label> <label class="control-label col-sm-5"  style="text-align: center">{{ model.heightAxis }}</label>
          <div class="col-sm-12" style="height: 200px; overflow-y: scroll; overflow-x: hidden;">
              <div data-ng-repeat="p in model[field]">
                <input data-ng-repeat="e in p track by $index" class="form-control sr-number-list" data-string-to-number="float" data-ng-model="e" data-ng-disabled="model.pointsFile" style="text-align: right;" required />
              </div>
          </div>
        </div>
        <div data-ng-switch-when="ShapeButton" class="col-sm-7">
          <div data-shape-button="" data-model-name="modelName" data-field-class="fieldClass"></div>
        </div>
        <div data-ng-switch-when="TerminationTable" class="col-sm-12">
          <div data-termination-table="" data-field="model[field]" data-field-name="field" data-model="model" data-model-name="modelName"></div>
        </div>
        <div data-ng-switch-when="TransformTable" class="col-sm-12">
          <div data-transform-table="" data-field="model[field]" data-field-name="field" data-model="model" data-model-name="modelName" data-item-class="Transform" data-parent-controller="parentController"></div>
        </div>
    `;
});

SIREPO.app.factory('radiaService', function(appState, fileUpload, geometry, panelState, requestSender, utilities, validationService) {
    let self = {};

    const POST_SIM_REPORTS = ['electronTrajectoryReport', 'fieldIntegralReport', 'fieldLineoutAnimation', 'kickMapReport',];

    // why is this here? - answer: for getting frames
    self.computeModel = function(analysisModel) {
        return 'fieldLineoutAnimation';
    };

    appState.setAppService(self);

    self.axes = ['x', 'y', 'z'];
    self.isEditing = false;
    self.objBounds = null;
    self.pointFieldTypes = appState.enumVals('FieldType').slice(1);
    self.pointFieldExports = {
        csv: {
            contentType: 'text/csv;charset=utf-8',
            extension: 'csv',
            responseType: '',
        },
        sdds: {
            contentType: 'application/octet-stream',
            extension: 'sdds',
            responseType: '',
        },
        SRW: {
            contentType: 'application/zip',
            extension: 'zip',
            responseType: 'arraybuffer',
        }
    };
    self.pointFieldExportTypes = Object.keys(self.pointFieldExports);

    self.selectedObject = null;

    self.addOrModifyPath = function(type) {
        const p = appState.models[self.pathTypeModel(type)];
        if (! appState.models.fieldPaths.paths) {
            appState.models.fieldPaths.paths = [];
        }
        if (! findPath(p)) {
            if (type === 'file') {
                p.fileName = p.fileModel.name;
                upload((p.fileModel));
            }
            appState.models.fieldPaths.paths.push(p);
        }
        appState.saveChanges('fieldPaths', function (d) {
            self.showPathPicker(false);
        });
    };

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

    self.buildShapePoints = (o, callback) => {
        requestSender.sendStatelessCompute(
            appState,
            callback,
            {
                method: 'build_shape_points',
                args: {
                    object: o,
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
        o.points = o.referencePoints.map(
            p => p.map(
                (x, i) => p[i] + o.center[idx[i]] - (
                    SIREPO.UTILS.minForIndex(o.referencePoints, i) + o.size[idx[i]] / 2.0
                )
            )
        );
    };

    self.createPathModel = function(type) {
        const t = type || self.pathTypeModel(appState.models.fieldPaths.path);
        const model = {};
        appState.models[t] = appState.setModelDefaults(model, t);

        // set to fill bounds if any actors exist
        //TODO: must use OBJECT bounds, not the bounds of a vector field!
        if (t === 'fieldMapPath' && self.objBounds) {
            appState.models[t].lenX = Math.abs(self.objBounds[1] - self.objBounds[0]);
            appState.models[t].lenY = Math.abs(self.objBounds[3] - self.objBounds[2]);
            appState.models[t].lenZ = Math.abs(self.objBounds[5] - self.objBounds[4]);
            appState.models[t].ctrX = (self.objBounds[1] + self.objBounds[0]) / 2.0;
            appState.models[t].ctrY = (self.objBounds[3] + self.objBounds[2]) / 2.0;
            appState.models[t].ctrZ = (self.objBounds[5] + self.objBounds[4]) / 2.0;
        }
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
        self.saveGeometry(true, false);
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

    self.getObject = function(id) {
        let objs = appState.models.geometryReport.objects || [];
        for (const o of objs) {
            if (o.id == id) {
                return o;
            }
        }
        return null;
    };

    self.getObjects = function() {
        return appState.models.geometryReport.objects || [];
    };

    self.getPathType = function() {
        return (appState.models.fieldTypes || {}).path;
    };

    self.getSelectedObject = function() {
        return self.selectedObject;
    };

    self.newPath = function() {
        self.showPathPicker(true, true);
    };


    // In order to associate VTK objects in the viewer with Radia objects, we need a mapping between them.
    // When we create objects on the client side we don't yet know the Radia id so we cannot use it directly.
    // Instead, generate an id here and map it when the Radia object is created. A random string is good enough
    self.generateId = () => utilities.randomString(16);

    self.pathEditorTitle = function() {
        if (! appState.models.fieldPaths) {
            return '';
        }
        return (self.isEditing ? 'Edit ' : 'New ') + appState.models.fieldPaths.path;
    };

    self.pathTypeModel = function(type) {
        return type + 'Path';
    };

    self.reloadGeometry = (callback=() => {}) => {
        const r = 'geometryReport';
        panelState.clear(r);
        panelState.requestData(r, callback, true);
    };

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

    self.showFieldDownload = function(doShow, path) {
        self.selectedPath = path;
        $('#sr-field-download').modal(doShow ? 'show' : 'hide');
    };

    self.showPathPicker = function(doShow, isNew) {
        self.isEditing = doShow && ! isNew;
        if (doShow) {
            if (isNew) {
                self.createPathModel();
            }
        }
        $('#' + panelState.modalId('fieldpaths')).modal(doShow ? 'show' : 'hide');
    };

    self.scaledArray = function (arr, scale = 1.0) {
        return arr.map(x => scale * x);
    };

    self.syncReports = () => {
        POST_SIM_REPORTS.forEach(r => {
            appState.models[r].lastModified = appState.models.geometryReport.lastModified;
        });
        appState.saveChanges(POST_SIM_REPORTS);
    };

    self.updateExtruded = (o, callback) => {
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
            o.size[self.axisIndex(dim)] = Math.abs(Math.max(...p) - Math.min(...p));
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

    self.upload = function(inputFile) {
        upload(inputFile);
    };

    self.validateMagnetization = (magnetization, material) => {
        const mag = Math.hypot(magnetization || SIREPO.ZERO_ARR);
        validationService.validateField(
            'geomObject',
            'material',
            'select',
            SIREPO.APP_SCHEMA.constants.anisotropicMaterials.indexOf(material) < 0 || mag > 0,
            'Anisotropic materials require non-zero magnetization'
        );
    };

    function findPath(path) {
        for (const p of (appState.models.fieldPaths.paths || [])) {
            if (p.type === path.type && p.id === path.id) {
                return path;
            }
        }
        return null;
    }

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

    function upload(inputFile, type=SIREPO.APP_SCHEMA.constants.pathPtsFileType) {
        fileUpload.uploadFileToUrl(
            inputFile,
            {},
            requestSender.formatUrl(
                'uploadFile',
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

SIREPO.app.controller('RadiaSourceController', function (appState, geometry, panelState, plotting, radiaService, utilities, validationService, vtkPlotting, $scope) {
    //TODO(mvk): a lot of this is specific to freehand magnets and should be moved to a directive

    let self = this;

    const editorFields = [
        'geomObject.magnetization',
        'geomObject.material',
        'geomObject.symmetryType',
        'simulation.beamAxis',
        'simulation.heightAxis',
    ];
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


    self.copyObject = o => {
        const copy = appState.clone(o);
        copy.name = newObjectName(copy);
        copy.id = radiaService.generateId();
        copy.groupId = '';
        addObject(copy);
        self.editObject(copy);
    };

    self.editTool = tool => {
        if (tool.isInactive) {
            return;
        }
        panelState.showModalEditor(tool.model);
    };

    self.deleteObject = o => {
        deleteShapesForObject(o);
        radiaService.deleteObject(o);
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

    self.showDesigner = () => {
        return appState.models.simulation.magnetType === 'freehand';
    };

    self.showParams = () => {
        return appState.models.simulation.magnetType !== 'freehand';
    };

    self.getDipoleType = () => {
        if (self.getMagnetType() !== 'dipole') {
            return null;
        }
        return appState.models.simulation.dipoleType;
    };

    self.getMagnetType = () => {
        return appState.models.simulation.magnetType;
    };

    self.getObject = id => {
        return radiaService.getObject(id);
    };

    self.getObjects = () => {
        return radiaService.getObjects();
    };

    self.getShape = id => {
        return self.shapes.filter( s => s.id === id)[0];
    };

    self.getShapes = () => self.shapes;

    self.getUndulatorType = () => {
        if (self.getMagnetType() !== 'undulator') {
            return null;
        }
        return appState.models.simulation.undulatorType;
    };

    self.getView = () => `${appState.models.simulation[`${self.getMagnetType()}Type`]}`;

    self.isDropEnabled = () => self.dropEnabled;

    self.objectBounds = () => groupBounds();

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

        function save() {
            appState.saveChanges('geomObject', d => {
                transformShapesForObjects();
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
        if (o.layoutShape === 'polygon') {
            radiaService.updateExtruded(o, save);
        }
        else {
            save();
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

    self.shapeBounds = () => shapesBounds(self.shapes);

    // seems like a lot of this shape stuff can be refactored out to a common area
    self.shapeForObject = o => {
        const scale = SIREPO.APP_SCHEMA.constants.objectScale;
        let center = radiaService.scaledArray(o.center || SIREPO.ZERO_ARR, scale);
        let size =   radiaService.scaledArray(o.size || SIREPO.ZERO_ARR, scale);
        const isGroup = o.members && o.members.length;

        if (isGroup) {
            const b = groupBounds(o.members.map(id => self.getObject(id)));
            center = b.map(c => (c[0] + c[1]) / 2);
            size = b.map(c => Math.abs(c[1] - c[0]));
        }

        // initial dragged polygons have no points defined
        if (! o.points) {
            o.layoutShape = 'rect';
        }
        let pts = {};
        if (o.layoutShape === 'polygon') {
            const [k, i, j] = [o.extrusionAxis, o.widthAxis, o.heightAxis].map(radiaService.axisIndex);
            const scaledPts = o.points.map(p => radiaService.scaledArray(p, scale));
            pts[o.extrusionAxis] = scaledPts;
            const cp = center[k] + size[k] / 2.0;
            const cm = center[k] - size[k] / 2.0;
            let p = scaledPts.map(x => x[1]);
            let [mx, mn] = [Math.max(...p), Math.min(...p)];
            pts[o.widthAxis] = [[mx, cm], [mx, cp], [mn, cp], [mn, cm]];
            p = scaledPts.map(x => x[0]);
            [mx, mn] = [Math.max(...p), Math.min(...p)];
            pts[o.heightAxis] = [[cm, mx], [cp, mx], [cp, mn], [cm, mn]];
        }
        const shape = vtkPlotting.plotShape(
            o.id, o.name,
            center, size,
            o.color, 0.3, isGroup ? null : 'solid', isGroup ? 'dashed' : 'solid', null,
            o.layoutShape,
            pts
        );
        if (isGroup) {
            shape.outlineOffset = 5.0;
            shape.strokeWidth = 0.75;
            shape.draggable = false;
        }
        return shape;
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
        addShapesForObject(o);
    }

    function addShapesForObject(o) {
        let baseShape = self.getShape(o.id);
        if (! baseShape) {
            baseShape = self.shapeForObject(o);
            self.shapes.push(baseShape);
        }

        let txArr = [];
        let plIds = [];
        // probably better to create a transform and let svg do this work
        o.transforms.forEach(function (xform) {
            // draw the shapes for symmetry planes once
            if (xform.model === 'symmetryTransform') {
                plIds.push(...addSymmetryPlane(baseShape, xform));
            }
            // each successive transform must be applied to all previous shapes
            [baseShape, ...getVirtualShapes(baseShape, plIds)].forEach(function (xShape) {
                // these transforms do not copy the object
                if (xform.model === 'rotate') {
                    txArr.push(rotateFn(xform, 1));
                    return;
                }
                if (xform.model === 'translate') {
                    txArr.push(offsetFn(xform, 1));
                    return;
                }

                let xo = self.getObject(xShape.id);
                let linkTx;
                if (xform.model === 'cloneTransform') {
                    let clones = [];
                    for (let i = 1; i <= xform.numCopies; ++i) {
                        let cloneTx = txArr.slice(0);
                        linkTx = composeFn(cloneTx);
                        for (let j = 0; j < xform.transforms.length; ++j) {
                            let cloneXform = xform.transforms[j];
                            if (cloneXform.model === 'translateClone') {
                                cloneTx.push(offsetFn(cloneXform, i));
                            }
                            if (cloneXform.model === 'rotateClone') {
                                cloneTx.push(rotateFn(cloneXform, i));
                            }
                        }
                        addTxShape(xShape, xform, linkTx);
                        clones.push(...transformMembers(xo, xform, linkTx, clones));
                    }
                }
                if (xform.model === 'symmetryTransform') {
                    linkTx = mirrorFn(xform);
                    addTxShape(xShape, xform, linkTx);
                    transformMembers(xo, xform, linkTx);
                }
            });
        });

        // apply non-copying transforms to the object and its members (if any)
        composeFn(txArr)(baseShape, baseShape);
        for (const m of getMembers(o)) {
            let s = self.getShape(m.id);
            composeFn(txArr)(s, s);
        }

        if (o.groupId !== '') {
            let gShape = self.getShape(o.groupId);
            if (! gShape) {
                gShape = self.shapeForObject(self.getObject(o.groupId));
                self.shapes.push(gShape);
            }
            fit(baseShape, gShape);
            baseShape.addLink(gShape, fit);
        }
    }

    function addSymmetryPlane(baseShape, xform) {
        let plIds = [];
        for (const p in vtkPlotting.COORDINATE_PLANES) {
            const cpl = geometry.plane(vtkPlotting.COORDINATE_PLANES[p], geometry.point());
            const spl = geometry.plane(
                xform.symmetryPlane,
                geometry.pointFromArr(radiaService.scaledArray(
                    xform.symmetryPoint,
                    SIREPO.APP_SCHEMA.constants.objectScale)
                ));
            if (cpl.equals(spl) || ! spl.intersection(cpl)) {
                continue;
            }
            const pl = vtkPlotting.plotLine(
                virtualShapeId(baseShape), baseShape.name, spl.intersection(cpl),
                baseShape.color, 1.0, 'dashed', "8,8,4,8"
            );
            pl.coordPlane = p;
            self.shapes.push(pl);
            plIds.push(pl.id);
        }
        return plIds;
    }

    function addTxShape(sourceShape, xform, link) {
        let nextShape = txShape(sourceShape, xform);
        sourceShape.addLink(nextShape, link);
        self.shapes.push(nextShape);
        link(sourceShape, nextShape);
        return nextShape;
    }

    function baseShapeId(id) {
        return `${id}`.split('-')[0];
    }

    function composeFn(fnArr) {
        return function(shape1, shape2) {
            let prevShape = shape1;
            fnArr.forEach(function (tx) {
                prevShape = tx(prevShape, shape2);
            });
            return shape2;
        };
    }

    function deleteShapesForObject(o) {
        for (const s of getTransformedShapes(o)) {
            self.shapes.splice(indexOfShape(s), 1);
        }
        let shape = self.shapeForObject(o);
        for (const s of getVirtualShapes(shape)) {
            self.shapes.splice(indexOfShape(s), 1);
        }
        self.shapes.splice(indexOfShape(shape), 1);
    }

    // shape - in group; linkedShape: group
    function fit(shape, groupShape) {
        const o = self.getObject(shape.id);
        const groupId = o.groupId;
        if (groupId === '' || groupId !== groupShape.id) {
            groupShape.center = shape.center;
            groupShape.size = shape.size;
            return groupShape;
        }
        let mShapes = self.getObject(groupShape.id).members.map(function (mId) {
            return self.getShape(mId);
        }).filter(function (s) {
            return ! ! s;
        });
        const newBounds = shapesBounds(mShapes);
        for (const dim in newBounds) {
            groupShape.size[dim] = Math.abs(newBounds[dim][1] - newBounds[dim][0]);
            groupShape.center[dim] = newBounds[dim][0] + groupShape.size[dim] / 2;
        }
        return groupShape;
    }

    // recursive dive through all subgroups
    function getMembers(o) {
        if (! o) {
            return [];
        }
        let members = (o.members || []).map(function (id) {
            return self.getObject(id);
        });
        for (const m of members) {
            members.push(...getMembers(m));
        }
        return members;
    }

    function getTransformedShapes(o) {
        let xfIds = o.transforms.map(function (tx) {
            return tx.id;
        });
        if (! xfIds.length) {
            return [];
        }
        return self.shapes.filter(function (s) {
            return xfIds.indexOf(s.txId) >= 0;
        });
    }

    // may have to flatten
    function getVirtualShapes(baseShape, excludedIds = []) {
        let v = self.shapes.filter(function (s) {
            return excludedIds.indexOf(s.id) < 0 && hasBaseShape(s, baseShape);
        });
        let v2 = [];
        for (const s of v) {
            v2.push(...getVirtualShapes(s, excludedIds));
        }
        v.push(...v2);
        return v;
    }

    function groupBounds(objs) {
        const b = [
            [Number.MAX_VALUE, -Number.MAX_VALUE],
            [Number.MAX_VALUE, -Number.MAX_VALUE],
            [Number.MAX_VALUE, -Number.MAX_VALUE]
        ];
        const scale = SIREPO.APP_SCHEMA.constants.objectScale;
        b.forEach(function (c, i) {
            (objs || appState.models.geometryReport.objects || []).forEach(function (o) {
                const ctr =  radiaService.scaledArray(o.center || SIREPO.ZERO_ARR, scale);
                const sz =  radiaService.scaledArray(o.size || SIREPO.ZERO_ARR, scale);
                c[0] = Math.min(c[0], ctr[i] - sz[i] / 2);
                c[1] = Math.max(c[1], ctr[i] + sz[i] / 2);
            });
        });
        return b;
    }

    // indexOf does not work right...explicitly match by id here
    function indexOfShape(shape) {
        for (let i = 0; i < self.shapes.length; ++i) {
            if (self.shapes[i].id === shape.id) {
                return i;
            }
        }
        return -1;
    }

    function loadShapes() {
        self.shapes = [];
        appState.models.geometryReport.objects.forEach(addShapesForObject);
        addBeamAxis();
    }

    function mirrorFn(xform) {
        return function (shape1, shape2) {
            const pl = geometry.plane(
                xform.symmetryPlane,
                geometry.pointFromArr(
                    radiaService.scaledArray(xform.symmetryPoint, SIREPO.APP_SCHEMA.constants.objectScale)
                )
            );
            shape2.setCenter(
                pl.mirrorPoint(geometry.pointFromArr(
                [shape1.center.x, shape1.center.y, shape1.center.z]
                )).coords()
            );
            shape2.setSize(shape1.getSizeCoords());
            return shape2;
        };
    }

    function newObjectName(o) {
        return appState.uniqueName(appState.models.geometryReport.objects, 'name', o.name + ' {}');
    }

    function offsetFn(xform, i) {
        return function(shape1, shape2) {
            const d = radiaService.scaledArray(xform.distance, SIREPO.APP_SCHEMA.constants.objectScale);
            shape2.setCenter(
                shape1.getCenterCoords().map(function (c, j) {
                    return c + i * d[j];
                })
            );
            return shape2;
        };
    }

    function rotateFn(xform, i) {
        return (shape1, shape2) => {
            const scale = SIREPO.APP_SCHEMA.constants.objectScale;
            shape2.rotationMatrix = new SIREPO.GEOMETRY.RotationMatrix(
                radiaService.scaledArray(xform.axis, scale),
                radiaService.scaledArray(xform.center, scale),
                i * Math.PI * parseFloat(xform.angle) / 180.0
            );
            shape2.rotateAroundShapeCenter = xform.useObjectCenter === "1";
            return shape2;
        };
    }

    function shapesBounds(shapes) {
        let b = {
            x: [Number.MAX_VALUE, -Number.MAX_VALUE],
            y: [Number.MAX_VALUE, -Number.MAX_VALUE],
            z: [Number.MAX_VALUE, -Number.MAX_VALUE]
        };
        shapes.forEach(s => {
            let vs = getVirtualShapes(s);
            let sr = shapesBounds(vs);
            for (const dim in b) {
                if (s.center[dim] === undefined) {
                    continue;
                }
                b[dim] = [
                    Math.min(b[dim][0], s.center[dim] - s.size[dim] / 2, sr[dim][0]),
                    Math.max(b[dim][1], s.center[dim] + s.size[dim] / 2, sr[dim][1])
                ];
            }
        });
        for (const dim in b) {
            if (b[dim].some(x => Math.abs(x) === Number.MAX_VALUE)) {
                return b;
            }
        }
        // use an enclosing sphere to take rotations into account
        const r = Math.hypot(
            (b.x[1] - b.x[0]) / 2,
            (b.y[1] - b.y[0]) / 2,
            (b.z[1] - b.z[0]) / 2,
        );
        for (const dim in b) {
            const c = b[dim][0] + (b[dim][1] - b[dim][0]) / 2;
            b[dim][0] = c - r;
            b[dim][1] = c + r;
        }
        return b;
    }

    function transformMembers(o, xform, txFunction, excludedIds=[]) {
        if (! o) {
            return;
        }
        let txm = [];
        for (const m of getMembers(o)) {
            let shape = self.getShape(m.id);
            if (! shape) {
                // may be later in array if created externally
                addShapesForObject(self.getObject(m.id));
                shape = self.getShape(m.id);
            }
            let v = getVirtualShapes(shape, excludedIds);
            txm.push(addTxShape(shape, xform, txFunction).id);
            for (const s of v) {
                txm.push(addTxShape(s, xform, txFunction).id);
            }
        }
        return txm;
    }

    function transformShapesForObject(o) {
        let baseShape = self.getShape(o.id);
        [baseShape, ...getVirtualShapes(baseShape)].forEach(function (s) {
            s.runLinks();
        });
    }

    function transformShapesForObjects() {
        for (const o of self.getObjects()) {
            transformShapesForObject(o);
        }
    }

    function txShape(shape, tx) {
        const sh = vtkPlotting.plotShape(
            virtualShapeId(shape),
            shape.name,
            SIREPO.ZERO_ARR,
            shape.getSizeCoords(),
            shape.color, 0.1, shape.fillStyle, shape.strokeStyle, shape.dashes,
            shape.layoutShape
        );
        sh.draggable = false;
        sh.txId = tx.id;
        return sh;
    }

    function virtualShapeId(shape) {
        return `${shape.id}-${Math.floor(Math.random() * Number.MAX_SAFE_INTEGER)}`;
    }

    function hasBaseShape(shape, baseShape) {
        // base shape is not its own base
        if (shape.id === baseShape.id) {
            return false;
        }
        return baseShapeId(shape.id) === `${baseShape.id}`;
    }

    // initial setup
    if (! appState.models.geometryReport.objects) {
        appState.models.geometryReport.objects = [];
    }
    loadShapes();

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
                // calculate the size
                let s = [0, 0, 0];
                const i = geometry.basis.indexOf(o.axis);
                s[i] = o.height;
                for (const j of [0, 1]) {
                    s[(i + j + 1) % 3] = o.sides[j] + 2.0 * o.radii[1];
                }
                o.size = s;
                appState.saveQuietly('racetrack');
            }
            if (o.materialFile) {
                o.hmFileName = o.materialFile.name;
                radiaService.upload(o.materialFile, SIREPO.APP_SCHEMA.constants.hmFileType);
            }
        }
        radiaService.saveGeometry(true, false, () => {
            if (self.selectedObject) {
                loadShapes();
            }
        });
    });

    $scope.$on('layout.object.dropped', function (e, lo) {
        const m = appState.setModelDefaults({}, lo.type);
        m.center = lo.center;
        m.name = lo.type;
        m.name = newObjectName(m);
        self.editObject(m);
    });

    $scope.$on('drop.target.enabled', function (e, val) {
        self.dropEnabled = val;
    });
});

SIREPO.app.controller('RadiaVisualizationController', function (appState, panelState, persistentSimulation, radiaService, $scope) {

    let solving = false;

    let self = this;
    self.simScope = $scope;
    $scope.mpiCores = 0;
    $scope.panelState = panelState;
    $scope.svc = radiaService;

    self.solution = null;

    self.enableKickMaps = function() {
        return appState.isLoaded() && appState.models.simulation.enableKickMaps === '1';
    };

    self.isSolvable = function() {
        return appState.isLoaded() && appState.models.geometryReport.isSolvable == '1';
    };

    self.resetSimulation = function() {
        self.solution = null;
        solving = false;
        panelState.clear('geometryReport');
        panelState.requestData('reset', () => {}, true);
        radiaService.syncReports();
    };

    self.simHandleStatus = function(data) {
        if (data.error) {
            solving = false;
        }
        if ('percentComplete' in data && ! data.error) {
            if (data.percentComplete === 100 && ! self.simState.isProcessing()) {
                self.solution = data.solution;
                if (solving) {
                    radiaService.syncReports();
                }
                solving = false;
                radiaService.saveGeometry(false, true);
            }
        }
    };

    self.startSimulation = function(model) {
        self.solution = null;
        solving = true;
        self.simState.saveAndRunSimulation([model, 'simulation']);
    };

    self.simComputeModel = 'solverAnimation';
    self.simState = persistentSimulation.initSimulationState(self);

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
                  <li data-ng-if="! isImported()" class="sim-section" data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-magnet"></span> Design</a></li>
                  <li class="sim-section" data-ng-class="{active: nav.isActive(\'visualization\')}"><a href data-ng-click="nav.openSection(\'visualization\')"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>
                </div>
              </app-header-right-sim-loaded>
              <app-settings>
                    <li><a href data-ng-click="exportDmp()"><span class="glyphicon glyphicon-cloud-download"></span> Export Radia Dump</a></li>
              </app-settings>
              <app-header-right-sim-list>
                <ul class="nav navbar-nav sr-navbar-right">
                  <li><a href data-ng-click="showImportModal()"><span class="glyphicon glyphicon-cloud-upload"></span> Import</a></li>
                </ul>
              </app-header-right-sim-list>
            </div>
        `,
        controller: function($scope) {
            $scope.exportDmp = function() {
                requestSender.newWindow('exportArchive', {
                    '<simulation_id>': appState.models.simulation.simulationId,
                    '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                    '<filename>':  $scope.nav.simulationName() + '.dat',
                });
            };
            $scope.showImportModal = function() {
                $('#simulation-import').modal('show');
            };
            $scope.isImported = function() {
                let sim = appState.models.simulation || {};
                return isRawExample(sim.exampleName) || sim.dmpImportFile;
            };

            // "raw" examples are from radia_examples.py - a temporary repository
            function isRawExample(name) {
                return SIREPO.APP_SCHEMA.constants.rawExamples.indexOf(name) >= 0;
            }
        }
    };
});

SIREPO.app.directive('bevelTable', function(appState, panelState, radiaService) {
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
                <col span="5" style="width: 20ex">
              </colgroup>
              <thead>
                <tr>
                  <th>Cut Axis</th>
                  <th>Cut Edge</th>
                  <th>Vertical Distance From Corner</th>
                  <th>Horizontal Distance From Corner</th>
                  <th>Cut Removal Side</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr data-ng-repeat="item in loadItems()">
                  <td>{{ item.cutAxis }}</td>
                  <td>{{ bevelEdge(item.edge) }}</td>
                  <td>{{ item.amountVert }}mm</td>
                  <td>{{ item.amountHoriz }}mm</td>
                  <td>{{ item.cutRemoval }}</td>
                  <td style="text-align: right">
                    <div class="sr-button-bar-parent">
                      <div class="sr-button-bar" data-ng-class="sr-button-bar-active">
                        <button data-ng-click="editItem(item)" class="btn btn-info btn-xs sr-hover-button">Edit</button>
                        <button data-ng-click="deleteItem(item, $index)" class="btn btn-danger btn-xs"><span class="glyphicon glyphicon-remove"></span></button>
                      </div>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
            <button data-ng-click="addItem()" id="sr-new-bevel" class="btn btn-info btn-xs pull-right">New Bevel <span class="glyphicon glyphicon-plus"></span></button>
        `,
        controller: function($scope, $element) {
            let isEditing = false;
            let itemModel = 'objectBevel';
            let watchedModels = [itemModel];

            $scope.items = [];
            $scope.radiaService = radiaService;
            $scope.selectedItem = null;

            function itemIndex(data) {
                return $scope.items.indexOf(data);
            }

            $scope.addItem = () => {
                let b = appState.setModelDefaults({}, itemModel);
                $scope.editItem(b, true);
            };

            $scope.bevelEdge = index => {
                for (const e of SIREPO.APP_SCHEMA.enum.BevelEdge) {
                    if (e[SIREPO.ENUM_INDEX_VALUE] === index) {
                        return e[SIREPO.ENUM_INDEX_LABEL];
                    }
                }
                return '';
            };

            $scope.deleteItem = item => {
                const index = itemIndex(item);
                if (index < 0) {
                    return;
                }
                $scope.field.splice(index, 1);
                radiaService.saveGeometry(true);
            };

            $scope.editItem = (item, isNew) => {
                isEditing = ! isNew;
                $scope.selectedItem = item;
                appState.models[itemModel] = item;
                panelState.showModalEditor(itemModel);
            };

            $scope.getSelected = () => $scope.selectedItem;

            $scope.loadItems = () => {
                $scope.items = $scope.field;
                return $scope.items;
            };

            appState.whenModelsLoaded($scope, () => {

                $scope.$on('modelChanged', (e, modelName) => {
                    if (! watchedModels.includes(modelName)) {
                        return;
                    }
                    $scope.selectedItem = null;
                    let m = appState.models[modelName];
                    const d = m.cutAxis;
                    const h = SIREPO.APP_SCHEMA.constants.heightAxisMap[d];
                    const w = radiaService.calcWidthAxis(d, h);
                    const dirs = radiaService.getGeomDirections(d, h, w);
                    m.cutDir = dirs.depth;
                    m.heightDir = dirs.height;
                    m.widthDir = dirs.width;
                    appState.saveQuietly(modelName);
                    if (! isEditing) {
                        $scope.field.push(m);
                        isEditing = true;
                    }
                    radiaService.saveGeometry(true, false,() => {
                        $scope.loadItems();
                    });
                });

                $scope.$on('cancelChanges', (e, name) => {
                    if (! watchedModels.includes(name)) {
                        return;
                    }
                    appState.removeModel(name);
                });

                $scope.loadItems();
            });

        },
    };
});

SIREPO.app.directive('filletTable', function(appState, panelState, radiaService) {
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
                <col span="4" style="width: 20ex">
              </colgroup>
              <thead>
                <tr>
                  <th>Axis</th>
                  <th>Edge</th>
                  <th>Radius</th>
                  <th>Resolution</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr data-ng-repeat="item in loadItems()">
                  <td>{{ item.cutAxis }}</td>
                  <td>{{ bevelEdge(item.edge) }}</td>
                  <td>{{ item.radius }}mm</td>
                  <td>{{ item.numSides }}</td>
                  <td style="text-align: right">
                    <div class="sr-button-bar-parent">
                      <div class="sr-button-bar" data-ng-class="sr-button-bar-active" >
                        <button data-ng-click="editItem(item)" class="btn btn-info btn-xs sr-hover-button">Edit</button>
                        <button data-ng-click="deleteItem(item, $index)" class="btn btn-danger btn-xs"><span class="glyphicon glyphicon-remove"></span></button>
                      </div>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
            <button data-ng-click="addItem()" id="sr-new-fillet" class="btn btn-info btn-xs pull-right">New Fillet <span class="glyphicon glyphicon-plus"></span></button>
        `,
        controller: function($scope, $element) {
            let isEditing = false;
            let itemModel = 'objectFillet';
            let watchedModels = [itemModel];

            $scope.items = [];
            $scope.radiaService = radiaService;
            $scope.selectedItem = null;

            function itemIndex(data) {
                return $scope.items.indexOf(data);
            }

            $scope.addItem = function() {
                let b = appState.setModelDefaults({}, itemModel);
                $scope.editItem(b, true);
            };

            $scope.bevelEdge = (index) => {
                for (const e of SIREPO.APP_SCHEMA.enum.BevelEdge) {
                    if (e[SIREPO.ENUM_INDEX_VALUE] === index) {
                        return e[SIREPO.ENUM_INDEX_LABEL];
                    }
                }
                return '';
            };

            $scope.deleteItem = function(item) {
                const index = itemIndex(item);
                if (index < 0) {
                    return;
                }
                $scope.field.splice(index, 1);
                radiaService.saveGeometry(true);
            };

            $scope.editItem = function(item, isNew) {
                isEditing = ! isNew;
                $scope.selectedItem = item;
                appState.models[itemModel] = item;
                panelState.showModalEditor(itemModel);
            };

            $scope.getSelected = function() {
                return $scope.selectedItem;
            };

            $scope.loadItems = function() {
                $scope.items = $scope.field;
                return $scope.items;
            };

            appState.whenModelsLoaded($scope, function() {

                $scope.$on('modelChanged', function(e, modelName) {
                    if (watchedModels.indexOf(modelName) < 0) {
                        return;
                    }
                    $scope.selectedItem = null;
                    let m = appState.models[modelName];
                    const d = m.cutAxis;
                    const h = SIREPO.APP_SCHEMA.constants.heightAxisMap[d];
                    const w = radiaService.calcWidthAxis(d, h);
                    const dirs = radiaService.getGeomDirections(d, h, w);
                    m.cutDir = dirs.depth;
                    appState.saveQuietly(modelName);
                    if (! isEditing) {
                        $scope.field.push(m);
                        isEditing = true;
                    }
                    radiaService.saveGeometry(true, false,() => {
                        $scope.loadItems();
                    });
                });

                $scope.$on('cancelChanges', function(e, name) {
                    if (watchedModels.indexOf(name) < 0) {
                        return;
                    }
                    appState.removeModel(name);
                });

                $scope.loadItems();
            });

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
                        <div data-file-chooser="" data-input-file="inputFile" data-url="fileURL" data-title="title" data-description="description" data-require="true" data-file-formats="${IMPORT_FORMATS.join(',')}"></div>
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
            $scope.fileURL = null;
            $scope.isMissingImportFile = function() {
                return ! $scope.inputFile;
            };
            $scope.fileUploadError = '';
            $scope.isUploading = false;
            $scope.importDmpFile = function(inputFile) {
                if (! inputFile) {
                    return;
                }
                let data = null;
                let a = inputFile.name.split('.');
                let t = `${a[a.length - 1]}`;
                if (isRadiaImport(t)) {
                    data = newSimFromImport(inputFile);
                }
                importFile(inputFile, t, data);
            };

            function cleanup(simId) {
                $('#simulation-import').modal('hide');
                $scope.inputFile = null;
                URL.revokeObjectURL($scope.fileURL);
                $scope.fileURL = null;
                requestSender.localRedirectHome(simId);
            }

            function newSimFromImport(inputFile) {
                let model = appState.setModelDefaults(appState.models.simulation, 'simulation');
                model.name = inputFile.name.substring(0, inputFile.name.indexOf('.'));
                model.folder = fileManager.getActiveFolderPath();
                model.dmpImportFile = inputFile.name;
                model.notes = `Imported from ${inputFile.name}`;
                return model;
            }

            function importFile(inputFile, fileType, data={}) {
                let f = fileManager.getActiveFolderPath();
                if (fileManager.isFolderExample(f)) {
                    f = fileManager.rootFolder();
                }
                fileUpload.uploadFileToUrl(
                    inputFile,
                    {
                        folder: f,
                        arguments: importFileArguments(data)
                    },
                    requestSender.formatUrl(
                        'importFile',
                        {
                            '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                        }),
                    function(d) {
                        let simId = d.models.simulation.simulationId;
                        if (! isRadiaImport(fileType)) {
                            cleanup(simId);
                            return;
                        }
                        upload(inputFile, fileType, simId);
                    }, function (err) {
                        throw new Error(inputFile + ': Error during import ' + err);
                    });
            }

            // turn a dict into a delimited string so it can be added to the FormData.
            // works for simple values, not arrays or other dicts
            function importFileArguments(o) {
                let d = SIREPO.APP_SCHEMA.constants.inputFileArgDelims;
                let s = '';
                for (const k in o) {
                    s += `${k}${d.item}${o[k]}${d.list}`;
                }
                return s;
            }

            function isRadiaImport(fileType) {
                return RADIA_IMPORT_FORMATS.indexOf(`.${fileType}`) >= 0;
            }

            function upload(inputFile, fileType, simId) {
                fileUpload.uploadFileToUrl(
                    inputFile,
                    null,
                    requestSender.formatUrl(
                        'uploadFile',
                        {
                            '<simulation_id>': simId,
                            '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                            '<file_type>': SIREPO.APP_SCHEMA.constants.radiaDmpFileType,
                        }),
                    function(d) {
                        cleanup(simId);
                    }, function (err) {
                        throw new Error(inputFile + ': Error during upload ' + err);
                    });
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
    };
});

SIREPO.app.directive('fieldDownload', function(appState, geometry, panelState, radiaService, requestSender) {

    return {
        restrict: 'A',
        scope: {
        },
        template: `
            <div class="modal fade" tabindex="-1" role="dialog" id="sr-field-download" data-small-element-class="col-sm-2">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header bg-info">
                            <button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>
                            <span class="lead modal-title text-info">{{ svc.selectedPath.name }}</span>
                        </div>
                        <div class="modal-body">
                            <div class="form-horizontal">
                                <div class="form-group form-group-sm" data-ng-show="! isFieldMap()">
                                    <div class="control-label col-sm-5">
                                        <label><span>Field</span></label>
                                    </div>
                                    <div class="col-sm-5">
                                        <select data-ng-model="tModel.type" class="form-control">
                                            <option ng-repeat="t in svc.pointFieldTypes">{{ t }}</option>
                                        </select>
                                    </div>
                                </div>
                                <div class="control-label col-sm-5">
                                    <label><span>Export to</span></label>
                                </div>
                                <div class="form-group form-group-sm">
                                    <div class="col-sm-5">
                                        <select data-ng-model="tModel.exportType" class="form-control">
                                            <option ng-repeat="t in svc.pointFieldExportTypes">{{ t }}</option>
                                        </select>
                                    </div>
                                </div>
                                <div data-ng-show="tModel.exportType == \'SRW\'">
                                    <div class="control-label col-sm-5">
                                        <label><span>Magnetic Gap [mm]</span></label>
                                    </div>
                                    <div class="form-group form-group-sm">
                                        <div class="col-sm-5">
                                            <input data-string-to-number="" data-ng-model="tModel.gap" data-min="0" required />
                                        </div>
                                    </div>
                                </div>
                                <div class="row">
                                    <button data-ng-click="download()" class="btn btn-default col-sm-offset-6">Download</button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `,
        controller: function($scope, $element) {
            $scope.svc = radiaService;

            $scope.tModel = {
                exportType: radiaService.pointFieldExportTypes[0],
                gap: 0.0,
                type: radiaService.pointFieldTypes[0],
            };

            $scope.availableFieldTypes = function() {
                return radiaService.pointFieldTypes.filter(function(t) {

                });
            };

            $scope.download = function() {
                requestSender.newWindow('downloadDataFile', {
                    '<simulation_id>': appState.models.simulation.simulationId,
                    '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                    '<model>': 'fieldLineoutAnimation',
                    '<frame>': SIREPO.nonDataFileFrame,
                    '<suffix>': radiaService.pointFieldExports[$scope.tModel.exportType].extension
                });
                radiaService.showFieldDownload(false);
            };

            $scope.fieldType = function() {
                return $scope.isFieldMap() ? 'B' : $scope.tModel.type;
            };

            $scope.exportType = function() {
                return $scope.tModel.exportType;
            };

            $scope.isFieldMap = function() {
                return (radiaService.selectedPath || {}).type === 'fieldMap';
            };

            appState.whenModelsLoaded($scope, function () {
                $scope.tModel.gap = (appState.models.undulator || {}).gap || 0;
            });
        },
    };
});


SIREPO.app.directive('electronTrajectoryReport', function(appState, panelState) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@'
        },
        template: `
            <div class="col-md-6">
                <div data-ng-if="! dataCleared" data-report-panel="parameter" data-request-priority="0" data-model-name="electronTrajectoryReport"></div>
            </div>
        `,
        controller: function($scope) {
            $scope.dataCleared = true;
            $scope.model = appState.models[$scope.modelName];

            function setPanelHidden(doHide) {
                appState.models[$scope.modelName].hidePanel = doHide;
                appState.saveQuietly($scope.modelName);
                appState.autoSave();
            }

            if (appState.models[$scope.modelName].hidePanel === undefined) {
                setPanelHidden(true);
            }

            $scope.$on('radiaViewer.loaded', () => {
                $scope.dataCleared = false;
                panelState.setHidden($scope.modelName, appState.models[$scope.modelName].hidePanel);
            });

            $scope.$on(`panel.${$scope.modelName}.hidden`, (e, d) => {
                setPanelHidden(d);
            });
        },
    };
});

SIREPO.app.directive('fieldLineoutAnimation', function(appState, persistentSimulation, frameCache) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        template: `
            <div class="col-md-6">
              <div data-ng-if="showFieldLineoutPanel()" data-report-panel="parameter" data-model-name="fieldLineoutAnimation">
                <div data-sim-status-panel="simState"></div>
              </div>
            </div>
        `,
        controller: function($scope) {
            $scope.model = appState.models[$scope.modelName];
            $scope.dataCleared = true;
            $scope.simScope = $scope;
            $scope.simComputeModel = $scope.modelName;

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

            function setPath(p) {
                appState.models[$scope.modelName].lastModified = Date.now();
                if (p) {
                    appState.models[$scope.modelName].fieldPath = p;
                    if (p.axis) {
                        appState.models[$scope.modelName].plotAxis = p.axis;
                    }
                }
                appState.saveQuietly($scope.modelName);
            }

            function updatePath() {
                const p = getPath((appState.models[$scope.modelName].fieldPath || {}).id);
                if (p) {
                    setPath(p);
                }
                else {
                    delete appState.models[$scope.modelName].fieldPath;
                    setPath(appState.models.fieldPaths.paths[0]);
                }
            }

            $scope.hasPaths = () => {
                return appState.models.fieldPaths.paths && appState.models.fieldPaths.paths.length;
            };

            $scope.showFieldLineoutPanel = () => {
                return ! $scope.dataCleared && $scope.hasPaths();
            };

            $scope.$on('radiaViewer.loaded', () => {
                if ($scope.dataCleared && $scope.hasPaths()) {
                    $scope.simState.runSimulation();
                }
                $scope.dataCleared = false;
            });

            $scope.$on('fieldLineoutAnimation.saved', function () {
                if ($scope.showFieldLineoutPanel()) {
                    // Dont run automatically for sbatch or nersc
                    if (['sequential', 'parallel'].includes(appState.models.fieldLineoutAnimation.jobRunMode)) {
                        if (! $scope.simState.isProcessing()) {
                            $scope.simState.runSimulation();
                        }
                    }
                }
            });

            $scope.$on('fieldPaths.changed', updatePath);

            appState.watchModelFields($scope, [`${$scope.modelName}.fieldPath`],  () => {
                if (appState.models[$scope.modelName].fieldPath.axis) {
                    appState.models[$scope.modelName].plotAxis = appState.models[$scope.modelName].fieldPath.axis;
                }
            });

            updatePath();
            $scope.simState = persistentSimulation.initSimulationState($scope);
        },
    };
});

SIREPO.app.directive('fieldPathPicker', function(appState, panelState, radiaService) {

    return {
        restrict: 'A',
        scope: {
            modelName: '@',
            controller: '=',
            title: '@',
            id: '@',
            smallElementClass: '@',
        },
        template: `
            <div class="modal fade" data-ng-attr-id="{{ id }}" tabindex="-1" role="dialog">
              <div class="modal-dialog modal-lg">
                <div class="modal-content">
                  <div class="modal-header bg-info">
                    <button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>
                    <span class="lead modal-title text-info">{{ title }}</span>
                  </div>
                  <div class="modal-body">
                    <div class="container-fluid">
                      <div class="row">
                        <div data-field-editor="\'path\'" data-label-size="" data-field-size="3" style="text-align: right" data-model-name="modelName" data-model="model"></div>
                      </div>
                      <br />
                      <div class="row">
                        <div data-ng-repeat="type in pathTypes" data-ng-show="getPathType() == type" data-advanced-editor-pane="" data-view-name="radiaService.pathTypeModel(type)" data-field-def="basic" data-want-buttons="false">
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
        `,
        controller: function($scope, $element) {
            $scope.modelsLoaded = false;
            $scope.pathType = null;
            $scope.pathTypes = appState.enumVals('PathType');
            $scope.pathTypeModels = $scope.pathTypes.map(radiaService.pathTypeModel);
            $scope.radiaService = radiaService;

            $scope.getPathType = function() {
               return ($scope.model || {}).path;
            };

            appState.whenModelsLoaded($scope, function () {
                $scope.model = appState.models[$scope.modelName];
                $scope.pathTypes.forEach(t => {
                    $scope.$on(`${radiaService.pathTypeModel(t)}.changed`, () => {
                        radiaService.addOrModifyPath(t);
                    });
                });

                const el = $('#sr-fieldpaths-editor');
                el.on('hidden.bs.modal', function() {
                    appState.cancelChanges(radiaService.pathTypeModel($scope.getPathType()));
                    $scope.$apply();
                });

                $scope.$on('cancelChanges', function(e, name) {
                    if ($scope.pathTypeModels.indexOf(name) < 0) {
                        return;
                    }
                    appState.removeModel(name);
                    radiaService.showPathPicker(false);
                });
                $scope.$watch('model.path', function (m) {
                    const o = $($element).find('.modal').css('opacity');
                    if (o == 1 && ! radiaService.isEditing) {
                        // displaying editor but not editing, must be new
                        radiaService.createPathModel();
                    }
                });
                $scope.modelsLoaded = true;
            });
        },
    };
});

SIREPO.app.directive('fieldIntegralTable', function(appState, panelState, plotting, radiaService, requestSender, utilities) {
    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        template: `
            <div class="col-md-6">
                <div class="panel panel-info">
                    <div class="panel-heading">
                        <span class="sr-panel-heading">Field Integrals (T &#x00B7; mm)</span>
                        <div class="sr-panel-options pull-right">
                        <a data-ng-show="hasPaths()" data-ng-click="download()" target="_blank" title="Download"> <span class="sr-panel-heading glyphicon glyphicon-cloud-download" style="margin-bottom: 0"></span></a>
                        </div>
                    </div>
                    <div class="panel-body">
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
                            <tr data-ng-repeat="path in linePaths()">
                              <td>{{ path.name }}</td>
                              <td>[{{ path.begin }}] &#x2192; [{{ path.end }}]</td>
                              <td>
                                <div data-ng-repeat="t in INTEGRABLE_FIELD_TYPES"><span style="font-weight: bold">{{ t }}:</span> </span><span>{{ format(integrals[path.name][t]) }}</span></div>
                              </td>
                            </tr>
                          </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `,
        controller: function($scope) {

            $scope.CSV_HEADING = ['Line', 'x0', 'y0', 'z0', 'x1', 'y1', 'z1', 'Bx', 'By', 'Bz', 'Hx', 'Hy', 'Hz'];
            $scope.HEADING = ['Line', 'Endpoints', 'Fields'];
            $scope.INTEGRABLE_FIELD_TYPES = ['B', 'H'];
            $scope.integrals = {};
            $scope.model = appState.models[$scope.modelName];

            $scope.download = () => {
                const fileName = panelState.fileNameFromText('Field Integrals', 'csv');
                const data = [$scope.CSV_HEADING];
                $scope.linePaths().forEach(p => {
                    let row = [];
                    row.push(
                        p.name,
                        p.begin[0], p.begin[1], p.begin[2],
                        p.end[0], p.end[1], p.end[2]
                    );
                    $scope.INTEGRABLE_FIELD_TYPES.forEach(function (t) {
                        row = row.concat(
                            $scope.integrals[p.name][t]
                        );
                    });
                    data.push(row);
                });
                saveAs(new Blob([d3.csv.format(data)], {type: "text/csv;charset=utf-8"}), fileName);
            };

            $scope.hasPaths = () => $scope.linePaths().length;

            $scope.format = vals => {
                if (! vals) {
                    return [];
                }
                return vals.map(v => utilities.roundToPlaces(v, 4));
            };

            $scope.isLine = p => p.type === 'line' || p.type === 'axis';

            $scope.linePaths =  () => (($scope.model || {}).paths || []).filter($scope.isLine);

            function updateTable() {
                appState.models.fieldIntegralReport.lastCalculated = Date.now();
                appState.saveQuietly('fieldIntegralReport');
                panelState.clear('fieldIntegralReport');
                panelState.requestData('fieldIntegralReport', data => {
                    $scope.integrals = data;
                }, true);
            }

            $scope.$on('radiaViewer.loaded', updateTable);
            $scope.$on('fieldPaths.changed', updateTable);
        },
    };
});

SIREPO.app.directive('fieldPathTable', function(appState, geometry, panelState, radiaService, utilities) {
    return {
        restrict: 'A',
        scope: {
            paths: '='
        },
        template: `
            <table data-ng-if="hasPaths()" style="width: 100%; table-layout: fixed; margin-bottom: 10px" class="table radia-table-hover">
              <colgroup>
                <col style="width: 20ex">
                <col style="width: 10ex">
                <col style="width: 10ex">
                <col style="width: 100%">
                <col style="width: 10ex">
              </colgroup>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Num. points</th>
                  <th>Details</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr data-ng-repeat="path in paths track by $index">
                  <td><div class="badge sr-badge-icon sr-lattice-icon"><span>{{ path.name }}</span></div></td>
                  <td><span>{{ path.type }}</span></td>
                  <td><span>{{ path.numPoints }}</span></td>
                  <td><span>{{ pathDetails(path) }}</span></td>
                  <td style="text-align: right">
                    <div class="sr-button-bar-parent">
                        <div class="sr-button-bar" data-ng-class="sr-button-bar-active" >
                            <button class="btn btn-info btn-xs sr-hover-button" data-ng-click="copyPath(path)">Copy</button>
                             <button data-ng-click="editPath(path)" class="btn btn-info btn-xs sr-hover-button">Edit</button>
                             <button data-ng-click="svc.showFieldDownload(true, path)" class="btn btn-info btn-xs"><span class="glyphicon glyphicon-cloud-download"></span></button>
                             <button data-ng-click="deletePath(path, $index)" class="btn btn-danger btn-xs"><span class="glyphicon glyphicon-remove"></span></button>
                        </div>
                    <div>
                  </td>
                </tr>
              </tbody>
            </table>
        `,
        controller: function($scope) {
            const watchedModels = SIREPO.APP_SCHEMA.enum.PathType.map(function (e) {
                return e[SIREPO.ENUM_INDEX_VALUE];
            });

            $scope.paths = appState.models.fieldPaths.paths;
            $scope.svc = radiaService;

            $scope.hasPaths = () => $scope.paths && $scope.paths.length;

            $scope.copyPath = path => {
                const copy = appState.clone(path);
                copy.name = newPathName(copy);
                copy.id = radiaService.generateId();
                $scope.paths.push(copy);
                appState.saveChanges(['fieldPaths', radiaService.pathTypeModel(copy.type)], () => {
                    $scope.editPath(copy);
                });
            };

           $scope.deletePath = (path, index) => {
                $scope.paths.splice(index, 1);
                appState.saveChanges('fieldPaths');
           };

           $scope.editPath = path => {
               appState.models[radiaService.pathTypeModel(path.type)] = path;
               appState.models.fieldPaths.path = path.type;
               radiaService.showPathPicker(true, false);
           };

           $scope.pathDetails = path => {
               let res = '';
               const pt = radiaService.pathTypeModel(path.type);
               const d = SIREPO.APP_SCHEMA.constants.detailFields.fieldPath[pt];
               d.forEach((f, i) => {
                   res += (appState.modelInfo(pt)[f][0] + ': ' + path[f] + (i < d.length - 1 ? '; ' : ''));
               });
               return res;
           };

           function newPathName(path) {
               return appState.uniqueName(appState.models.fieldPaths, 'name', path.name + ' {}');
           }

           $scope.$on('axisPath.changed', (e, d) => {
               const m = appState.models.axisPath;
               m.name = `${m.axis.toUpperCase()}-Axis`;
               m.begin = geometry.basisVectors[m.axis].map(x => m.start * x);
               m.end = geometry.basisVectors[m.axis].map(x => m.stop * x);
               appState.saveQuietly('axisPath');
           });
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
            <div style="height: 200px; overflow-y: scroll; overflow-x: hidden;">
            <table style="table-layout: fixed;" class="table radia-table-hover">
                <tr style="background-color: lightgray;" data-ng-show="field.length > 0">
                  <th>Members</th>
                  <th></th>
                </tr>
                <tr data-ng-repeat="mId in field">
                    <td style="padding-left: 1em"><div class="badge sr-badge-icon"><span data-ng-drag="true" data-ng-drag-data="element">{{ getObject(mId).name }}</span></div></td>
                    <td style="text-align: right">&nbsp;<div class="sr-button-bar-parent"><div class="sr-button-bar">  <button data-ng-click="ungroupObject(mId)" class="btn btn-danger btn-xs"><span class="glyphicon glyphicon-remove"></span></button></div><div></td>
                </tr>
                <tr style="background-color: lightgray;">
                  <th>Ungrouped</th>
                  <th></th>
                </tr>
                <tr data-ng-repeat="oId in getIds() | filter:hasNoGroup">
                  <td style="padding-left: 1em"><div class="badge sr-badge-icon"><span data-ng-drag="true" data-ng-drag-data="element">{{ getObject(oId).name }}</span></div></td>
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
                    objs.push(...[mId, ...groupedObjects(mId)]);
                }
                return objs;
            }
        },
    };
});

SIREPO.app.directive('kickMapReport', function(appState, panelState, plotting, radiaService, requestSender, utilities) {
    return {
        restrict: 'A',
        scope: {
            direction: '@',
            viewName: '@',
        },
        template: `
            <div class="col-md-6">
                <div data-ng-if="! dataCleared" data-report-panel="3d" data-panel-title="Kick Map" data-model-name="kickMapReport"></div>
            </div>
        `,
        controller: function($scope) {

            $scope.dataCleared = true;

            $scope.model = appState.models.kickMapReport;
            $scope.$on('radiaViewer.loaded', () => {
                $scope.dataCleared = false;
            });

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
            });

        },
    };
});


// this kind of thing should be generic
SIREPO.app.directive('transformTable', function(appState, panelState, radiaService, $rootScope) {
    return {
        restrict: 'A',
        scope: {
            field: '=',
            fieldName: '=',
            itemClass: '@',
            model: '=',
            modelName: '=',
            parentController: '='
        },
        template: `
            <div data-toolbar="toolbarSections" data-item-filter="itemFilter" data-parent-controller="parentController"></div>
            <div class="sr-object-table">
              <p class="lead text-center"><small><em>drag and drop {{ itemClass.toLowerCase() }}s or use arrows to reorder the list</em></small></p>
              <div style="overflow-y: scroll; overflow-x: hidden; height: 100px;">
              <table class="table radia-table-hover" style="width: 100%; height: 15%; table-layout: fixed;">
                <tr data-ng-repeat="item in loadItems()">
                  <td data-ng-drop="true" data-ng-drop-success="dropItem($index, $data)" data-ng-drag-start="selectItem($data)">
                    <div class="sr-button-bar-parent pull-right"><div class="sr-button-bar"><button class="btn btn-info btn-xs"  data-ng-disabled="$index == 0" data-ng-click="moveItem(-1, item)"><span class="glyphicon glyphicon-arrow-up"></span></button> <button class="btn btn-info btn-xs" data-ng-disabled="$index == items.length - 1" data-ng-click="moveItem(1, item)"><span class="glyphicon glyphicon-arrow-down"></span></button> <button class="btn btn-info btn-xs sr-hover-button" data-ng-click="editItem(item)">Edit</button> <button data-ng-click="toggleExpand(item)" class="btn btn-info btn-xs"><span class="glyphicon" data-ng-class="{\'glyphicon-chevron-up\': isExpanded(item), \'glyphicon-chevron-down\': ! isExpanded(item)}"></span></button> <button data-ng-click="deleteItem(item)" class="btn btn-danger btn-xs"><span class="glyphicon glyphicon-remove"></span></button></div></div>
                    <div class="sr-command-icon-holder" data-ng-drag="true" data-ng-drag-data="item">
                      <a style="cursor: move; -moz-user-select: none; font-size: 14px" class="badge sr-badge-icon" data-ng-class="{\'sr-item-selected\': isSelected(item) }" href data-ng-click="selectItem(item)" data-ng-dblclick="editItem(item)">{{ itemName(item) }}</a>
                    </div>
                    <div data-ng-show="! isExpanded(item) && itemDetails(item)" style="margin-left: 3em; margin-right: 1em; color: #777; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{{ itemDetails(item) }}</div>
                    <div data-ng-show="isExpanded(item) && itemDetails(item)" style="color: #777; margin-left: 3em; white-space: pre-wrap">{{ itemDetails(item) }}</div>
                  </td>
                </tr>
                <tr><td style="height: 3em; text-align: center; color: #aaaaaa;" data-ng-drop="true" data-ng-drop-success="dropLast($data)"><em>*drop here*</em></td></tr>
              </table>
            </div>
            </div>
        `,
        controller: function($scope, $element) {
            const expanded = {};
            let isEditing = false;
            const spatialTransforms = [
                'rotate',
                'translate'
            ];
            let watchedModels;

            $scope.items = [];
            $scope.radiaService = radiaService;
            $scope.selectedItem = null;
            $scope.toolbarItems = [];
            $scope.toolbarSections = SIREPO.APP_SCHEMA.constants.toolbarItems.filter(section => {
                return $scope.modelName === 'cloneTransform' ?
                    section.name === 'Transforms (clone)' :
                    section.name === 'Transforms';
            });

            $scope.toolbarSections.forEach(s => {
                $scope.toolbarItems.push(...s.contents);
            });

            watchedModels = $scope.toolbarItems.map(item => item.model);

            function itemIndex(data) {
                return $scope.items.indexOf(data);
            }

            $scope.addItem = item => {
                $scope.editItem(item, true);
            };

            $scope.deleteItem = item => {
                const index = itemIndex(item);
                if (index < 0) {
                    return;
                }
                $scope.field.splice(index, 1);
                radiaService.saveGeometry(true);
            };

            $scope.editItem = (item, isNew) => {
                isEditing = ! isNew;
                $scope.selectedItem = item;
                if (isNew) {
                    appState.models[item.model] = appState.setModelDefaults({}, item.model);
                    appState.models[item.model].model = item.model;
                }
                else {
                    appState.models[item.model] = item;
                }
                panelState.showModalEditor(item.model);
            };

            $scope.dropItem = (index, data) => {
                if (! data) {
                    return;
                }
                const i = $scope.items.indexOf(data);
                if (i < 0) {
                    $scope.addItem(data);
                    return;
                }
                data = $scope.items.splice(i, 1)[0];
                if (i < index) {
                    index--;
                }
                $scope.items.splice(index, 0, data);
            };

            $scope.dropLast = item => {
                if (! item) {
                    return;
                }
                $scope.addItem(item);
            };

            $scope.getSelected = () => $scope.selectedItem;

            $scope.itemDetails = item => {
                let res = '';
                const d = SIREPO.APP_SCHEMA.constants.detailFields[$scope.fieldName][item.model];
                const info = appState.modelInfo(item.model);
                d.forEach((f, i) => {
                    let val = angular.isArray(item[f]) ? '[' + item[f].length + ']' : item[f];
                    if (info[f][SIREPO.INFO_INDEX_TYPE] === 'Boolean') {
                        val = val === '1';
                    }
                    res += (info[f][SIREPO.INFO_INDEX_LABEL] + ': ' + val + (i < d.length - 1 ? '; ' : ''));
                });
                return res;
            };

            $scope.isExpanded = item => expanded[itemIndex(item)];

            $scope.loadItems = () => {
                $scope.items = $scope.field;
                return $scope.items;
            };

            $scope.moveItem = (direction, item) => {
                const d = direction == 0 ? 0 : (direction > 0 ? 1 : -1);
                const currentIndex = itemIndex(item);
                const newIndex = currentIndex + d;
                if (newIndex >= 0 && newIndex < $scope.items.length) {
                    const tmp = $scope.items[newIndex];
                    $scope.items[newIndex] = item;
                    $scope.items[currentIndex] = tmp;
                }
            };

            $scope.toggleExpand = item => {
                expanded[itemIndex(item)] = ! expanded[itemIndex(item)];
            };

            $scope.itemFilter = item => {
                let iIdx = -1;
                for (const sIdx in $scope.toolbarSections) {
                    iIdx = $scope.toolbarSections[sIdx].contents.indexOf(item);
                    if (iIdx < 0) {
                        continue;
                    }
                    break;
                }
                // item not in sections presented
                if (iIdx < 0) {
                    return false;
                }
                // cannot nest
                if (item.model === $scope.modelName) {
                    return false;
                }
                if ($scope.modelName === 'cloneTransform') {
                    // don't include clone or symmetry if we are editing a clone already
                    return spatialTransforms.includes(item.type);
                }
                return true;
            };

            appState.whenModelsLoaded($scope, () => {

                $scope.$on('modelChanged', (e, modelName) => {
                    if (watchedModels.indexOf(modelName) < 0) {
                        return;
                    }
                    $scope.selectedItem = null;
                    if (! isEditing) {
                        appState.models[modelName].id = radiaService.generateId();
                        $scope.field.push(appState.models[modelName]);
                        isEditing = true;
                    }
                    radiaService.saveGeometry(true, false,() => {
                        $scope.loadItems();
                    });
                });

                $scope.$on('cancelChanges', (e, name) => {
                    $rootScope.$broadcast('drop.target.enabled', true);
                    if (! watchedModels.includes(name)) {
                        return;
                    }
                    appState.removeModel(name);
                });

                $scope.$on('$destroy', () => {
                    $rootScope.$broadcast('drop.target.enabled', true);
                });

                $scope.loadItems();
            });

            $rootScope.$broadcast('drop.target.enabled', false);
        },
    };
});

SIREPO.app.directive('radiaFieldPaths', function(appState, panelState, radiaService) {

    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        template: `
            <div class="col-md-6">
                <div class="panel panel-info">
                    <div class="panel-heading"><span class="sr-panel-heading">Field Paths</span></div>
                    <div class="panel-body">
                        <button class="btn btn-info btn-xs pull-right" accesskey="p" data-ng-click="radiaService.newPath()"><span class="glyphicon glyphicon-plus"></span> New <u>P</u>ath</button>
                        <div data-field-path-table="" data-paths="model.paths"></div>
                        <button class="btn btn-default col-sm-2 col-sm-offset-5" data-ng-show="hasPaths()" data-ng-click="confirmClear()">Clear</button>
                    </div>
                </div>
            </div>
            <div data-confirmation-modal="" data-id="sr-clear-paths-confirmation" data-title="Clear All Paths?" data-ok-text="OK" data-ok-clicked="clearPaths()">Clear All Paths?</div>
        `,
        controller: function($scope) {
            $scope.modelsLoaded = false;
            $scope.pathTypes = appState.enumVals('PathType');
            $scope.radiaService = radiaService;

            $scope.getPathType = () => ($scope.model || {}).path;

            $scope.clearPaths = () => {
                $scope.model.paths = [];
                appState.saveChanges($scope.modelName);
            };

            $scope.confirmClear = () => {
                $('#sr-clear-paths-confirmation').modal('show');
            };

            $scope.hasPaths = () => {
                if (! $scope.modelsLoaded) {
                    return false;
                }
                return $scope.model.paths && $scope.model.paths.length;
            };

            appState.whenModelsLoaded($scope, () => {
                $scope.model = appState.models[$scope.modelName];
                $scope.modelsLoaded = true;
            });
        },
    };
});

// does not need to be its own directive?  everything in viz and service? (and move template to html)
SIREPO.app.directive('radiaSolver', function(appState, errorService, frameCache, geometry, layoutService, panelState, radiaService, utilities) {

    return {
        restrict: 'A',
        scope: {
            viz: '<',
            modelName: '@',
        },
        template: `
            <div class="col-md-6">
                <div data-basic-editor-panel="" data-view-name="solverAnimation">
                        <div data-sim-status-panel="viz.simState" data-start-function="viz.startSimulation(modelName)"></div>
                        <div data-ng-show="viz.solution">
                                <div><strong>Time:</strong> {{ solution().time }}ms</div>
                                <div><strong>Step Count:</strong> {{ solution().steps }}</div>
                                <div><strong>Max |M|: </strong> {{ solution().maxM }} A/m</div>
                                <div><strong>Max |H|: </strong> {{ solution().maxH }} A/m</div>
                        </div>
                        <div data-ng-hide="viz.solution">No solution found</div>
                        <div class="col-sm-6 pull-right" style="padding-top: 8px;">
                            <button class="btn btn-default" data-ng-click="viz.resetSimulation()">Reset</button>
                        </div>
                    </div>
                </div>
            </div>
        `,
        controller: function($scope) {

            $scope.model = appState.models[$scope.modelName];

            $scope.solution = () => {
                const s = $scope.viz.solution;
                return {
                    time: s ? utilities.roundToPlaces(1000 * s.time, 3) : '',
                    steps: s ? s.steps : '',
                    maxM: s ? utilities.roundToPlaces(s.maxM, 4) : '',
                    maxH: s ?  utilities.roundToPlaces(s.maxH, 4) : '',
                };
            };

            $scope.reset = () => {
                $scope.viz.resetSimulation();
            };
        },
    };
});

SIREPO.app.directive('radiaViewer', function(appState, errorService, frameCache, geometry, layoutService, panelState, plotting, plotToPNG, radiaService, radiaVtkUtils, requestSender, utilities, vtkPlotting, vtkUtils, $interval, $rootScope) {

    return {
        restrict: 'A',
        transclude: true,
        scope: {
            modelName: '@',
            viewName: '@',
            viz: '<',
        },
        template: `
            <div class="col-md-6">
                <div class="panel panel-info" id="sr-magnetDisplay-basicEditor">
                  <div class="panel-heading clearfix" data-panel-heading="Magnet Viewer" data-view-name="magnetDisplay" data-is-report="true" data-model-key="modelKey" data-report-id="reportId"></div>
                    <div class="panel-body" data-ng-hide="panelState.isHidden(modelKey)">
                      <div data-advanced-editor-pane="" data-view-name="viewName" data-want-buttons="true" data-field-def="basic" data-model-data="modelData" data-parent-controller="parentController"></div>
                      <div data-ng-transclude="">
                        <div data-vtk-display="" class="vtk-display" data-ng-class="{'col-sm-11': isViewTypeFields()}" style="padding-right: 0" data-show-border="true" data-model-name="{{ modelName }}" data-report-id="reportId" data-event-handlers="eventHandlers" data-enable-axes="true" data-axis-cfg="axisCfg" data-axis-obj="axisObj" data-enable-selection="true" data-reset-side="x"></div>
                        <div class="col-sm-1" style="padding-left: 0" data-ng-if="isViewTypeFields()">
                            <div class="colorbar"></div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
            </div>
        `,
        controller: function($scope, $element) {
            $scope.reportId = utilities.reportId();
            $scope.axisObj = null;
            $scope.defaultColor = "#ff0000";
            $scope.mode = null;
            $scope.modelKey = 'magnetDisplay';

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
                 'magnetDisplay.viewType',
                 'magnetDisplay.fieldType',
            ];
            let displayVals = getDisplayVals();
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
                        let gObj = radiaService.getObject(objId) || {};
                        let gColor = gObj.color ? vtk.Common.Core.vtkMath.hex2float(gObj.color) : null;
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
                geometry.basis.forEach(function (dim, i) {
                    acfg[dim] = {};
                    acfg[dim].dimLabel = dim;
                    acfg[dim].label = dim + ' [mm]';
                    acfg[dim].max = bounds[2 * i + 1];
                    acfg[dim].min = bounds[2 * i];
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
                $scope.vtkScene.setCam();
                enableWatchFields(true);
            }

            function didDisplayValsChange() {
                const v = getDisplayVals();
                for (let i = 0; i < v.length; ++i) {
                    if (v[i] !== displayVals[i]) {
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
                const minLogMag = Math.min.apply(null, logMags);
                const maxLogMag = Math.max.apply(null, logMags);
                const minMag = Math.min.apply(null, vectors.magnitudes);
                const maxMag = Math.max.apply(null, vectors.magnitudes);
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
                if (renderer !== callData.pokedRenderer) {
                    return;
                }

                // regular clicks are generated when spinning the scene - we'll select/deselect with ctrl-click
                const iMode = $scope.vtkScene.interactionMode;
                if (iMode === vtkUtils.INTERACTION_MODE_MOVE ||
                    (iMode === vtkUtils.INTERACTION_MODE_SELECT && ! callData.controlKey)
                ) {
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

                const pas = picker.getActors();

                let selectedValue = Number.NaN;
                let highlightVectColor = [255, 0, 0];
                // the 1st actor in the array is the closest to the viewer
                const actor = pas[0];
                vtkSelection = {};
                const info = getInfoForActor(actor);
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
                        selectedValue = Math.min.apply(null, linArr.getData());
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
                displayVals = getDisplayVals();
                $rootScope.$broadcast('radiaViewer.loaded');
                $rootScope.$broadcast('vtk.hideLoader');
                sceneData = data;
                buildScene();
                if (! initDone) {
                    initDone = true;
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

            function updateViewer() {
                const c = didDisplayValsChange();
                sceneData = {};
                actorInfo = {};
                radiaService.objBounds = null;
                if (c || ! initDone) {
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

            $scope.$on('vtkScene.interactionMode', (e, d) => {
                if (d === SIREPO.VTK.VTKUtils.interactionMode().INTERACTION_MODE_MOVE) {
                    if (selectedObj) {
                        $scope.$broadcast('vtk.selected', null);
                        setEdgeColor(
                            getActorInfo(selectedObj.id),
                            [0, 0, 0]
                        );
                        selectedObj = null;
                        savedObj = null;
                    }
                }
            });

            $scope.$on('radiaObject.changed', function(e) {
                radiaService.saveGeometry(true, false);
            });

            $scope.$on('fieldPaths.changed', function () {
                if (! $scope.model.fieldPoints) {
                    $scope.model.fieldPoints = [];
                }
                const r = 'fieldLineoutAnimation';
                for (const p of appState.models.fieldPaths.paths) {
                    if (! appState.models[r].fieldPath || p.id === appState.models[r].fieldPath.id) {
                        appState.models[r].fieldPath = p;
                        appState.saveChanges(r);
                        break;
                    }
                }
                updateViewer();
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

            $scope.$on('magnetDisplay.changed',  (e, d) => {
                // does not seem the best way...
                let interval = null;
                interval = $interval(function() {
                    if (interval) {
                        $interval.cancel(interval);
                        interval = null;
                    }
                    // only fetch if we need different view or field
                    if (didDisplayValsChange()) {
                        updateViewer();
                    }
                }, 500, 1);

            });

            $scope.$on('framesCleared', updateViewer);
            $scope.$on('framesLoaded', (e, d) => {
                if (! initDone) {
                    return;
                }
                updateViewer();
            });

            $scope.$on('$destroy', () => {
                $element.off();
            });

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
                mins[j] =  Math.min(mins[j], Math.min.apply(null, c));
                maxs[j] =  Math.max(maxs[j], Math.max.apply(null, c));
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
            points.push(...t.vertices);
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

    function setPoints(data) {
        $scope.modelData.referencePoints = data.points;
        radiaService.updateExtruded($scope.modelData, () => {
            appState.saveChanges(editedModels);
            updateShapeEditor();
        });
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

SIREPO.viewLogic('geomObjectView', function(appState, panelState, radiaService, requestSender, $scope) {

    let editedModels = [];

    $scope.watchFields = [
        [
            'geomObject.type',
        ], updateObjectEditor
    ];

    $scope.whenSelected = () => {
        $scope.modelData = appState.models[$scope.modelName];
        editedModels = radiaService.updateModelAndSuperClasses($scope.modelData.type, $scope.modelData);
        updateObjectEditor();
    };

    $scope.$on('geomObject.changed', () => {
        if (editedModels.includes('extrudedPoly')) {
            radiaService.updateExtruded($scope.modelData);
        }
        editedModels = [];
    });


    function updateObjectEditor() {
        const o = $scope.modelData;
        if (! o) {
            return;
        }
        panelState.showField('geomObject', 'materialFile', o.material === 'custom');

        panelState.enableField('geomObject', 'size', true);

        if (o.type === 'stl') {
            panelState.enableField('geomObject', 'size', false);
            //TODO(BG): Only disables 'size' field, need to build shape to get sizes to update values (likely will need to send request since python)
        }

        if (o.type !== 'extrudedPoints') {
            return;
        }

        for (const dim of [o.widthAxis, o.heightAxis]) {
            panelState.enableArrayField(
                'geomObject',
                'size',
                SIREPO.GEOMETRY.GeometryUtils.BASIS().indexOf(dim),
                false
            );
        }
        panelState.enableArrayField(
            'geomObject',
            'size',
            SIREPO.GEOMETRY.GeometryUtils.BASIS().indexOf(o.extrusionAxis),
            true
        );
    }


    const self = {};
    self.getBaseObject = () => $scope.modelData;
    return self;
});

for(const m of ['Dipole', 'Undulator']) {
    for (const d of SIREPO.APP_SCHEMA.enum[`${m}Type`]) {
        SIREPO.viewLogic(`${d[0]}View`, function(appState, panelState, radiaService, validationService, $scope) {

            $scope.model = appState.models[$scope.modelName];
            $scope.watchFields = [];

            let editedModels = [];
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

            //TODO(mvk): implement validation for parameterized magnets - this is a placeholder
            const e = `watch${m}Editor`;
            if (e in SIREPO) {
                SIREPO[e]($scope, appState, panelState, radiaService, validationService);
            }
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
