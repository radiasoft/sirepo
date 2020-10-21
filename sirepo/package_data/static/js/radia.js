'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

SIREPO.app.config(function() {
    SIREPO.appDefaultSimulationValues.simulation.beamAxis = 'z';
    SIREPO.SINGLE_FRAME_ANIMATION = ['solver'];
    SIREPO.appFieldEditors += [
        '<div data-ng-switch-when="Color" data-ng-class="fieldClass">',
          '<div data-color-picker="" data-form="form" data-color="model.color" data-model-name="modelName" data-model="model" data-field="field" data-default-color="defaultColor"></div>',
        '</div>',
        '<div data-ng-switch-when="FloatStringArray" class="col-sm-7">',
            '<div data-number-list="" data-model="model" data-field="model[field]" data-info="info" data-type="Float" data-count=""></div>',
        '</div>',
        '<div data-ng-switch-when="IntStringArray" class="col-sm-7">',
            '<div data-number-list="" data-model="model" data-field="model[field]" data-info="info" data-type="Integer" data-count=""></div>',
        '</div>',
        '<div data-ng-switch-when="Group" class="col-sm-12">',
          '<div data-group-editor="" data-field="model[field]" data-model="model"></div>',
        '</div>',
        '<div data-ng-switch-when="TransformTable" class="col-sm-12">',
          '<div data-transform-table="" data-field="model[field]" data-field-name="field" data-model="model" data-model-name="modelName" data-item-class="Transform" data-parent-controller="parentController"></div>',
        '</div>',
        '<div data-ng-switch-when="PtsFile" data-ng-class="fieldClass">',
          '<input id="radia-pts-file-import" type="file" data-file-model="model[field]" accept=".dat,.txt"/>',
        '</div>',
        //'<div data-ng-switch-when="HMFile" data-ng-class="HMFile">',
        //  '<input id="radia-h-m-file-import" type="file" data-file-model="model[field]" accept=".dat,.txt"/>',
        //'</div>',
        //'<div data-ng-switch-when="HMFile" class="fieldClass">',
        //  '<div data-file-field="field" data-model="model" data-file-type="h-m" data-empty-selection-text="No File Selected"></div>',
        //'</div>',
    ].join('');
    SIREPO.appPanelHeadingButtons = [
        '<div style="display: inline-block">',
        '<a data-ng-click="download()" title="Download"> <span class="sr-panel-heading glyphicon glyphicon-cloud-download" style="margin-bottom: 0"></span></a> ',
        //'<ul class="dropdown-menu dropdown-menu-right">',
        //'<li data-export-python-link="" data-report-title="{{ reportTitle() }}"></li>',
        //'</ul>',
        '</div>',
    ].join('');
});

SIREPO.app.factory('radiaService', function(appState, fileUpload, panelState, requestSender) {
    var self = {};

    // why is this here? - answer: for getting frames
    self.computeModel = function(analysisModel) {
        return 'solver';
    };

    appState.setAppService(self);

    self.isEditing = false;
    self.objBounds = null;
    self.pointFieldTypes = appState.enumVals('FieldType').slice(1);
    self.selectedObject = null;

    self.addOrModifyPath = function(type) {
        var p = appState.models[self.pathTypeModel(type)];
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
        var m = 'geometry';
        var f = 'alpha';
        var d = panelState.getFieldDelegate(m, f);
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

    self.createPathModel = function(type) {
        var t = type || self.pathTypeModel(appState.models.fieldPaths.path);
        var model = {
            id: numPathsOfType(appState.models.fieldPaths.path),
        };
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

    self.getObject = function(id) {
        var objs = appState.models.geometry.objects || [];
        for (var i in objs) {
            if (objs[i].id == id) {
                return objs[i];
            }
        }
        return null;
    };

    self.getObjects = function() {
        return appState.models.geometry.objects || [];
    };

    self.getPathType = function() {
        return (appState.models.fieldTypes || {}).path;
    };

    self.getRadiaData = function(inData, handler) {
        // store inData on the model, so that we can refer to it if
        // getApplicationData fails
        requestSender.getApplicationData(inData, function (d) {
            if (d.error) {
                throw new Error(d.error);
            }
            handler(d);
        });
    };

    self.getSelectedObject = function() {
        return self.selectedObject;
    };

    self.newPath = function() {
        self.showPathPicker(true, true);
    };

    self.pathEditorTitle = function() {
        if (! appState.models.fieldPaths) {
            return '';
        }
        return (self.isEditing ? 'Edit ' : 'New ') + appState.models.fieldPaths.path;
    };

    self.pathTypeModel = function(type) {
        return type + 'Path';
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

    self.stringToFloatArray = function (str, scale) {
        return str.split(/\s*,\s*/)
            .map(function (v) {
                return (scale || 1.0) * parseFloat(v);
            });
    };

    self.upload = function(inputFile) {
        upload(inputFile);
    };

    function findPath(path) {
        for(var i = 0; i < (appState.models.fieldPaths.paths || []).length; ++i) {
            var p = appState.models.fieldPaths.paths[i];
            if (p.type === path.type && p.id === path.id) {
                return path;
            }
        }
        return null;
    }

    function numPathsOfType(type) {
        return (appState.models.fieldPaths.paths || []).filter(function (p) {
            return p.type === type;
        }).length;
    }

    function toFloat(v) {
        return parseFloat('' + v);
    }
    function toInt(v) {
        return parseInt('' + v);
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

SIREPO.app.controller('RadiaSourceController', function (appState, geometry, panelState, plotting, radiaService, vtkPlotting, $scope) {
    var self = this;

    const editorFields = [
        'geomObject.magnetization',
        'geomObject.material',
        'geomObject.symmetryType',
        'geomObject.doDivide',
    ];
    const groupModels = [
        'geomGroup',
        'geomUndulatorGroup'
    ];
    var watchedModels = [
        'geomObject',
        'geomGroup',
        'radiaObject'
    ];

    self.builderCfg = {
        fitToObjects: true,
        fixedDomain: false,
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


    self.copyObject = function(o) {
        var copy = appState.clone(o);
        copy.name = newObjectName(copy);
        addObject(copy);
        self.editObject(copy);
    };

    self.editTool = function(tool) {
        if (tool.isInactive) {
            return;
        }
        panelState.showModalEditor(tool.model);
    };

    self.deleteObject = function(o) {
        const oIdx = appState.models.geometry.objects.indexOf(o);
        if (oIdx < 0) {
            return;
        }
        deleteShapesForObject(o);
        for (var i in (o.members || [])) {
            self.getObject(o.members[i]).groupId = '';
        }
        appState.models.geometry.objects.splice(oIdx, 1);
        appState.saveChanges('geometry');
    };

    self.editItem = function(o) {
        self.editObject(o);
    };

    self.editObjectWithId = function(id) {
        var o = self.getObject(id);
        if (! o) {
            return;
        }
        self.editObject(o);
    };

    self.editObject = function(o) {
        self.selectObject(o);
        panelState.showModalEditor(o.model);
    };

    self.getObject = function(id) {
        return radiaService.getObject(id);
    };

    self.getObjects = function() {
        return radiaService.getObjects();
    };

    self.getShape = function(id) {
        return self.shapes.filter(function (s) {
            return s.id === id;
        })[0];
    };

    self.getShapes = function() {
        return self.shapes;
    };

    self.isDropEnabled = function() {
        return self.dropEnabled;
    };

    self.isEditable = function() {
        return true;
    };

    self.nextId = function() {
        return appState.maxId(appState.models.geometry.objects, 'id') + 1;
    };

    self.objectBounds = function() {
        return groupBounds();
    };

    self.objectsOfType = function(type) {
        return appState.models.geometry.objects.filter(function (o) {
            return o.type === type;
        });
    };

    self.objectTypes = function() {
        var t = [];
        appState.models.geometry.objects.forEach(function (o) {
            if (t.indexOf(o.type) < 0) {
                t.push(o.type);
            }
        });
        return t.sort();
    };

    self.pass = function() {
        return function(item) {
            return true;
        };
    };

    self.saveObject = function(id, callback) {
        if (! self.selectObjectWithId(id)) {
            return;
        }
        appState.saveChanges('geomObject', function (d) {
            transformShapesForObjects();
            self.selectedObject = null;
            radiaService.setSelectedObject(null);
            if (callback) {
                callback(d);
            }
        });
    };

    self.selectObject = function(o) {
        if (o) {
            self.selectedObject = o;
            radiaService.setSelectedObject(o);
            appState.models[panelState.getBaseModelKey(o.model)] = o;
        }
        return o;
    };

    self.selectObjectWithId = function(id) {
        return self.selectObject(self.getObject(id));
    };

    self.shapeBounds = function() {
        return shapesBounds(self.shapes);
    };

    // seems like a lot of this shape stuff can be refactored out to a common area
    self.shapeForObject = function(o) {
        var center = radiaService.stringToFloatArray(o.center || SIREPO.ZERO_STR, SIREPO.APP_SCHEMA.constants.objectScale);
        var size =  radiaService.stringToFloatArray(o.size || SIREPO.ZERO_STR, SIREPO.APP_SCHEMA.constants.objectScale);
        var isGroup = o.members && o.members.length;  //false;

        if (o.members && o.members.length) {
            isGroup = true;
            var b = groupBounds(o.members.map(function (id) {
                return self.getObject(id);
            }));
            center = b.map(function (c) {
                return (c[0] + c[1]) / 2;
            });
            size = b.map(function (c) {
                return Math.abs((c[1] - c[0]));
            });
        }

        var shape = vtkPlotting.plotShape(
            o.id, o.name,
            center, size,
            o.color, 0.3, isGroup ? null : 'solid', isGroup ? 'dashed' : 'solid', null,
            o.layoutShape
        );
        if (isGroup) {
            shape.outlineOffset = 5.0;
            shape.strokeWidth = 0.75;
            shape.draggable = false;
        }
        return shape;
    };

    function addObject(o) {
        o.id  = self.nextId();
        o.mapId = getMapId(o);
        appState.models.geometry.objects.push(o);
        // for groups, set the group id of all members
        //var n = 0;
        (o.members || []).forEach(function (oId) {
            self.getObject(oId).groupId = o.id;
        //    ++n;
        });
        //if (n > 0) {
        //    let z = groupBounds(o.members);
        //    o.size = '0,0,0';
        //}
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
        for (let m of getMembers(o)) {
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
        //srdbg('shapes', self.shapes);
        //srdbg(o.id, 'num shapes', self.shapes.length);
    }

    function transformMembers(o, xform, txFunction, excludedIds=[]) {
        if (! o) {
            return;
        }
        let txm = [];
        for (let m of getMembers(o)) {
            let shape = self.getShape(m.id);
            let v = getVirtualShapes(shape, excludedIds);
            txm.push(addTxShape(shape, xform, txFunction).id);
            for (let s of v) {
                txm.push(addTxShape(s, xform, txFunction).id);
            }
        }
        return txm;
    }

    // recursive dive through all subgroups
    function getMembers(o) {
        if (! o) {
            return [];
        }
        let members = (o.members || []).map(function (id) {
            return self.getObject(id);
        });
        for (let m of members) {
            members.push(...getMembers(m));
        }
        return members;
    }

    function addSymmetryPlane(baseShape, xform) {
        let plIds = [];
        for (let p in vtkPlotting.COORDINATE_PLANES) {
            const cpl = geometry.plane(vtkPlotting.COORDINATE_PLANES[p], geometry.point());
            const spl = geometry.plane(
                radiaService.stringToFloatArray(xform.symmetryPlane),
                geometry.pointFromArr( radiaService.stringToFloatArray(
                    xform.symmetryPoint,
                    SIREPO.APP_SCHEMA.constants.objectScale)
                ));
            if (cpl.equals(spl) || ! spl.intersection(cpl)) {
                continue;
            }
            var pl = vtkPlotting.plotLine(
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

    function transformShapesForObject(o) {
        let baseShape = self.getShape(o.id);
        [baseShape, ...getVirtualShapes(baseShape)].forEach(function (s) {
            s.runLinks();
        });
    }

    function transformShapesForObjects() {
        for (let o of self.getObjects()) {
            transformShapesForObject(o);
        }
    }

    function composeFn(fnArr) {
        return function(shape1, shape2) {
            var prevShape = shape1;
            fnArr.forEach(function (tx) {
                prevShape = tx(prevShape, shape2);
            });
            return shape2;
        };
    }

    function deleteShapesForObject(o) {
        for (let s of getTransformedShapes(o)) {
            self.shapes.splice(indexOfShape(s), 1);
        }
        let shape = self.shapeForObject(o);
        for (let s of getVirtualShapes(shape)) {
            self.shapes.splice(indexOfShape(s), 1);
        }
        self.shapes.splice(indexOfShape(shape), 1);
    }

    // shape - in group; linkedShape: group
    function fit(shape, groupShape) {
        const o = self.getObject(shape.id);
        const groupId = o.groupId;
        if (groupId === '' || groupId !== groupShape.id) {
            groupShape.center = shape.center.join(',');
            groupShape.size = shape.size.join(',');
            return groupShape;
        }
        let mShapes = self.getObject(groupShape.id).members.map(function (mId) {
            return self.getShape(mId);
        }).filter(function (s) {
            return ! ! s;
        });
        const newBounds = shapesBounds(mShapes);
        for (let dim in newBounds) {
            groupShape.size[dim] = Math.abs(newBounds[dim][1] - newBounds[dim][0]);
            groupShape.center[dim] = newBounds[dim][0] + groupShape.size[dim] / 2;
        }
        return groupShape;
    }

    // used to map the client-created object to a server-created Radia id
    function getMapId(o) {
        return o.name + '.' + o.id;
    }

    function groupBounds(objs) {
        let b = [
            [Number.MAX_VALUE, -Number.MAX_VALUE],
            [Number.MAX_VALUE, -Number.MAX_VALUE],
            [Number.MAX_VALUE, -Number.MAX_VALUE]
        ];
        b.forEach(function (c, i) {
            (objs || appState.models.geometry.objects || []).forEach(function (o) {
                var ctr =  radiaService.stringToFloatArray(o.center || SIREPO.ZERO_STR, SIREPO.APP_SCHEMA.constants.objectScale);
                var sz =  radiaService.stringToFloatArray(o.size || SIREPO.ZERO_STR, SIREPO.APP_SCHEMA.constants.objectScale);
                c[0] = Math.min(c[0], ctr[i] - sz[i] / 2);
                c[1] = Math.max(c[1], ctr[i] + sz[i] / 2);
            });
        });
        return b;
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
        for (let s of v) {
            v2.push(...getVirtualShapes(s, excludedIds));
        }
        v.push(...v2);
        return v;
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
        appState.models.geometry.objects.forEach(function (o) {
            addShapesForObject(o);
        });
    }

    function mirrorFn(xform) {
        return function (shape1, shape2) {
            var pl = geometry.plane(
                radiaService.stringToFloatArray(xform.symmetryPlane),
                geometry.pointFromArr(radiaService.stringToFloatArray(xform.symmetryPoint, SIREPO.APP_SCHEMA.constants.objectScale))
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
        return appState.uniqueName(appState.models.geometry.objects, 'name', o.name + ' {}');
    }

    function offsetFn(xform, i) {
        return function(shape1, shape2) {
            const d = radiaService.stringToFloatArray(xform.distance, SIREPO.APP_SCHEMA.constants.objectScale);
            shape2.setCenter(
                shape1.getCenterCoords().map(function (c, j) {
                    return c + i * d[j];
                })
            );
            return shape2;
        };
    }

    function rotateFn(xform, i) {
        return function(shape1, shape2) {
            var ctr =  radiaService.stringToFloatArray(xform.center, SIREPO.APP_SCHEMA.constants.objectScale);
            var axis =  radiaService.stringToFloatArray(xform.axis, SIREPO.APP_SCHEMA.constants.objectScale);
            // need a 4-vector to account for translation
            var shapeCtr4 = shape1.getCenterCoords();
            shapeCtr4.push(0);
            var angle = Math.PI * parseFloat(xform.angle) / 180.0;
            var a = i * angle;
            var m = geometry.rotationMatrix(ctr, axis, a);
            shape2.setCenter(geometry.vectorMult(m, shapeCtr4));
            shape2.rotationAngle = -180.0 * a / Math.PI;
            return shape2;
        };
    }

    function shapesBounds(shapes) {
        let b = {
            x: [Number.MAX_VALUE, -Number.MAX_VALUE],
            y: [Number.MAX_VALUE, -Number.MAX_VALUE],
            z: [Number.MAX_VALUE, -Number.MAX_VALUE]
        };
        shapes.forEach(function (s) {
            let vs = getVirtualShapes(s);
            let sr = shapesBounds(vs);
            for (let dim in b) {
                b[dim] = [
                    Math.min(b[dim][0], s.center[dim] - s.size[dim] / 2, sr[dim][0]),
                    Math.max(b[dim][1], s.center[dim] + s.size[dim] / 2, sr[dim][1])
                ];
            }
        });
        return b;
    }

    function txShape(shape, tx) {
        var sh = vtkPlotting.plotShape(
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

    function updateObjectEditor() {
        var o = self.selectedObject;
        if (! o) {
            return;
        }
        panelState.showField(
            'geomObject',
            'division',
            o.doDivide == '1'
        );
        panelState.showField(
            'geomObject',
            'materialFile',
            o.material === 'custom'
        );
        //srdbg('mf', o.materialFile);
        //let form = panelState.getForm('geomObject', 'materialFile');
        //if (o.material === 'custom') {
        //    if (! o.materialFile) {
        //        form.$valid = false;
        //    }
        //}
        //panelState.showField(
        //    'geomObject',
        //    'symmetryPlane',
        //    //o.symmetryType != 'none'
        //);
        //panelState.showField(
        //    'geomObject',
        //    'symmetryPoint',
        //    //o.symmetryType != 'none'
        //);
        var mag = (o.magnetization || SIREPO.ZERO_STR).split(/\s*,\s*/).map(function (m) {
            return parseFloat(m);
        });
        //panelState.showField(
        //    'geomObject',
        //    'material',
        //    true  //Math.hypot(mag[0], mag[1], mag[2]) > 0
        //);
    }

    function updateToolEditor(toolItem) {
    }

    function virtualShapeId(shape) {
        return `${shape.id}-${Math.floor(Math.random() * Number.MAX_SAFE_INTEGER)}`;
    }

    function baseShapeId(id) {
        return `${id}`.split('-')[0];
    }

    function hasBaseShape(shape, baseShape) {
        // base shape is not its own base
        if (shape.id === baseShape.id) {
            return false;
        }
        return baseShapeId(shape.id) === `${baseShape.id}`;
    }

    appState.whenModelsLoaded($scope, function() {
        // initial setup
        appState.watchModelFields($scope, editorFields, function(d) {
            updateObjectEditor();
        });
        if (! appState.models.geometry.objects) {
            appState.models.geometry.objects = [];
        }
        loadShapes();

        $scope.$on('modelChanged', function(e, modelName) {
            if (watchedModels.indexOf(modelName) < 0) {
                return;
            }
            var o = self.selectedObject;
            if (o.id !== 0 && (angular.isUndefined(o.id) || o.id === '')) {
                // catch unrelated saved objects
                if (o.model === modelName || panelState.getBaseModelKey(o.model) === modelName) {
                    addObject(o);
                }
                else {
                    self.selectedObject = null;
                }
            }
            if (o.materialFile) {
                o.hmFileName = o.materialFile.name;
                radiaService.upload(o.materialFile, SIREPO.APP_SCHEMA.constants.hmFileType);
            }
            appState.saveChanges('geometry', function (d) {
                //srdbg('geometry ch', self.selectedObject);
                if (self.selectedObject) {
                    loadShapes();
                }
                //self.selectedObject = null;
                //loadShapes();
            });
        });
        $scope.$on('geomObject.editor.show', function(e, o) {
            updateObjectEditor();
        });
        $scope.$on('tool.editor.show', function(e, o) {
            updateToolEditor();
        });
        $scope.$on('layout.object.dropped', function (e, lo) {
            var m = appState.setModelDefaults({}, lo.model);
            m.center = lo.center;
            m.name = lo.type;
            m.name = newObjectName(m);
            m.model = lo.model;
            self.editObject(m);
        });
        $scope.$on('drop.target.enabled', function (e, val) {
            self.dropEnabled = val;
        });
    });
});

SIREPO.app.controller('RadiaVisualizationController', function (appState, errorService, frameCache, panelState, persistentSimulation, radiaService, utilities, $scope) {
    var SINGLE_PLOTS = ['magnetViewer'];
    var self = this;
    self.simScope = $scope;
    $scope.mpiCores = 0;
    $scope.panelState = panelState;
    $scope.svc = radiaService;

    self.solution = null;

    self.simHandleStatus = function(data) {
        if (data.error) {
            throw new Error('Solver failed: ' + data.error);
        }
        //$scope.mpiCores = data.mpiCores > 1 ? data.mpiCores : 0;
        SINGLE_PLOTS.forEach(function(name) {
            frameCache.setFrameCount(0, name);
        });
        if ('percentComplete' in data && ! data.error) {
            if (data.percentComplete === 100 && ! self.simState.isProcessing()) {
                self.solution = data.solution;
                SINGLE_PLOTS.forEach(function(name) {
                    frameCache.setFrameCount(1, name);
                });
            }
        }
        frameCache.setFrameCount(data.frameCount);
    };

    self.startSimulation = function() {
        self.solution = null;
        $scope.$broadcast('solveStarted', self.simState);
        self.simState.saveAndRunSimulation('simulation');
    };

    self.simState = persistentSimulation.initSimulationState(self);
});


SIREPO.app.directive('appFooter', function() {
    return {
        restrict: 'A',
        scope: {
            nav: '=appFooter',
        },
        template: [
            '<div data-common-footer="nav"></div>',
            '<div data-dmp-import-dialog="" data-title="Dump File" data-description="Import Radia dump file"></div>',
        ].join(''),
    };
});

SIREPO.app.directive('appHeader', function(appState, requestSender) {
    return {
        restrict: 'A',
        scope: {
            nav: '=appHeader',
        },
        template: [
            '<div data-app-header-brand="nav"></div>',
            '<div data-app-header-left="nav"></div>',
            '<div data-app-header-right="nav">',
              '<app-header-right-sim-loaded>',
                '<div data-sim-sections="">',
                  '<li data-ng-if="! isImported()" class="sim-section" data-ng-class="{active: nav.isActive(\'source\')}"><a href data-ng-click="nav.openSection(\'source\')"><span class="glyphicon glyphicon-magnet"></span> Design</a></li>',
                  '<li class="sim-section" data-ng-class="{active: nav.isActive(\'visualization\')}"><a href data-ng-click="nav.openSection(\'visualization\')"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>',
                '</div>',
              '</app-header-right-sim-loaded>',
              '<app-settings>',
                    '<li><a href data-ng-click="exportDmp()"><span class="glyphicon glyphicon-cloud-download"></span> Export Radia Dump</a></li>',
              '</app-settings>',
              '<app-header-right-sim-list>',
                '<ul class="nav navbar-nav sr-navbar-right">',
                  '<li><a href data-ng-click="showImportModal()"><span class="glyphicon glyphicon-cloud-upload"></span> Import</a></li>',
                '</ul>',
              '</app-header-right-sim-list>',
            '</div>',
        ].join(''),
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
                return (appState.models.simulation || {}).isExample ||
                    (appState.models.simulation || {}).dmpImportFile;
            };
        }
    };
});

SIREPO.app.directive('dmpImportDialog', function(appState, fileManager, fileUpload, requestSender) {
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
                        '<div data-file-chooser="" data-input-file="inputFile" data-url="fileURL" data-title="title" data-description="description" data-require="true"></div>',
                          '<div class="col-sm-6 pull-right">',
                            '<button data-ng-click="importDmpFile(inputFile)" class="btn btn-primary" data-ng-class="{\'disabled\': isMissingImportFile() }">Import File</button>',
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
            $scope.title = $scope.title || 'Import Dump File';
            $scope.description = $scope.description || 'Select File';

            $scope.importDmpFile = function(inputFile) {
                if (! inputFile) {
                    return;
                }
                newSimFromDmp(inputFile);
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
                            '<file_type>': SIREPO.APP_SCHEMA.constants.radiaDmpFileType,
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

            function newSimFromDmp(inputFile) {
                var url = $scope.fileURL;
                var model = appState.setModelDefaults(appState.models.simulation, 'simulation');
                model.name = inputFile.name.substring(0, inputFile.name.indexOf('.'));
                model.folder = fileManager.getActiveFolderPath();
                model.dmpImportFile = inputFile.name;
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
    };
});

SIREPO.app.directive('fieldDownload', function(appState, geometry, panelState, radiaService, requestSender) {

    return {
        restrict: 'A',
        scope: {
        },
        template: [
            '<div class="modal fade" tabindex="-1" role="dialog" id="sr-field-download" data-small-element-class="col-sm-2">',
                '<div class="modal-dialog modal-lg">',
                    '<div class="modal-content">',
                        '<div class="modal-header bg-info">',
                            '<button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>',
                            '<span class="lead modal-title text-info">{{ svc.selectedPath.name }}</span>',
                        '</div>',
                        '<div class="modal-body">',
                            '<div class="form-horizontal">',
                                '<div class="form-group form-group-sm" data-ng-show="! isFieldMap()">',
                                    '<div class="control-label col-sm-5">',
                                        '<label><span>Field</span></label>',
                                    '</div>',
                                    '<div class="col-sm-5">',
                                        '<select data-ng-model="tModel.type" data-ng-change="ch()" class="form-control">',
                                            '<option ng-repeat="t in svc.pointFieldTypes">{{ t }}</option>',
                                        '</select>',
                                    '</div>',
                                '</div>',
                                '<div class="row">',
                                    '<button data-ng-click="download()" class="btn btn-default col-sm-offset-6">Download</button>',
                                '</div>',
                            '</div>',
                        '</div>',
                    '</div>',
                '</div>',
            '</div>',
        ].join(''),
        controller: function($scope, $element) {
            $scope.svc = radiaService;

            $scope.tModel = {
                type: radiaService.pointFieldTypes[0],
            };

            $scope.download = function() {
                var p = radiaService.selectedPath;
                var f = p.name + ' ' + $scope.fieldType();
                var ext = $scope.isFieldMap() ? 'sdds' : 'csv';
                var fn = panelState.fileNameFromText(f, ext);
                var ct = $scope.isFieldMap() ? 'application/octet-stream' : 'text/csv;charset=utf-8';
                requestSender.getApplicationData(
                    {
                        beamAxis: appState.models.simulation.beamAxis,
                        contentType: ct,
                        fieldPaths: [radiaService.selectedPath],
                        fieldType: $scope.fieldType(),
                        fileType: $scope.isFieldMap() ? 'sdds' : 'csv',
                        method: 'save_field',
                        name: radiaService.selectedPath.name,
                        simulationId: appState.models.simulation.simulationId,
                        viewType: 'fields',
                    },
                    function(d) {
                        saveAs(new Blob([d], {type: ct}), fn);
                        radiaService.showFieldDownload(false);
                    },
                    fn
                );
            };

            $scope.fieldType = function() {
                return $scope.isFieldMap() ? 'B' : $scope.tModel.type;
            };

            $scope.isFieldMap = function() {
                return (radiaService.selectedPath || {}).type === 'fieldMap';
            };

            appState.whenModelsLoaded($scope, function () {
            });
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
        template: [
            '<div class="modal fade" data-ng-attr-id="{{ id }}" tabindex="-1" role="dialog">',
              '<div class="modal-dialog modal-lg">',
                '<div class="modal-content">',
                  '<div class="modal-header bg-info">',
                    '<button type="button" class="close" data-dismiss="modal"><span>&times;</span></button>',
                    '<span class="lead modal-title text-info">{{ title }}</span>',
                  '</div>',
                  '<div class="modal-body">',
                    '<div class="container-fluid">',
                      '<div class="row">',
                        '<div data-field-editor="\'path\'" data-label-size="" data-field-size="3" style="text-align: right" data-model-name="modelName" data-model="model"></div>',
                      '</div>',
                      '<br />',
                      '<div class="row">',
                        '<div data-ng-repeat="type in pathTypes" data-ng-show="getPathType() == type" data-advanced-editor-pane="" data-view-name="radiaService.pathTypeModel(type)" data-field-def="basic" data-want-buttons="false">',
                      '</div>',
                    '</div>',
                  '</div>',
                '</div>',
              '</div>',
            '</div>',
        ].join(''),
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
                $scope.pathTypes.forEach(function (t) {
                    var pt = radiaService.pathTypeModel(t);
                    $scope.$on(pt + '.changed', function () {
                        radiaService.addOrModifyPath(t);
                    });
                });

                let el = $('#sr-fieldpaths-editor');
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
                    var o = $($element).find('.modal').css('opacity');
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
        template: [
            '<div class="col-md-6">',
                '<div class="panel panel-info">',
                    '<div class="panel-heading">',
                        '<span class="sr-panel-heading">Field Integrals (T &#x00B7; mm)</span>',
                        '<div class="sr-panel-options pull-right">',
                        '<a data-ng-show="hasPaths()" data-ng-click="download()" target="_blank" title="Download"> <span class="sr-panel-heading glyphicon glyphicon-cloud-download" style="margin-bottom: 0"></span></a> ',
                        '</div>',
                    '</div>',
                    '<div class="panel-body">',
                        '<table data-ng-if="hasPaths()" style="width: 100%; table-layout: fixed; margin-bottom: 10px" class="table table-hover">',
                          '<colgroup>',
                            '<col style="width: 20ex">',
                            '<col>',
                            '<col>',
                          '</colgroup>',
                          '<thead>',
                            '<tr>',
                              '<th data-ng-repeat="h in HEADING">{{ h }}</th>',
                            '</tr>',
                          '</thead>',
                          '<tbody>',
                            '<tr data-ng-repeat="path in linePaths()">',
                              '<td>{{ path.name }}</td>',
                              '<td>[{{ path.begin }}] &#x2192; [{{ path.end }}]</td>',
                              '<td>',
                                '<div data-ng-repeat="t in INTEGRABLE_FIELD_TYPES"><span style="font-weight: bold">{{ t }}:</span> </span><span>{{ format(integrals[path.name][t]) }}</span></div>',
                              '</td>',
                            '</tr>',
                          '</tbody>',
                        '</table>',
                    '</div>',
                '</div>',
            '</div>',
        ].join(''),
        controller: function($scope) {

            $scope.CSV_HEADING = ['Line', 'x0', 'y0', 'z0', 'x1', 'y1', 'z1', 'Bx', 'By', 'Bz', 'Hx', 'Hy', 'Hz'];
            $scope.HEADING = ['Line', 'Endpoints', 'Fields'];
            $scope.INTEGRABLE_FIELD_TYPES = ['B', 'H'];
            $scope.integrals = {};

            $scope.download = function() {
                var fileName = panelState.fileNameFromText('Field Integrals', 'csv');
                var data = [$scope.CSV_HEADING];
                $scope.linePaths().forEach(function (p) {
                    var row = [];
                    var begin = radiaService.stringToFloatArray(p.begin);
                    var end = radiaService.stringToFloatArray(p.end);
                    row.push(
                        p.name,
                        begin[0], begin[1], begin[2],
                        end[0], end[1], end[2]
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

            $scope.hasPaths = function() {
                return $scope.linePaths().length;
            };

            $scope.format = function(vals) {
                if (! vals) {
                    return [];
                }
                return vals.map(function (v, i) {
                    return utilities.roundToPlaces(v, 4);
                });
            };

            $scope.isLine = function(p) {
                return p.type === 'line';
            };

            $scope.linePaths = function () {
                return (($scope.model || {}).paths || []).filter($scope.isLine);
            };
/*
            function updateTable() {
                requestSender.getApplicationData(
                    {
                        fieldPaths: $scope.linePaths(),
                        method: 'get_field_integrals',
                        simulationId: appState.models.simulation.simulationId,
                    },
                    function(d) {
                        $scope.integrals = d;
                    });
            }
*/
            function updateTable() {
                var inData = {
                    fieldPaths: $scope.linePaths(),
                    method: 'get_field_integrals',
                    simulationId: appState.models.simulation.simulationId,
                };
                radiaService.getRadiaData(inData, function(d) {
                    $scope.integrals = d;
                });
            }

            $scope.$on('fieldPaths.changed', function () {
                updateTable();
            });

           appState.whenModelsLoaded($scope, function() {
               $scope.model = appState.models[$scope.modelName];
               // wait until we have some data to update
               $scope.$on('radiaViewer.loaded', function () {
                    updateTable();
               });
            });

        },
    };
});

SIREPO.app.directive('fieldPathTable', function(appState, panelState, radiaService, utilities) {
    return {
        restrict: 'A',
        scope: {
            paths: '='
        },
        template: [
            '<table data-ng-if="hasPaths()" style="width: 100%; table-layout: fixed; margin-bottom: 10px" class="table table-hover">',
              '<colgroup>',
                '<col style="width: 20ex">',
                '<col style="width: 10ex">',
                '<col style="width: 10ex">',
                '<col style="width: 100%">',
                '<col style="width: 10ex">',
              '</colgroup>',
              '<thead>',
                '<tr>',
                  '<th>Name</th>',
                  '<th>Type</th>',
                  '<th>Num. points</th>',
                  '<th>Details</th>',
                  '<th></th>',
                '</tr>',
              '</thead>',
              '<tbody>',
                '<tr data-ng-repeat="path in paths track by $index">',
                  '<td><div class="badge sr-badge-icon sr-lattice-icon"><span>{{ path.name }}</span></div></td>',
                  '<td><span>{{ path.type }}</span></td>',
                  '<td><span>{{ path.numPoints }}</span></td>',
                  '<td><span>{{ pathDetails(path) }}</span></td>',
                  '<td style="text-align: right">',
                    '<div class="sr-button-bar-parent">',
                        '<div class="sr-button-bar" data-ng-class="sr-button-bar-active" >',
                            '<button class="btn btn-info btn-xs sr-hover-button" data-ng-click="copyPath(path)">Copy</button>',
                            ' <button data-ng-click="editPath(path)" class="btn btn-info btn-xs sr-hover-button">Edit</button>',
                            ' <button data-ng-click="svc.showFieldDownload(true, path)" class="btn btn-info btn-xs"><span class="glyphicon glyphicon-cloud-download"></span></button>',
                            ' <button data-ng-click="deletePath(path, $index)" class="btn btn-danger btn-xs"><span class="glyphicon glyphicon-remove"></span></button>',
                        '</div>',
                    '<div>',
                  '</td>',
                '</tr>',
              '</tbody>',
            '</table>',
        ].join(''),
        controller: function($scope) {
            const watchedModels = SIREPO.APP_SCHEMA.enum.PathType.map(function (e) {
                return e[SIREPO.ENUM_INDEX_VALUE];
            });

            $scope.svc = radiaService;

            $scope.hasPaths = function() {
                return $scope.paths && $scope.paths.length;
            };

            $scope.copyPath = function(path) {
                let copy = appState.clone(path);
                copy.name = newPathName(copy);
                copy.id = nextId();
                $scope.paths.push(copy);
                appState.saveChanges(['fieldPaths', radiaService.pathTypeModel(copy.type)], function () {
                    $scope.editPath(copy);
                });
            };

           $scope.deletePath = function(path, index) {
                $scope.paths.splice(index, 1);
                appState.saveChanges('fieldPaths');
           };

           $scope.editPath = function(path) {
               appState.models[radiaService.pathTypeModel(path.type)] = path;
               appState.models.fieldPaths.path = path.type;
               radiaService.showPathPicker(true, false);
           };

           $scope.pathDetails = function(path) {
               var res = '';
               var pt = radiaService.pathTypeModel(path.type);
               var info = appState.modelInfo(pt);
               var d = SIREPO.APP_SCHEMA.constants.detailFields.fieldPath[pt];
               d.forEach(function (f, i) {
                   var fi = info[f];
                   res += (fi[0] + ': ' + path[f] + (i < d.length - 1 ? '; ' : ''));
               });
               return res;
           };

           function newPathName(path) {
               return appState.uniqueName(appState.models.fieldPaths, 'name', path.name + ' {}');
           }

           function nextId() {
               return appState.maxId(appState.models.fieldPaths.paths, 'id');
           }

           appState.whenModelsLoaded($scope, function() {
               $scope.paths = appState.models.fieldPaths.paths;
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
        template: [
            '<table table-layout: fixed" class="table table-hover">',
                '<tr data-ng-show="field.length > 0">',
                  '<th>Members</th>',
                  '<th></th>',
                '</tr>',
                '<tr data-ng-repeat="mId in field">',
                    '<td style="padding-left: 1em"><div class="badge sr-badge-icon"><span data-ng-drag="true" data-ng-drag-data="element">{{ getObject(mId).name }}</span></div></td>',
                    '<td style="text-align: right">&nbsp;<div class="sr-button-bar-parent"><div class="sr-button-bar">  <button data-ng-click="removeObject(mId)" class="btn btn-danger btn-xs"><span class="glyphicon glyphicon-remove"></span></button></div><div></td>',
                '</tr>',
                '<tr>',
                  '<th>Ungrouped</th>',
                '</tr>',
                '<tr data-ng-repeat="oId in getIds() | filter:hasNoGroup">',
                  '<td style="padding-left: 1em"><div class="badge sr-badge-icon"><span data-ng-drag="true" data-ng-drag-data="element">{{ getObject(oId).name }}</span></div></td>',
                  '<td style="text-align: right">&nbsp;<div class="sr-button-bar-parent"><div class="sr-button-bar"><button class="btn btn-info btn-xs sr-hover-button" data-ng-click="addObject(oId)"><span class="glyphicon glyphicon-plus"></span></button> </div><div></td>',
                '</tr>',
            '</table>',
        ].join(''),
        controller: function($scope) {

            $scope.objects = appState.models.geometry.objects;
            if (! $scope.field) {
                $scope.field = [];
            }

            $scope.addObject = function(oId) {
                let o = $scope.getObject(oId);
                o.groupId = $scope.model.id;
                $scope.field.push(o.id);
            };

            $scope.getIds = function() {
                return $scope.objects.map(function (o) {
                    return o.id;
                });
            };

            $scope.getObject = function(oId) {
                return radiaService.getObject(oId);
            };

            $scope.hasNoGroup = function(oId) {
                if ($scope.field.indexOf(oId) >= 0) {
                    return false;
                }
                let o = $scope.getObject(oId);
                return oId !== $scope.model.id && (! o.groupId || o.groupId === '');
            };

            $scope.removeObject = function(oId) {
                let o = $scope.getObject(oId);
                o.groupId = '';
                var oIdx = $scope.field.indexOf(oId);
                if (oIdx < 0) {
                    return;
                }
                $scope.field.splice(oIdx, 1);
            };
        },
    };
});

SIREPO.app.directive('numberList', function() {
    return {
        restrict: 'A',
        scope: {
            field: '=',
            model: '=',
            info: '<',
            type: '@',
            count: '@',
        },
        template: [
            '<div data-ng-repeat="defaultSelection in parseValues() track by $index" style="display: inline-block" >',
                '<label style="margin-right: 1ex">{{ valueLabels[$index] || \'Plane \' + $index }}</label>',
                '<input class="form-control sr-list-value" data-string-to-number="{{ numberType }}" data-ng-model="values[$index]" data-min="min" data-max="max" data-ng-change="didChange()" class="form-control" style="text-align: right" required />',
            '</div>'
        ].join(''),
        controller: function($scope, $element) {

            let lastModel = null;
            // NOTE: does not appear to like 'model.field' format
            $scope.values = null;
            $scope.numberType = $scope.type.toLowerCase();
            $scope.min = $scope.numberType === 'int' ? Number.MIN_SAFE_INTEGER : -Number.MAX_VALUE;
            $scope.max = $scope.numberType === 'int' ? Number.MAX_SAFE_INTEGER : Number.MAX_VALUE;
            $scope.valueLabels = ($scope.info[4] || '').split(/\s*,\s*/);
            $scope.didChange = function() {
                $scope.field = $scope.values.join(', ');
            };
            $scope.parseValues = function() {
                // values were sticking around when the model changed
                if (! lastModel || lastModel !== $scope.model) {
                    lastModel = $scope.model;
                    $scope.values = null;
                }
                if ($scope.field && ! $scope.values) {
                    $scope.values = $scope.field.split(/\s*,\s*/);
                }
                return $scope.values;
            };
        },
    };
});

// this kind of thing should be generic
SIREPO.app.directive('transformTable', function(appState, panelState, radiaService) {
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
        template: [
            '<div data-toolbar="toolbarSections" data-item-filter="itemFilter" data-parent-controller="parentController"></div>',
            '<div class="sr-object-table">',
              '<p class="lead text-center"><small><em>drag and drop {{ itemClass.toLowerCase() }}s or use arrows to reorder the list</em></small></p>',
              '<table class="table table-hover" style="width: 100%; table-layout: fixed">',
                '<tr data-ng-repeat="item in loadItems()">',
                  '<td data-ng-drop="true" data-ng-drop-success="dropItem($index, $data)" data-ng-drag-start="selectItem($data)">',
                    '<div class="sr-button-bar-parent pull-right"><div class="sr-button-bar"><button class="btn btn-info btn-xs"  data-ng-disabled="$index == 0" data-ng-click="moveItem(-1, item)"><span class="glyphicon glyphicon-arrow-up"></span></button> <button class="btn btn-info btn-xs" data-ng-disabled="$index == items.length - 1" data-ng-click="moveItem(1, item)"><span class="glyphicon glyphicon-arrow-down"></span></button> <button class="btn btn-info btn-xs sr-hover-button" data-ng-click="editItem(item)">Edit</button> <button data-ng-click="toggleExpand(item)" class="btn btn-info btn-xs"><span class="glyphicon" data-ng-class="{\'glyphicon-chevron-up\': isExpanded(item), \'glyphicon-chevron-down\': ! isExpanded(item)}"></span></button> <button data-ng-click="deleteItem(item)" class="btn btn-danger btn-xs"><span class="glyphicon glyphicon-remove"></span></button></div></div>',
                    '<div class="sr-command-icon-holder" data-ng-drag="true" data-ng-drag-data="item">',
                      '<a style="cursor: move; -moz-user-select: none; font-size: 14px" class="badge sr-badge-icon" data-ng-class="{\'sr-item-selected\': isSelected(item) }" href data-ng-click="selectItem(item)" data-ng-dblclick="editItem(item)">{{ itemName(item) }}</a>',
                    '</div>',
                    '<div data-ng-show="! isExpanded(item) && itemDetails(item)" style="margin-left: 3em; margin-right: 1em; color: #777; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{{ itemDetails(item) }}</div>',
                    '<div data-ng-show="isExpanded(item) && itemDetails(item)" style="color: #777; margin-left: 3em; white-space: pre-wrap">{{ itemDetails(item) }}</div>',
                  '</td>',
                '</tr>',
                '<tr><td style="height: 3em" data-ng-drop="true" data-ng-drop-success="dropLast($data)"> </td></tr>',
              '</table>',
            '</div>',
            //'<div data-advanced-editor-pane="" data-view-name="tbItem.model" data-parent-controller="parentController" data-ng-repeat="tbItem in toolbarItems" data-ng-show="selectedItem.model === tbItem.model"></div>',
            //'<div data-confirmation-modal="" data-id="sr-delete-item-confirmation" data-title="Delete {{ itemClass }}?" data-ok-text="Delete" data-ok-clicked="deleteSelected()">Delete command &quot;{{ selectedItemName() }}&quot;?</div>',
        ].join(''),
        controller: function($scope, $element) {
            var expanded = {};
            var isEditing = false;
            var spatialTransforms = [
                'rotate',
                'translate'
            ];
            var watchedModels;

            $scope.items = [];
            $scope.radiaService = radiaService;
            $scope.selectedItem = null;
            $scope.toolbarItems = [];
            $scope.toolbarSections = SIREPO.APP_SCHEMA.constants.toolbarItems.filter(function (section) {
                return $scope.modelName === 'cloneTransform' ?
                    section.name === 'Transforms (clone)' :
                    section.name === 'Transforms';
            });

            $scope.toolbarSections.forEach(function (s) {
                s.contents.forEach(function (c) {
                    $scope.toolbarItems.push(c);
                });
            });

            watchedModels = $scope.toolbarItems.map(function (item) {
                return item.model;
            });

            function itemIndex(data) {
                return $scope.items.indexOf(data);
            }

            $scope.addItem = function(item) {
                $scope.editItem(item, true);
            };

            $scope.deleteItem = function(item) {
                var index = itemIndex(item);
                if (index < 0) {
                    return;
                }
                $scope.field.splice(index, 1);
                appState.saveChanges('geometry');
            };

            $scope.editItem = function(item, isNew) {
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

            $scope.dropItem = function(index, data) {
                if (! data) {
                    return;
                }
                var i = $scope.items.indexOf(data);
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

            $scope.dropLast = function(item) {
                if (! item) {
                    return;
                }
                $scope.addItem(item);
            };

            $scope.getSelected = function() {
                return $scope.selectedItem;
            };

            $scope.itemDetails = function(item) {
                var res = '';
                var info = appState.modelInfo(item.model);
                var d = SIREPO.APP_SCHEMA.constants.detailFields[$scope.fieldName][item.model];
                d.forEach(function (f, i) {
                    var fi = info[f];
                    var val = angular.isArray(item[f]) ? '[' + item[f].length + ']' : item[f];
                    res += (fi[0] + ': ' + val + (i < d.length - 1 ? '; ' : ''));
                });
                return res;
            };

            $scope.isExpanded = function(item) {
                return expanded[itemIndex(item)];
            };

            $scope.loadItems = function() {
                $scope.items = $scope.field;
                return $scope.items;
            };

            $scope.moveItem = function(direction, item) {
                var d = direction == 0 ? 0 : (direction > 0 ? 1 : -1);
                var currentIndex = itemIndex(item);
                var newIndex = currentIndex + d;
                if (newIndex >= 0 && newIndex < $scope.items.length) {
                    var tmp = $scope.items[newIndex];
                    $scope.items[newIndex] = item;
                    $scope.items[currentIndex] = tmp;
                }
            };

            $scope.toggleExpand = function(item) {
                expanded[itemIndex(item)] = ! expanded[itemIndex(item)];
            };

            $scope.itemFilter = function(item) {
                var iIdx = -1;
                for (var sIdx in $scope.toolbarSections) {
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
                    return spatialTransforms.indexOf(item.type) >= 0;
                }
                return true;
            };

            appState.whenModelsLoaded($scope, function() {

                $scope.$on('modelChanged', function(e, modelName) {
                    if (watchedModels.indexOf(modelName) < 0) {
                        return;
                    }
                    $scope.selectedItem = null;
                    if (! isEditing) {
                        appState.models[modelName].id = nextId();
                        $scope.field.push(appState.models[modelName]);
                        isEditing = true;
                    }
                    appState.saveChanges('geometry', function () {
                        $scope.loadItems();
                    });
                });

                $scope.$on('cancelChanges', function(e, name) {
                    $scope.$emit('drop.target.enabled', true);
                    if (watchedModels.indexOf(name) < 0) {
                        return;
                    }
                    appState.removeModel(name);
                });

                $scope.$on('$destroy', function () {
                    $scope.$emit('drop.target.enabled', true);
                });

                $scope.$watch($scope.modelName, function () {
                    //srdbg('watch saw', $scope.modelName);
                });

                $scope.$watch('items', function () {
                    //srdbg('watch saw', $scope.items);
                });

                $scope.loadItems();
            });

            function nextId() {
                return appState.maxId($scope.field, 'id') + 1;
            }

            $scope.$emit('drop.target.enabled', false);
        },
    };
});

SIREPO.app.directive('radiaFieldPaths', function(appState, panelState, radiaService) {

    return {
        restrict: 'A',
        scope: {
            modelName: '@',
        },
        template: [
            '<div class="col-md-6">',
                '<div class="panel panel-info">',
                    '<div class="panel-heading"><span class="sr-panel-heading">Field Paths</span></div>',
                    '<div class="panel-body">',
                        '<button class="btn btn-info btn-xs pull-right" accesskey="p" data-ng-click="radiaService.newPath()"><span class="glyphicon glyphicon-plus"></span> New <u>P</u>ath</button>',
                        '<div data-field-path-table="" data-paths="model.paths"></div>',
                        '<button class="btn btn-default col-sm-2 col-sm-offset-5" data-ng-show="hasPaths()" data-ng-click="confirmClear()">Clear</button>',
                    '</div>',
                '</div>',
            '</div>',
            //'<div data-confirmation-modal="" data-id="sr-delete-path-confirmation" data-title="Delete Path?" data-ok-text="Delete" data-ok-clicked="deleteSelected()">Delete command &quot;{{ selectedItemName() }}&quot;?</div>',
            '<div data-confirmation-modal="" data-id="sr-clear-paths-confirmation" data-title="Clear All Paths?" data-ok-text="OK" data-ok-clicked="clearPaths()">Clear All Paths?</div>',

        ].join(''),
        controller: function($scope, $element) {
            $scope.modelsLoaded = false;
            $scope.pathTypes = appState.enumVals('PathType');
            $scope.radiaService = radiaService;

            $scope.getPathType = function() {
                return ($scope.model || {}).path;
            };

            $scope.clearPaths = function() {
                $scope.model.paths = [];
                appState.saveChanges($scope.modelName);
            };

            $scope.confirmClear = function() {
                $('#sr-clear-paths-confirmation').modal('show');
            };

            $scope.hasPaths = function() {
                if (! $scope.modelsLoaded) {
                    return false;
                }
                return $scope.model.paths && $scope.model.paths.length;
            };

            appState.whenModelsLoaded($scope, function () {
                $scope.model = appState.models[$scope.modelName];
                $scope.modelsLoaded = true;
            });
        },
    };
});

SIREPO.app.directive('radiaGeomObjInfo', function(appState, panelState, radiaService) {

    return {
        restrict: 'A',
        scope: {
            model: '=',
        },
        template: [
            '<div class="col-md-6">',
                '<div data-label-with-tooltip="" class="control-label" data-ng-class="labelClass" data-label="{{ model.name }}" data-tooltip=""></div>',
                '<div data-field-editor="\'color\'" data-model-name="geomObject" data-model="model"></div>',
            '</div>',
        ].join(''),
        controller: function($scope, $element) {
            $scope.radiaService = radiaService;
            appState.whenModelsLoaded($scope, function () {
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
        template: [
            '<div class="col-md-6">',
                '<div data-basic-editor-panel="" data-view-name="solver">',
                        '<div data-sim-status-panel="viz.simState"></div>',
                        '<div data-ng-show="viz.solution">',
                                '<div><strong>Time:</strong> {{ solution().time }}ms</div>',
                                '<div><strong>Step Count:</strong> {{ solution().steps }}</div>',
                                '<div><strong>Max |M|: </strong> {{ solution().maxM }} A/m</div>',
                                '<div><strong>Max |H|: </strong> {{ solution().maxH }} A/m</div>',
                        '</div>',
                        '<div data-ng-hide="viz.solution">No solution found</div>',
                        '<div class="col-sm-6 pull-right" style="padding-top: 8px;">',
                            '<button class="btn btn-default" data-ng-click="reset()">Reset</button>',
                        '</div>',
                    '</div>',
                '</div>',
            '</div>',

        ].join(''),
        controller: function($scope, $element) {

            $scope.model = appState.models[$scope.modelName];

            $scope.solution = function() {
                var s = $scope.viz.solution;
                return {
                    time: s ? utilities.roundToPlaces(1000 * s.time, 3) : '',
                    steps: s ? s.steps : '',
                    maxM: s ? utilities.roundToPlaces(s.maxM, 4) : '',
                    maxH: s ?  utilities.roundToPlaces(s.maxH, 4) : '',
                };
            };

            $scope.reset = function() {
                $scope.viz.solution = null;
                panelState.clear('geometry');
                panelState.requestData('reset', function (d) {
                    frameCache.setFrameCount(0);
                }, true);
            };

            appState.whenModelsLoaded($scope, function () {
            });


        },
    };
});

SIREPO.app.directive('radiaViewer', function(appState, errorService, frameCache, geometry, layoutService, panelState, plotting, plotToPNG, radiaService, radiaVtkUtils, requestSender, utilities, vtkPlotting, vtkUtils, $interval, $rootScope) {

    return {
        restrict: 'A',
        scope: {
            modelName: '@',
            viz: '<',
        },
        template: [
            '<div class="col-md-6">',
                '<div class="row" data-basic-editor-panel="" data-view-name="{{ modelName }}">',
                    '<div data-vtk-display="" class="vtk-display" data-ng-class="{\'col-sm-11\': isViewTypeFields()}" style="padding-right: 0" data-show-border="true" data-model-name="{{ modelName }}" data-event-handlers="eventHandlers" data-enable-axes="true" data-axis-cfg="axisCfg" data-axis-obj="axisObj" data-enable-selection="true"></div>',
                    //'<div data-vtk-axes="" data-width="canvasGeometry().size.width" data-height="canvasGeometry().size.height" data-bound-obj="beamAxisObj" data-axis-cfg="beamAxisCfg"></div>',
                    '<div class="col-sm-1" style="padding-left: 0" data-ng-if="isViewTypeFields()">',
                        '<div class="colorbar"></div>',
                    '</div>',
                '</div>',
            '</div>',

        ].join(''),
        controller: function($scope, $element) {

            $scope.axisObj = null;
            $scope.defaultColor = "#ff0000";
            $scope.gModel = null;
            $scope.mode = null;

            $scope.isViewTypeFields = function () {
                return (appState.models.magnetDisplay || {}).viewType === SIREPO.APP_SCHEMA.constants.viewTypeFields;
            };

            $scope.isViewTypeObjects = function () {
                return (appState.models.magnetDisplay || {}).viewType === SIREPO.APP_SCHEMA.constants.viewTypeObjects;
            };

            var LINEAR_SCALE_ARRAY = 'linear';
            var LOG_SCALE_ARRAY = 'log';
            var ORIENTATION_ARRAY = 'orientation';
            var FIELD_ATTR_ARRAYS = [LINEAR_SCALE_ARRAY, LOG_SCALE_ARRAY, ORIENTATION_ARRAY];

            var PICKABLE_TYPES = [
                SIREPO.APP_SCHEMA.constants.geomTypePolys,
                SIREPO.APP_SCHEMA.constants.geomTypeVectors
            ];

            var SCALAR_ARRAY = 'scalars';

            var actorInfo = {};
            var alphaDelegate = null;
            var beamAxis = [[-1, 0, 0], [1, 0, 0]];
            var cm = vtkPlotting.coordMapper();
            var colorbar = null;
            var colorbarPtr = null;
            var colorScale = null;
            var cPicker = null;
            var displayFields = [
                 'magnetDisplay.pathType',
                 'magnetDisplay.viewType',
                 'magnetDisplay.fieldType',
            ];
            var fieldDisplayModelFields = {
                'fieldDisplay': ['colorMap', 'scaling'],
            };
            var fieldDisplayFields = fieldDisplayModelFields.fieldDisplay.map(function (f) {
                return 'fieldDisplay.' + f;
            });

            var initDone = false;
            var ptPicker = null;
            var renderer = null;
            var renderWindow = null;
            var selectedColor = [];
            var selectedInfo = null;
            var selectedObj = null;
            var selectedOutline = null;
            var selectedPointId = -1;
            var sceneData = {};

            // these objects are used to set various vector properties
            var vectInArrays = [{
                location: vtk.Common.DataModel.vtkDataSet.FieldDataTypes.COORDINATE,
            }];

            var vectOutArrays = [{
                    location: vtk.Common.DataModel.vtkDataSet.FieldDataTypes.POINT,
                    name: SCALAR_ARRAY,
                    dataType: 'Uint8Array',
                    attribute: vtk.Common.DataModel.vtkDataSetAttributes.AttributeTypes.SCALARS,
                    numberOfComponents: 3,
                },
            ];
            var vectArrays = {
                input: vectInArrays,
                output: vectOutArrays,
            };

            var vtkAPI = {};
            var vtkSelection = {};

            var watchFields = displayFields.concat(fieldDisplayFields);

            FIELD_ATTR_ARRAYS.forEach(function (n) {
                vectOutArrays.push({
                    location: vtk.Common.DataModel.vtkDataSet.FieldDataTypes.POINT,
                    name: n,
                    dataType: 'Float32Array',
                    numberOfComponents: 3,
                });
            });

            // stash the actor and associated info to avoid recalculation
            function addActor(id, group, actor, geomType, pickable) {
                //srdbg('addActor', 'id', id, 'grp', group, 'geomType', type, 'pick', pickable);
                var pData = actor.getMapper().getInputData();
                var info = {
                    actor: actor,
                    colorIndices: [],
                    group: group || 0,
                    id: id,
                    pData: pData,
                    scalars: pData.getCellData().getScalars(),
                    type: geomType,
                };

                if (info.scalars) {
                    info.colorIndices = utilities.indexArray(numColors(pData, geomType))
                        .map(function (i) {
                            return 4 * i;
                        });
                }
                actorInfo[id] = info;

                vtkPlotting.addActor(renderer, actor);
                if (pickable) {
                    ptPicker.addPickList(actor);
                    //cPicker.addPickList(actor);
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
                //srdbg('buildScene', sceneData);
                // scene -> multiple data -> multiple actors
                var name = sceneData.name;
                var data = sceneData.data;

                vtkPlotting.removeActors(renderer);
                var didModifyGeom = false;
                for (var i = 0; i < data.length; ++i) {

                    // ***NEED BETTER ID, KNOWN ON BOTH SIDES***
                    var gname = name + '.' + i;
                    var sceneDatum = data[i];

                    // trying a separation into an actor for each data type, to better facilitate selection
                    for (var j = 0; j < radiaVtkUtils.GEOM_TYPES.length; ++j) {
                        var t = radiaVtkUtils.GEOM_TYPES[j];
                        var id = gname + '.' + t;
                        var d = sceneDatum[t];
                        if (! d || ! d.vertices || ! d.vertices.length) {
                            continue;
                        }
                        var isPoly = t === SIREPO.APP_SCHEMA.constants.geomTypePolys;
                        //var gObj = radiaService.getObject(id) || {};
                        var gObj = radiaService.getObject(i) || {};
                        //srdbg('gobj', gObj);
                        var gColor = gObj.color ? vtk.Common.Core.vtkMath.hex2float(gObj.color) : null;
                        // use colors from Radia for groups
                        if (gObj.members) {
                            gColor = null;
                        }
                        var pdti = radiaVtkUtils.objToPolyData(sceneDatum, [t], gColor);
                        var pData = pdti.data;
                        var bundle;
                        if (radiaVtkUtils.GEOM_OBJ_TYPES.indexOf(t) >= 0) {
                            bundle = cm.buildActorBundle();
                            bundle.mapper.setInputData(pData);
                        }
                        else {
                            var vectorCalc = vtk.Filters.General.vtkCalculator.newInstance();
                            vectorCalc.setFormula(getVectFormula(d, appState.models.fieldDisplay.colorMap));
                            vectorCalc.setInputData(pData);

                            var mapper = vtk.Rendering.Core.vtkGlyph3DMapper.newInstance();
                            mapper.setInputConnection(vectorCalc.getOutputPort(), 0);

                            var s = vtk.Filters.Sources.vtkArrowSource.newInstance();
                            mapper.setInputConnection(s.getOutputPort(), 1);
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
                        var info = addActor(id, gname, bundle.actor, t, PICKABLE_TYPES.indexOf(t) >= 0);
                        gColor = getColor(info);
                        if (isPoly && $.isEmptyObject(gObj)) {
                            //srdbg('add poly obj', gObj);
                            gObj = appState.setModelDefaults(gObj, 'radiaObject');
                            gObj.name = id;
                            gObj.id = id;
                            if (gColor) {
                                // **IF GROUP COLOR USE IF NOT USE OBJECT COLOR**
                                gObj.color = vtk.Common.Core.vtkMath.floatRGB2HexCode(vtkUtils.rgbToFloat(gColor));
                            }
                            // temporary handling of examples until they are "buildaable"
                            // ***KEEPS ADDING OVER AND OVER***
                            if (appState.models.simulation.isExample || appState.models.simulation.dmpImportFile) {
                                if (! appState.models.geometry.objects) {
                                    appState.models.geometry.objects = [];
                                }
                                appState.models.geometry.objects.push(gObj);
                            }

                            didModifyGeom = true;
                        }
                        if (! gObj.center || ! gObj.size) {
                            var b = bundle.actor.getBounds();
                            gObj.center = [0.5 * (b[1] + b[0]), 0.5 * (b[3] + b[2]), 0.5 * (b[5] + b[4])].join(',');
                            gObj.size = [Math.abs(b[1] - b[0]), Math.abs(b[3] - b[2]), Math.abs(b[5] - b[4])].join(',');
                            didModifyGeom = true;
                        }
                        if (
                            t === SIREPO.APP_SCHEMA.constants.geomTypeLines &&
                            appState.models.magnetDisplay.viewType == SIREPO.APP_SCHEMA.constants.viewTypeFields
                        ) {
                            setEdgeColor(info, [216, 216, 216]);
                        }
                    }
                }

                var pb = renderer.computeVisiblePropBounds();
                radiaService.objBounds = pb;
                //srdbg('bnds', b);
                //srdbg('l', [Math.abs(b[1] - b[0]), Math.abs(b[3] - b[2]), Math.abs(b[5] - b[4])]);
                //srdbg('ctr', [(b[1] + b[0]) / 2, (b[3] + b[2]) / 2, (b[5] + b[4]) / 2]);

                var padPct = 0.1;
                var l = [
                    Math.abs(pb[1] - pb[0]),
                    Math.abs(pb[3] - pb[2]),
                    Math.abs(pb[5] - pb[4])
                ].map(function (c) {
                    return (1 + padPct) * c;
                });

                var bndBox = cm.buildBox(l, [(pb[1] + pb[0]) / 2, (pb[3] + pb[2]) / 2, (pb[5] + pb[4]) / 2]);
                bndBox.actor.getProperty().setRepresentationToWireframe();
                // NOTE: vtkLineFilter exists but is not included in the default vtk build
                //var lf = vtk.Filters.General.vtkLineFilter.newInstance();

                renderer.addActor(bndBox.actor);
                var vpb = vtkPlotting.vpBox(bndBox.source, renderer);
                renderWindow.render();
                vpb.defaultCfg.edgeCfg.z.sense = -1;
                vpb.initializeWorld(
                    {
                        edgeCfg: {
                            x: {sense: 1},
                            y: {sense: 1},
                            z: {sense: -1},
                        }
                    });
                $scope.axisObj = vpb;

                var acfg = {};
                geometry.basis.forEach(function (dim, i) {
                    acfg[dim] = {};
                    acfg[dim].dimLabel = dim;
                    acfg[dim].label = dim + ' [mm]';
                    acfg[dim].max = pb[2 * i + 1];
                    acfg[dim].min = pb[2 * i];
                    acfg[dim].numPoints = 2;
                    acfg[dim].screenDim = dim === 'z' ? 'y' : 'x';
                    acfg[dim].showCentral = dim === appState.models.simulation.beamAxis;
                });
                $scope.axisCfg = acfg;

                // visual rep of paths?
                /*
                appState.models.fieldPaths.paths.forEach(function (p) {
                    if (p.type == 'line') {
                        var s = vtk.Filters.Sources.vtkLineSource.newInstance({
                            point1: [p.beginX, p.beginY, p.beginZ],
                            point2: [p.endX, p.endY, p.endZ],
                            resolution: 2,
                        });
                        var b = cm.buildFromSource(s);
                        b.actor.getProperty().setColor(255, 0, 0);
                        renderer.addActor(b.actor);
                    }
                });
                */

                if (didModifyGeom) {
                    appState.saveQuietly('geometry');
                }
                updateLayout();
                setAlpha();
                setBGColor();
                vtkAPI.setCam();
                enableWatchFields(true);
            }

            function enableWatchFields(doEnable) {
                watchFields.forEach(function (wf) {
                    var mf = appState.parseModelField(wf);
                    panelState.enableField(mf[0], mf[1], doEnable);
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
                    .filter(function (id) {
                        return getActorInfo(id).type === typeName;
                    })
                    .map(function (id) {
                        return getActorInfo(id);
                    });
            }

            function getActorsOfType(typeName) {
                return getActorInfoOfType(typeName).map(function (info) {
                    return info.actor;
                });
            }

            function getColor(info) {
                var s = info.scalars;
                if (! s) {
                    return null;
                }
                var inds = info.colorIndices;
                if (! inds) {
                    return null;
                }
                return s.getData().slice(inds[0], inds[0] + 3);
            }

            function getGeomObj(id) {
                var gObjs = appState.models.geometry.objects || [];
                for (var i = 0; i < gObjs.length; ++i) {
                    if (gObjs[i].id === id) {
                        return gObjs[i];
                    }
                }
                return null;
            }

            function getInfoForActor(actor) {
                for (var n in actorInfo) {
                    if (getActor(n) === actor) {
                        return getActorInfo(n);
                    }
                }
            }

            // used to create array of arrows (or other objects) for vector fields
            // change to use magnitudes and color locally
            function getVectFormula(vectors, colorMapName) {

                //srdbg('getVectFormula', colorMapName);
                var cmap = plotting.colorMapOrDefault(
                    colorMapName,
                    appState.fieldProperties('fieldDisplay', 'colorMap').default
                );
                //srdbg('v', vectors);
                //srdbg('cm', cmap);
                var norms = utilities.normalize(vectors.magnitudes);
                var logMags = vectors.magnitudes.map(function (n) {
                    return Math.log(n);
                });

                // get log values back into the original range, so that the extremes have the same
                // size as a linear scale
                var minLogMag = Math.min.apply(null, logMags);
                var maxLogMag = Math.max.apply(null, logMags);
                var minMag = Math.min.apply(null, vectors.magnitudes);
                var maxMag = Math.max.apply(null, vectors.magnitudes);
                colorScale = plotting.colorScale(minMag, maxMag, cmap);

                logMags = logMags.map(function (n) {
                    return minMag + (n - minLogMag) * (maxMag - minMag) / (maxLogMag - minLogMag);
                });

                return {
                    getArrays: function(inputDataSets) {
                        return vectArrays;
                    },
                    evaluate: function (arraysIn, arraysOut) {
                        var coords = arraysIn.map(function (d) {
                            return d.getData();
                        })[0];
                        var o = arraysOut.map(function (d) {
                            return d.getData();
                        });
                        // note these arrays already have the correct length, so we need to set elements, not append
                        var orientation = o[getVectOutIndex(ORIENTATION_ARRAY)];
                        var linScale = o[getVectOutIndex(LINEAR_SCALE_ARRAY)].fill(1.0);
                        var logScale = o[getVectOutIndex(LOG_SCALE_ARRAY)].fill(1.0);
                        var scalars = o[getVectOutIndex(SCALAR_ARRAY)];

                        for (var i = 0; i < coords.length / 3; i += 1) {
                            var c = [0, 0, 0];
                            if (cmap.length) {
                                var rgb = d3.rgb(colorScale(norms[i]));
                                c = [rgb.r, rgb.g, rgb.b];
                            }
                            // scale arrow length (object-local x-direction) only
                            // this can stretch/squish the arrowhead though so the actor may have to adjust the ratio
                            linScale[3 * i] = vectors.magnitudes[i];
                            logScale[3 * i] = logMags[i];
                            for (var j = 0; j < 3; ++j) {
                                var k = 3 * i + j;
                                orientation[k] = vectors.directions[k];
                                scalars[k] = c[j];
                            }
                        }

                        // Mark the output vtkDataArray as modified
                        arraysOut.forEach(function (x) {
                            x.modified();
                        });
                    },
                };
            }

            function getVectOutIndex(name) {
                for (var vIdx in vectArrays.output) {
                    if (vectArrays.output[vIdx].name === name) {
                        return vIdx;
                    }
                }
                throw new Error('No vector array named ' + name  + ': ' + vectArrays.output);
            }

            function getVectorInfo(point, vect, units) {
                var pt = [];
                point.forEach(function (c) {
                    pt.push(utilities.roundToPlaces(c, 2));
                });
                var val = Math.hypot(vect[0], vect[1], vect[2]);
                var theta = 180 * Math.acos(vect[2] / (val || 1)) / Math.PI;
                var phi = 180 * Math.atan2(vect[1], vect[0]) / Math.PI;
                return isNaN(val) ?
                    '--' :
                    utilities.roundToPlaces(val, 4) + units +
                    '  θ ' + utilities.roundToPlaces(theta, 2) +
                    '°  φ ' + utilities.roundToPlaces(phi, 2) +
                    '°  at (' + pt + ')';
            }

            function handlePick(callData) {
                //srdbg('handle', callData);
                if (renderer !== callData.pokedRenderer) {
                    return;
                }

                // regular clicks are generated when spinning the scene - we'll select/deselect with ctrl-click
                var iMode = vtkAPI.getMode();
                if (iMode === vtkUtils.INTERACTION_MODE_MOVE ||
                    (iMode === vtkUtils.INTERACTION_MODE_SELECT && ! callData.controlKey)
                ) {
                    return;
                }

                var pos = callData.position;
                var point = [pos.x, pos.y, 0.0];
                ptPicker.pick(point, renderer);
                cPicker.pick(point, renderer);
                var pid = ptPicker.getPointId();

                // cell id is "closest cell within tolerance", meaning a single value, though
                // we may get multiple actors
                var cid = cPicker.getCellId();
                //srdbg('Picked pt', point);
                //srdbg('Picked pid', pid);
                //srdbg('Picked cid', cid);

                var picker;
                if (appState.models.magnetDisplay.viewType === SIREPO.APP_SCHEMA.constants.viewTypeObjects && cid >= 0) {
                    picker = cPicker;
                }
                else if (appState.models.magnetDisplay.viewType === SIREPO.APP_SCHEMA.constants.viewTypeFields && pid >= 0) {
                    picker = ptPicker;
                }
                if (! picker) {
                    //srdbg('Pick failed');
                    return;
                }

                var pas = picker.getActors();
                //var posArr = view.cPicker.getPickedPositions();
                //srdbg('pas', pas, 'positions', posArr);

                var selectedValue = Number.NaN;
                var highlightVectColor = [255, 0, 0];
                // it seems the 1st actor in the array is the closest to the viewer
                var actor = pas[0];
                vtkSelection = {};
                //var pos = posArr[aIdx];
                var info = getInfoForActor(actor);
                selectedInfo = info;
                //srdbg('actor', actor, 'info', info);
                if (! info || ! info.pData) {
                    return;
                }

                var pts = info.pData.getPoints();

                // TODO(mvk): attach pick functions to actor info?
                // vectors
                if (info.type === SIREPO.APP_SCHEMA.constants.geomTypeVectors) {
                    var n = pts.getNumberOfComponents();
                    var coords = pts.getData().slice(n * pid, n * (pid + 1));
                    var f = actor.getMapper().getInputConnection(0).filter;
                    var linArr = f.getOutputData().getPointData().getArrayByName(LINEAR_SCALE_ARRAY);
                    if (! linArr) {
                        return;
                    }
                    selectedValue = linArr.getData()[pid * linArr.getNumberOfComponents()];

                    var oArr = f.getOutputData().getPointData().getArrayByName(ORIENTATION_ARRAY);
                    var oid = pid * oArr.getNumberOfComponents();
                    var o = oArr.getData().slice(oid, oid + oArr.getNumberOfComponents());
                    var v = o.map(function (dir) {
                        return selectedValue * dir;
                    });

                    var sArr = f.getOutputData().getPointData().getArrayByName(SCALAR_ARRAY);
                    var ns = sArr.getNumberOfComponents();
                    var sid = pid * ns;
                    var sc = sArr.getData().slice(sid, sid + ns);

                    //srdbg('SEL C', sc, selectedColor, 'AT', sid);
                    //srdbg('SET OLD V COLOR');
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
                        //srdbg('SET NEW V COLOR', pid);
                        //srdbg(sArr.getData().slice(sid, sid + 3), '->', highlightVectColor);
                        highlightVectColor.forEach(function (c, i) {
                            sArr.getData()[sid + i] = c;
                        });
                        selectedPointId = pid;
                        selectedColor = sc;
                    }
                    info.pData.modified();

                    //srdbg(info.id, 'coords', coords, 'mag', selectedValue, 'orientation', o, 'color', sc);
                    vtkSelection = {
                        info: getVectorInfo(point, v, sceneData.data[0].vectors.units),
                    };
                    colorbarPtr.pointTo(selectedValue);
                }

                // objects
                else if (info.type === SIREPO.APP_SCHEMA.constants.geomTypePolys) {
                    var j = info.colorIndices[cid];
                    selectedColor = info.scalars.getData().slice(j, j + 3);  // 4 to get alpha
                   //srdbg(info.name, 'poly tup', cid, selectedColor);

                    var g = getGeomObj(info.id);
                    //srdbg(info.id, 'selected', g);
                    if (selectedObj === g) {
                        selectedObj = null;
                    }
                    else {
                        selectedObj = g;
                        selectedOutline = vtk.Filters.General.vtkOutlineFilter.newInstance();
                    }
                    var highlight = selectedColor.map(function (c) {
                        return 255 - c;
                    });

                    for (var id in actorInfo) {
                        setEdgeColor(
                            getActorInfo(id),
                            selectedObj && sharesGroup(getActor(id), actor) ? highlight : [0, 0, 0]
                        );
                    }

                    vtkSelection = {
                        info: selectedObj ? selectedObj.name : '--',
                        model: selectedObj ? {
                            getData: function () {
                                return selectedObj;
                            },
                            // just color etc here?
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
                //srdbg('init...');
                $scope.$broadcast('sliderParent.ready', appState.models.geometry);
                if (! renderer) {
                    throw new Error('No renderer!');
                }

                var t = 30;
                colorbar = Colorbar()
                    .margin({top: 5, right: t + 10, bottom: 0, left: 0})
                    .thickness(t)
                    .orient('vertical')
                    .barlength($('.vtk-canvas-holder').height())
                    .origin([0, 0]);

                var ca = vtk.Rendering.Core.vtkAnnotatedCubeActor.newInstance();
                vtk.Rendering.Core.vtkAnnotatedCubeActor.Presets.applyPreset('default', ca);
                var df = ca.getDefaultStyle();
                df.fontFamily = 'Arial';
                df.faceRotation = 45;
                ca.setDefaultStyle(df);

                var m = vtk.Interaction.Widgets.vtkOrientationMarkerWidget.newInstance({
                    actor: ca,
                    interactor: renderWindow.getInteractor()
                });
                m.setViewportCorner(
                    vtk.Interaction.Widgets.vtkOrientationMarkerWidget.Corners.TOP_RIGHT
                );
                m.setViewportSize(0.07);
                m.computeViewport();
                m.setMinPixelSize(50);
                m.setMaxPixelSize(100);
                vtkAPI.setMarker(m);
                updateViewer();
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
                var i = 0;
                var j = 0;
                while (i < data.length) {
                    i += (data[i] + 1);
                    ++j;
                }
                return j;
            }

            // some weird disconnect between the model and the slider when cancelling...???
            function setAlpha() {
                if (! renderer) {
                    return;
                }
                var alpha = $scope.gModel.alpha;
                for (var id in actorInfo) {
                    var info = actorInfo[id];
                    var s = info.scalars;
                    if (! s) {
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
                renderWindow.render();
            }

            function setBGColor(a, b) {
                renderer.setBackground(vtk.Common.Core.vtkMath.hex2float(appState.models.magnetDisplay.bgColor));
                renderWindow.render();
            }

            //function setColor(info, type, color, alpha=255) {
            function setColor(info, type, color, alpha) {
                //srdbg('setColor', 'info', info, 'type', type, 'color', color, 'alpha', alpha);
                if (angular.isUndefined(alpha)) {
                    alpha = 255;
                }
                var s = info.scalars;
                if (! s) {
                    return;
                }
                if (type !== info.type) {
                    return;
                }
                var colors = s.getData();
                var nc = s.getNumberOfComponents();
                var i = 0;
                var inds = info.colorIndices || [];
                for (var j = 0; j < inds.length && i < s.getNumberOfValues(); ++j) {
                    if (color) {
                        for (var k = 0; k < nc - 1; ++k) {
                            colors[inds[j] + k] = color[k];
                        }
                    }
                    colors[inds[j] + nc - 1] = alpha;
                    i += nc;
                }
                info.pData.modified();
            }

            function setColorMap() {
                getActorsOfType(SIREPO.APP_SCHEMA.constants.geomTypeVectors).forEach(function (actor) {
                    actor.getMapper().getInputConnection(0).filter
                        .setFormula(getVectFormula(
                            sceneData.data[0].vectors,
                            appState.models.fieldDisplay.colorMap
                        ));  // which data? all? at what index?
                });
                if (colorScale) {
                    colorbar.scale(colorScale);
                    colorbarPtr = d3.select('.colorbar').call(colorbar);
                }
                renderWindow.render();
            }

            function setEdgeColor(info, color) {
                if (! info ) {
                    return;
                }
                if (! renderer) {
                    return;
                }
                //info.actor.getProperty().setEdgeColor(...color);
                info.actor.getProperty().setEdgeColor(color[0], color[1], color[2]);
                setColor(info, SIREPO.APP_SCHEMA.constants.geomTypeLines, color);
            }

            function setScaling() {
                getActorsOfType(SIREPO.APP_SCHEMA.constants.geomTypeVectors).forEach(function (actor) {
                    var mapper = actor.getMapper();
                    mapper.setScaleFactor(vectorScaleFactor(renderer.computeVisiblePropBounds()));
                    var vs = appState.models.fieldDisplay.scaling;
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
                renderWindow.render();
            }

            function setupSceneData(data) {
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
                //srdbg('updateLayout', appState.models.magnetDisplay.viewType);
                if ($scope.isViewTypeObjects())  {
                    d3.select('svg.colorbar').remove();
                }
                panelState.showField(
                    'magnetDisplay',
                    'fieldType',
                    $scope.isViewTypeFields()
                );
                panelState.showField(
                    'geometry',
                    'alpha',
                    $scope.isViewTypeObjects()
                );
                radiaService.pointFieldTypes.forEach(function (ft) {
                    panelState.showEnum('magnetDisplay', 'fieldType', ft, hasPaths());
                });
                fieldDisplayFields.forEach(function (f) {
                    var mf = appState.parseModelField(f);
                    panelState.showField(mf[0], mf[1], $scope.isViewTypeFields());
                });
                setColorMap();
                setScaling();
            }

            function updateViewer() {
                //srdbg('update v');
                sceneData = {};
                actorInfo = {};
                radiaService.objBounds = null;
                //enableWatchFields(false);
                var inData = {
                    method: 'get_geom',
                    name: appState.models.geometry.name,
                    viewType: appState.models.magnetDisplay.viewType,
                    simulationId: appState.models.simulation.simulationId,
                };
                if (appState.models.simulation.dmpImportFile) {
                    inData.dmpImportFile = appState.models.simulation.dmpImportFile;
                }
                if ($scope.isViewTypeFields()) {
                    inData.fieldType = appState.models.magnetDisplay.fieldType;
                    inData.method = 'get_field';
                }
                if (radiaService.pointFieldTypes.indexOf(appState.models.magnetDisplay.fieldType) >= 0 ) {
                    inData.fieldPaths = appState.models.fieldPaths.paths;
                }

                //srdbg('getting app data...', inData);
                $rootScope.$broadcast('vtk.showLoader');
                radiaService.getRadiaData(
                    inData,
                    function(d) {
                        //srdbg('got app data', d);
                        if (d && d.data && d.data.length) {
                            $scope.viz.simState.state ='completed';
                            $scope.viz.solution = d.solution;
                            setupSceneData(d);
                            return;
                        }
                        //srdbg('no app data, requesting');
                        panelState.clear('geometry');
                        panelState.requestData('geometry', setupSceneData, true);
                    });
            }

            $scope.eventHandlers = {
                keypress: function (evt) {
                    // do nothing?  Stops vtk from changing render based on key presses
                },
                //ondblclick: function(evt) {
                //    vtkAPI.setCam();
                //}
            };

            appState.whenModelsLoaded($scope, function () {
                $scope.model = appState.models[$scope.modelName];
                $scope.gModel = appState.models.geometry;
                appState.watchModelFields($scope, watchFields, updateLayout);
                appState.watchModelFields($scope, ['magnetDisplay.bgColor'], setBGColor);
                alphaDelegate = radiaService.alphaDelegate();
                alphaDelegate.update = setAlpha;
                panelState.enableField('geometry', 'name', ! appState.models.simulation.isExample);
            });

            // or keep stuff on vtk viewer scope?
            // start using custom javascript events to break away from angular?
            $scope.$on('vtk-init', function (e, d) {
                //srdbg('VTK INIT', e, d);
                renderer = d.objects.renderer;
                renderWindow = d.objects.window;
                vtkAPI = d.api;
                // move pickers to vtkdisplay?
                cPicker = vtk.Rendering.Core.vtkCellPicker.newInstance();
                cPicker.setPickFromList(false);
                ptPicker = vtk.Rendering.Core.vtkPointPicker.newInstance();
                ptPicker.setPickFromList(true);
                ptPicker.initializePickList();
                renderWindow.getInteractor().onLeftButtonPress(handlePick);
                init();
            });

            $scope.$on('modelChanged', function(e, name) {
                //srdbg('modelChanged', name);
            });

            $scope.$on('geomObject.changed', function(e) {
                appState.saveChanges('geometry', function (d) {
                    //srdbg('geom save', d);
                });
            });

            $scope.$on('fieldPaths.changed', function () {
                if (! $scope.model.fieldPoints) {
                    $scope.model.fieldPoints = [];
                }
                if (! appState.models.fieldPaths.paths || ! appState.models.fieldPaths.paths.length) {
                    return;
                }
                updateViewer();
            });

            $scope.$on('geomObject.color', function (e, h) {
                var c = vtk.Common.Core.vtkMath.hex2float(h);
                setColor(
                    selectedInfo,
                    SIREPO.APP_SCHEMA.constants.geomTypePolys,
                    vtkUtils.floatToRGB(c)
                );
                setAlpha();
            });

            $scope.$on('magnetDisplay.changed', function (e, d) {
                // does not seem the best way...
                var interval = null;
                interval = $interval(function() {
                    if (interval) {
                        $interval.cancel(interval);
                        interval = null;
                    }
                    updateViewer();
                }, 500, 1);
            });

            $scope.$on('framesCleared', function () {
                updateViewer();
            });
            $scope.$on('framesLoaded', function (e, d) {
                if (! initDone) {
                    return;
                }
                updateViewer();
            });

            $scope.$on('$destroy', function () {
                $element.off();
            });

            $scope.$on('solveStarted', function (e, d) {
            });

        },
    };
});

SIREPO.app.factory('radiaVtkUtils', function(utilities) {

    var self = {};

    self.GEOM_OBJ_TYPES = [
        SIREPO.APP_SCHEMA.constants.geomTypeLines,
        SIREPO.APP_SCHEMA.constants.geomTypePolys,
    ];
    self.GEOM_TYPES = [
        SIREPO.APP_SCHEMA.constants.geomTypeLines,
        SIREPO.APP_SCHEMA.constants.geomTypePolys,
        SIREPO.APP_SCHEMA.constants.geomTypeVectors,
    ];

    self.objBounds = function(json) {
        var mins = [Number.MAX_VALUE, Number.MAX_VALUE, Number.MAX_VALUE];
        var maxs = [-Number.MAX_VALUE, -Number.MAX_VALUE, -Number.MAX_VALUE];

        self.GEOM_TYPES.forEach(function (type) {
            if (! json[type]) {
                return;
            }
            var pts = json[type].vertices;
            function modf(j) {
                return function(p, i) {
                    return i % 3 === j;
                };
            }
            for (var j = 0; j < 3; ++j) {
                //var c = pts.filter(function (p, i) {
                //    return i % 3 === j;
                //});
                var c = pts.filter(modf(j));
                mins[j] =  Math.min(mins[j], Math.min.apply(null, c));
                maxs[j] =  Math.max(maxs[j], Math.max.apply(null, c));
            }
        });

        return [mins[0], maxs[0], mins[1], maxs[1], mins[2], maxs[2]];
    };

    self.objToPolyData = function(json, includeTypes, color) {

        var colors = [];
        var points = [];
        var tData = {};

        if (! includeTypes || includeTypes.length === 0) {
            includeTypes = self.GEOM_TYPES;
        }

        var typeInfo = {};
        self.GEOM_TYPES.forEach(function (type, tIdx) {
            typeInfo[type] = {};
            if (includeTypes.indexOf(type) < 0) {
                //srdbg('Ignoring data for type', type);
                return;
            }

            var t = json[type];
            if (! t || json[type].vertices.length === 0) {
                //srdbg('No data for requested type', type);
                return;
            }

            // may not always be colors in the data
            var c = t.colors || [];
            for (var i = 0; i < c.length; i++) {
                var cc = (color || [])[i % 3] || c[i];
                colors.push(Math.floor(255 * cc));
                if (i % 3 === 2) {
                    colors.push(255);
                }
            }

            var tArr = [];
            var tOffset = points.length / 3;
            typeInfo[type].offset = tOffset;
            t.vertices.forEach(function (v) {
                points.push(v);
            });
            var tInd = 0;
            var tInds = utilities.indexArray(t.vertices.length / 3);
            t.lengths.forEach(function (len) {
                tArr.push(len);
                for (var j = 0; j < len; j++) {
                    tArr.push(tInds[tInd++] + tOffset);
                }
            });
            if (tArr.length) {
                tData[type] = new window.Uint32Array(tArr);
            }

        });

        points = new window.Float32Array(points);

        var pd = vtk.Common.DataModel.vtkPolyData.newInstance();
        pd.getPoints().setData(points, 3);

        //srdbg('setting polydata from', tData);
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

    self.vectorsToPolyData = function(json) {
        var points = new window.Float32Array(json.vectors.vertices);
        var pd = vtk.Common.DataModel.vtkPolyData.newInstance();
        pd.getPoints().setData(points, 3);
        return pd;
    };

    return self;
});
