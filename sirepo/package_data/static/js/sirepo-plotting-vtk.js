'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;

class ObjectViews {

    static scaledArray(arr, scale) {
        return arr.map(x => scale * x);
    }

    constructor(id=SIREPO.UTILS.randomString(), name='ObjectViews', center=[0, 0, 0], size=[1, 1, 1], scale=1.0) {
        this.id = id;
        this.name = name;
        this.scale = scale;
        this.center = this.scaledArray(center);
        this.size = this.scaledArray(size);

        // for convenience
        this._AXES = SIREPO.GEOMETRY.GeometryUtils.BASIS();

        this.affineTransform = new SIREPO.GEOMETRY.AffineMatrix();
        this.shapes = {};
        this.virtualViews = [];
    }

    addCopyingTransform(t, numCopies=1) {
        let c = this;
        for (let i = 1; i <= numCopies; ++i) {
            c = c.copy();
            c.addTransform(t);
            this.addVirtualView(c);
        }
    }

    addTransform(t) {
        this.affineTransform = this.affineTransform.multiplyAffine(t);
        for (const v of this.virtualViews) {
            v.addTransform(t);
        }
    }

    addView(dim, shape) {
        if (! this._AXES.includes(dim)) {
            throw new Error('Invalid axis: ' + dim);
        }
        shape.id = this.id;
        shape.name = this.name;
        this.shapes[dim] = shape;
    }

    allViews(elevation) {
        let v = [this.getView(elevation)];
        for (const vv of this.virtualViews) {
            v = v.concat(vv.allViews(elevation));
        }
        return v;
    }

    addVirtualView(v) {
        for (const dim in v.shapes) {
            v.id = `${this.id}-${v.id}`;
            v.shapes[dim].draggable = false;
        }
        this.virtualViews.push(v);
    }

    copy(exclude=[]) {
        const c = SIREPO.UTILS.copyInstance(this, exclude.concat(['id', 'affineTransform', 'shapes', 'virtualViews']));
        c.affineTransform = SIREPO.UTILS.copyInstance(this.affineTransform);
        for (const e in this.shapes) {
            c.shapes[e] = this.shapes[e].copy();
            c.shapes[e].transform = SIREPO.UTILS.copyInstance(this.shapes[e].transform);
        }
        for (const v of this.virtualViews) {
            c.addVirtualView(v.copy());
        }
        return c;
    }

    getView(elevation) {
        return this.shapes[elevation.axis];
    }

    scaledArray(arr) {
        return ObjectViews.scaledArray(arr, this.scale);
    }

    setShapeProperties(props) {
        for (const e in this.shapes) {
            const s = this.shapes[e];
            for (const p in props) {
                s[`set${SIREPO.UTILS.capitalize(p)}`](props[p]);
            }
        }
    }
}

class ExtrudedPolyViews extends ObjectViews {
    constructor(id, name, center=[0, 0, 0], size=[1, 1, 1], axis='z', points=[[0,0],[0,1],[1,1]], scale=1.0) {
        super(id, name, center, size, scale);
        this.axis = axis;
        const k = SIREPO.GEOMETRY.GeometryUtils.axisIndex(axis);
        const [w, h] = SIREPO.GEOMETRY.GeometryUtils.nextAxes(axis);
        const [i, j] = SIREPO.GEOMETRY.GeometryUtils.nextAxisIndices(axis);
        this.points = [];
        const pts = points.map(p => this.scaledArray(p));
        for (const z of [this.center[k] - this.size[k] / 2.0,this.center[k] + this.size[k] / 2.0]) {
            for (const p of pts) {
                let pp = [0, 0, 0];
                pp[i] = p[0];
                pp[j] = p[1];
                pp[k] = z;
                this.points.push(new SIREPO.GEOMETRY.Point(...pp));
            }
        }
        const s = new SIREPO.PLOTTING.PlotPolygon(id, name, this.shapePoints(axis));
        s.z = this.center[k];
        this.addView(axis, s);
        for (const dim of [w, h]) {
            const s = new SIREPO.PLOTTING.PlotPolygon(
                id,
                name,
                this.shapePoints(dim)
            );
            s.z = this.center[SIREPO.GEOMETRY.GeometryUtils.axisIndex(dim)];
            this.addView(dim, s);
        }
    }

    addTransform(t) {
        super.addTransform(t);
        const l = t.getLinearMinor();
        const x = t.getTranslation().deltas;
        for (let p of this.points) {
            const c = SIREPO.GEOMETRY.Matrix.vect(l.val, p.coords());
            p.x = c[0] + x[0];
            p.y = c[1] + x[1];
            p.z = c[2] + x[2];
        }
        for (const dim in this.shapes) {
            const sp = this.shapePoints(dim);
            this.shapes[dim].setPoints(sp.map(p => new SIREPO.GEOMETRY.Point(...p)));
        }
    }

    copy(exclude = []) {
        const c = super.copy(exclude.concat('points'));
        c.points = [];
        for (const p of this.points) {
            c.points.push(new SIREPO.GEOMETRY.Point(p.x, p.y, p.z));
        }
        return c;
    }

    shapePoints(dim) {
        const [i, j] = SIREPO.GEOMETRY.GeometryUtils.nextAxisIndices(this.axis);
        if (dim === this.axis) {
            return this.points.slice(0, this.points.length / 2).map(x => {
                const c = x.coords();
                return [c[i], c[j]];
            });
        }
        const [ii, jj] = SIREPO.GEOMETRY.GeometryUtils.nextAxisIndices(dim);
        // points can stack on each other
        const pp = SIREPO.UTILS.unique(
            this.points, (a, b) => a.coordEquals(b, ii) && a.coordEquals(b, jj)
        ).map(p => [p.coords()[ii], p.coords()[jj]]);
        return d3.geom.hull(pp);
    }
}

class CuboidViews extends ExtrudedPolyViews {
    constructor(id, name, center=[0, 0, 0], size=[1, 1, 1], scale=1.0) {
        super(
            id,
            name,
            center,
            size,
            'z',
            [
                [center[0] - size[0] / 2, center[1] - size[1] / 2],
                [center[0] - size[0] / 2, center[1] + size[1] / 2],
                [center[0] + size[0] / 2, center[1] + size[1] / 2],
                [center[0] + size[0] / 2, center[1] - size[1] / 2],
            ],
            scale
        );
    }
}

class CylinderViews extends ExtrudedPolyViews {
    constructor(
        id,
        name,
        center=[0, 0, 0],
        size=[1, 1, 1],
        axis='z',
        numSides=8,
        scale=1.0
    ) {
        const [i, j] = SIREPO.GEOMETRY.GeometryUtils.nextAxisIndices(axis);
        const pts = [];
        for (let n = 0; n < numSides; ++n) {
            const t = 2 * n * Math.PI / numSides;
            pts.push(
                [
                    center[i] + 0.5 * Math.cos(t) * size[i],
                    center[j] + 0.5 * Math.sin(t) * size[j],
                ]
            );
        }
        super(id, name, center, size, axis, pts, scale);
    }
}

class RacetrackViews extends ExtrudedPolyViews {
    constructor(
        id,
        name,
        center=[0, 0, 0],
        size=[1, 1, 1],
        axis='z',
        numArcSides=8,
        outerRadius=1.0,
        scale=1.0

    ) {
        let pts = [];
        const [i, j] = SIREPO.GEOMETRY.GeometryUtils.nextAxisIndices(axis);
        const tr = [Math.cos, Math.sin];
        [[-1, 1], [1, 1], [1, -1], [-1, -1]].forEach((d, n) => {
            const c = [
                center[i] + d[0] * (size[i] / 2 - outerRadius),
                center[j] + d[1] * (size[j] / 2 - outerRadius)
            ];
            for (let m = 0; m <= numArcSides; ++m) {
                const t = m * Math.PI / (2 * numArcSides);
                pts.push(
                    [
                        c[0] + d[0] * outerRadius * tr[0](t),
                        c[1] + d[1] * outerRadius * tr[1](t),
                    ]
                );
            }
            tr.reverse();
        });
        super(id, name, center, size, axis, pts, scale);
    }
}

class SphereViews extends ObjectViews {
    constructor(
        id,
        name,
        center=[0, 0, 0],
        radius=1.0,
        numSides=8,
        scale=1.0
    ) {
        super(id, name, center, [2 * radius, 2 * radius, 2 * radius], scale);
        this.center = center;
        this.numSides = numSides;
        this.radius = radius;
        SIREPO.GEOMETRY.GeometryUtils.BASIS().forEach(dim => {
            this.addView(dim, new SIREPO.PLOTTING.PlotPolygon(id, name, this.buildPoints()));
        });
    }

    buildPoints(dim) {
        const pts = [];
        const [i, j] = SIREPO.GEOMETRY.GeometryUtils.nextAxisIndices(dim);
        for (let n = 0; n < this.numSides; ++n) {
            const t = 2 * n * Math.PI / this.numSides;
            pts.push(
                [
                    this.center[i] + 0.5 * Math.cos(t) * this.radius,
                    this.center[j] + 0.5 * Math.sin(t) * this.radius,
                ]
            );
        }
        return pts;
    }

    setRadius(r) {
        this.radius = r;
        this.updateViews();
    }

    shapePoints(dim) {
        return this.shapes[dim].points.map(p => this.scaledArray(p.coords()));
    }

    updateView(dim) {
        this.shapes[dim].setPoints(this.buildPoints(dim).map(x => new SIREPO.GEOMETRY.Point(...x)));
    }

    updateViews() {
        SIREPO.GEOMETRY.GeometryUtils.BASIS().forEach(dim => {
            this.updateView(dim);
        });
    }
}

/**
 * Collection of static methods and fields related to vtk
 */
class VTKUtils {

    /**
     * Builds a wireframe box with the specified bounds and optional padding
     * @param {[number]} bounds - the bounds in the format [xMin, xMax, yMin, yMax, zMin, zMax]
     * @param {number} padPct - additional padding as a percentage of the size
     * @returns {BoxBundle}
     */
    static buildBoundingBox(bounds, padPct = 0.0) {
        const l = [
            Math.abs(bounds[1] - bounds[0]),
            Math.abs(bounds[3] - bounds[2]),
            Math.abs(bounds[5] - bounds[4])
        ].map(c=> (1 + padPct) * c);

        const b = new BoxBundle(
            l,
            [(bounds[1] + bounds[0]) / 2, (bounds[3] + bounds[2]) / 2, (bounds[5] + bounds[4]) / 2]
        );
        b.actorProperties.setRepresentationToWireframe();
        return b;
    }

    /**
     * Makes an orientation widget out of the given vtk actor and interactor, placed in the given corner of the
     * viewport
     * @param {vtk.Rendering.Core.vtkActor} actor - vtk actor
     * @param {vtk.Rendering.Core.vtkRenderWindowInteractor} interactor - interactor from a render window
     * @param {vtk.Interaction.Widgets.vtkOrientationMarkerWidget.Corners} location - which corner to place the widget
     * @returns {vtk.Interaction.Widgets.vtkOrientationMarkerWidget}
     */
    static buildOrientationMarker(actor, interactor, location) {
        const m = vtk.Interaction.Widgets.vtkOrientationMarkerWidget.newInstance({
            actor: actor,
            interactor: interactor,
        });
        m.setViewportCorner(location);
        m.setViewportSize(0.07);
        m.computeViewport();
        m.setMinPixelSize(50);
        m.setMaxPixelSize(100);

        return m;
    }

    /**
     * Converts a string or an array of floats to an array of floats using vtk's conversion util, for use in
     * colors
     * @param {string|[number]} hexStringOrArray - a color string (#rrggbb) or array of floats
     * @returns {[number]} - array of floats ranging from 0 - 1.
     */
    static colorToFloat(hexStringOrArray) {
        return Array.isArray(hexStringOrArray) ? hexStringOrArray : vtk.Common.Core.vtkMath.hex2float(hexStringOrArray);
    }

    /**
     * Converts a string or an array of floats to a string using vtk's conversion util, for use in
     * colors
     * @param {string|[number]} hexStringOrArray - a color string (#rrggbb) or array of floats
     * @returns {string} - a color string (#rrggbb)
     */
    static colorToHex(hexStringOrArray) {
       return Array.isArray(hexStringOrArray) ? vtk.Common.Core.vtkMath.floatRGB2HexCode(hexStringOrArray) : hexStringOrArray;
    }

    /**
     * Creates a vtk user matrix from a SquareMatrix.
     * * @param {SquareMatrix} matrix - vtk actor
     * @returns {[[number]]}
     */
    static userMatrix(matrix) {
        let m = [];
        for (const x of matrix.val) {
            m = m.concat(x);
            m.push(0);
        }
        m = m.concat([0, 0, 0, 1]);
        return m;
    }
}

// used to create array of arrows (or other objects) for vector fields
// change to use magnitudes and color locally
class VTKVectorFormula {

    static ARRAY_NAMES() {
        return {
            ...VTKVectorFormula.FLOAT_ARRAY_NAMES(),
            scalars: 'scalars',
        };
    }

    static FLOAT_ARRAY_NAMES() {
        return {
            linear: 'linear',
            log: 'log',
            orientation: 'orientation',
        };
    }

    constructor(scalars, vectors, colorMapName='jet') {
        this.scalars = scalars;
        this.vectors = vectors;
        this.colorMapName = colorMapName;
        this.colorMap = SIREPO.PLOTTING.Utils.COLOR_MAP()[colorMapName];

        this.magnitudes = this.scalars;
        this.directions = this.vectors.map((x, i) => x.map(y => y / this.magnitudes[i]));
        this.norms = SIREPO.UTILS.normalize(this.magnitudes);

        // get log values back into the original range, so that the extremes have the same
        // size as a linear scale
        const logMags = this.magnitudes.map(x =>  Math.log(x));
        const minLogMag = SIREPO.UTILS.arrayMin(logMags);
        const maxLogMag = SIREPO.UTILS.arrayMax(logMags);
        const minMag = SIREPO.UTILS.arrayMin(this.magnitudes);
        const maxMag = SIREPO.UTILS.arrayMax(this.magnitudes);

        this.logMags = logMags.map(
            n => minMag + (n - minLogMag) * (maxMag - minMag) / (maxLogMag - minLogMag)
        );
        this.colorScale = SIREPO.PLOTTING.Utils.colorScale(minMag, maxMag, this.colorMap);

        this.arrays = {
            input: [{
                location: vtk.Common.DataModel.vtkDataSet.FieldDataTypes.COORDINATE,
            }],
            output: [{
                location: vtk.Common.DataModel.vtkDataSet.FieldDataTypes.POINT,
                name: 'scalars',
                dataType: 'Uint8Array',
                attribute: vtk.Common.DataModel.vtkDataSetAttributes.AttributeTypes.SCALARS,
                numberOfComponents: 3,
            }],
        };
        for (const n of Object.values(VTKVectorFormula.FLOAT_ARRAY_NAMES())) {
            this.arrays.output.push({
                location: vtk.Common.DataModel.vtkDataSet.FieldDataTypes.POINT,
                name: n,
                dataType: 'Float32Array',
                numberOfComponents: 3,
            });
        }
    }

    getArrays(inputDataSets) {
        return this.arrays;
    }

    evaluate(arraysIn, arraysOut) {

        function getSubArrayOut(array, name) {
            const o = arraysOut.map(d => d.getData());
            for (const i in array) {
                if (array[i].name === name) {
                    return o[i];
                }
            }
            return null;
        }

        const coords = arraysIn.map(d => d.getData())[0];

        // note these arrays already have the correct length, so we need to set elements, not append
        const out = this.arrays.output;
        const orientation = getSubArrayOut(out, VTKVectorFormula.ARRAY_NAMES().orientation);
        const linScale = getSubArrayOut(out, VTKVectorFormula.ARRAY_NAMES().linear).fill(1.0);
        const logScale = getSubArrayOut(out, VTKVectorFormula.ARRAY_NAMES().log).fill(1.0);
        const scalars = getSubArrayOut(out, VTKVectorFormula.ARRAY_NAMES().scalars);

        for (let i = 0; i < coords.length / 3; ++i) {
            let c = [0, 0, 0];
            if (this.colorMap.length) {
                const rgb = d3.rgb(this.colorScale(this.magnitudes[i]));
                c = [rgb.r, rgb.g, rgb.b];
            }
            // scale arrow length (object-local x-direction) only
            // this can stretch/squish the arrowhead though so the actor may have to adjust the ratio
            linScale[3 * i] = this.magnitudes[i];
            logScale[3 * i] = this.logMags[i];
            for (let j = 0; j < 3; ++j) {
                const k = 3 * i + j;
                orientation[k] = this.directions[i][j];
                scalars[k] = c[j];
            }
        }

        arraysOut.forEach(x => {
            x.modified();
        });
    }
}

/**
 * This class encapsulates various basic vtk elements such as the renderer, and supplies methods for using them.
 */
class VTKScene {
    /**
     * @param {{}} container - jquery element in which to place the scene
     * @param {string} resetSide - the dimension to display facing the user when the scene is reset
     */
    constructor(container, resetSide, resetDirection=1) {
        this.fsRenderer = vtk.Rendering.Misc.vtkFullScreenRenderWindow.newInstance({
            background: [1, 1, 1, 1],
            container: container,
            listenWindowResize: true,
        });

        this.container = this.fsRenderer.getContainer();
        this.renderer = this.fsRenderer.getRenderer();
        this.renderWindow = this.fsRenderer.getRenderWindow();
        this.cam = this.renderer.get().activeCamera;
        this.camProperties = VTKScene.CAM_DEFAULTS();
        this.resetSide = resetSide;
        this.resetDirection = resetDirection;

        this.marker = null;
        this.isMarkerEnabled = false;

        this.viewSide = this.resetSide;
        this.viewDirection = this.resetDirection;
    }

    /**
     * Gets a map of dimension to camera properties
     * @returns {{x: {viewUp: number[]}, y: {viewUp: number[]}, z: {viewUp: number[]}}}
     * @constructor
     */
    static CAM_DEFAULTS() {
        return {
            x: {
                viewUp: [0, 0, 1],
            },
            y: {
                viewUp: [0, 0, 1],
            },
            z: {
                viewUp: [0, 1, 0],
            }
        };
    }

    /**
     * Convenience method for adding an actor to the renderer
     * @param {vtk.Rendering.Core.vtkActor} actor
     */
    addActor(actor) {
        this.renderer.addActor(actor);
    }

    /**
     * Gets the bounds of all the objects in the scene
     * @returns {[number]}
     */
    bounds() {
        this.renderer.resetCamera();
        return this.renderer.computeVisiblePropBounds();
    }

    /**
     * Gets an icon based on the view direction ("into/out of the screen")
     * @returns {string}
     */
    directionIcon() {
        return this.viewDirection === 1 ? '⊙' : '⦻';
    }

    /**
     * @returns {boolean} - true if an orientation marker has been defined
     */
    hasMarker() {
        return ! ! this.marker;
    }

    /**
     * Refreshes the visibility of the orientation marker, if one exists
     * @param doRender - if true, perform a render
     */
    refreshMarker(doRender=true) {
        if (! this.hasMarker()) {
            return;
        }
        this.marker.setEnabled(this.isMarkerEnabled);
        if (doRender) {
            this.render();
        }
    }

    /**
     * Convenience method for removing the given actor from the renderer
     * @param {vtk.Rendering.Core.vtkActor} actor
     */
    removeActor(actor) {
        if (! actor ) {
            return;
        }
        this.renderer.removeActor(actor);
    }

    /**
     * Convenience method for removing the given actors from the renderer, or all actors if input is null/empty
     * @param {[vtk.Rendering.Core.vtkActor]|null} actors
     */
    removeActors(actors) {
        if (! actors) {
            this.renderer.removeAllActors();
            return;
        }
        for (const a of actors) {
            this.removeActor(a);
        }
        actors.length = 0;
    }

    /**
     * Convenience method for triggering a render in the render window
     */
    render() {
        this.renderWindow.render();
    }

    /**
     * Sets the camera so that the resetSide is facing the user
     */
    resetView() {
        this.showSide();
    }

    /**
     * Rotates the camera around the axis pointing into/out of the screen
     * @param {number} angle - the angle ini degrees
     */
    rotate(angle) {
        this.cam.roll(angle);
        this.render();
    }

    /**
     * Builds a wireframe box around all the objects in the scene, with optional padding
     * @param {number} padPct - additional padding as a percentage of the size
     * @returns {BoxBundle}
     */
    sceneBoundingBox(padPct = 0.0) {
        // must reset the camera before computing the bounds
        this.renderer.resetCamera();
        return VTKUtils.buildBoundingBox(this.bounds(), padPct);
    }

    /**
     * Sets the background color of the renderer
     * @param {string|[number]} color
     */
    setBgColor(color) {
        this.renderer.setBackground(VTKUtils.colorToFloat(color));
        this.render();
    }

    /**
     * Sets the camera to the given position, pointing such that "up" is in the given direction
     * @param {[number]} position
     * @param {[number]} viewUp
     */
    setCam(position = [1, 0, 0], viewUp = [0, 0, 1]) {
        // set focal point outside of the origin initially to avoid a VTK warning:
        //  "resetting view-up since view plane normal is parallel"
        // this happens because the camera is recalculated on each modification
        this.cam.setFocalPoint(10, 10, 10);
        this.cam.setViewUp(...viewUp);
        this.cam.setPosition(...position);
        this.cam.setFocalPoint(0, 0, 0);
        this.renderer.resetCamera();
        this.cam.yaw(0.6);
        if (this.marker) {
            this.marker.updateMarkerOrientation();
        }
        this.render();
    }

    /**
     * Sets a property for the camera along the given dimension
     * @param {string} dim x|y|z
     * @param {string} name
     * @param {*} val
     */
    setCamProperty(dim, name, val) {
        this.camProperties[dim][name] = val;
    }

    /**
     * Sets the camera so that the given side is facing the user. If that side is already set, flip to the
     * other side
     * @param {string} side - x|y|z
     */
    showSide(side) {
        if (! side) {
            this.viewSide = this.resetSide;
            this.viewDirection = this.resetDirection;
        }
        else {
            if (side === this.viewSide) {
                this.viewDirection *= -1;
            }
            this.viewSide = side;
        }
        const pos = SIREPO.GEOMETRY.GeometryUtils.BASIS_VECTORS()[this.viewSide]
            .map(c =>  c * this.viewDirection);
        this.setCam(pos, this.camProperties[this.viewSide].viewUp);
    }

    /**
     * Sets an orientation marker
     * @param {vtk.Interaction.Widgets.vtkOrientationMarkerWidget} m
     */
    setMarker(m) {
        this.marker = m;
        this.isMarkerEnabled = true;
        this.refreshMarker();
    }

    /**
     * Cleans up vtk items
     */
    teardown() {
        window.removeEventListener('resize', this.fsRenderer.resize);
        document.removeEventListener(
            'visibilitychange',
            this.fsRenderer.getInteractor().handleVisibilityChange,
        );
        this.isMarkerEnabled = false;
        this.refreshMarker(false);
        this.fsRenderer.getInteractor().unbindEvents();
        this.fsRenderer.delete();
    }
}

/**
 * A convenient object bundling a source, actor, and mapper, which almost always appear together anyway
 */
class ActorBundle {
    /**
     * @param {*} source - a vtk source, reader, etc.
     * @param {SIREPO.GEOMETRY.Transform} transform - a Transform to translate between "lab" and "local" coordinate systems
     * @param {Object} actorProperties - a map of actor properties (e.g. 'color') to values
     */
    constructor(source, transform = new SIREPO.GEOMETRY.Transform(), actorProperties = {}) {
        /** @member {SIREPO.GEOMETRY.Transform} - the transform */
        this.transform = transform;

        /** @member {vtk.Rendering.Core.vtkMapper} - a mapper */
        this.mapper = vtk.Rendering.Core.vtkMapper.newInstance();

        /** @member {*} - vtk source */
        this.setSource(source);

        /** @member {vtk.Rendering.Core.vtkActor} - the actor */
        this.actor = vtk.Rendering.Core.vtkActor.newInstance({
            mapper: this.mapper
        });

        /** @member {vtk.Rendering.Core.Property} - properties of the actor */
        this.actorProperties = this.actor.getProperty();

        this.setActorProperties(actorProperties);

        this.actor.setUserMatrix(VTKUtils.userMatrix(this.transform.matrix));
    }

    /**
     * Builds a wireframe box around this actor, with optional padding
     * @param {number} padPct - additional padding as a percentage of the size
     * @returns {BoxBundle}
     */
    actorBoundingBox(padPct = 0.0) {
        return VTKUtils.buildBoundingBox(this.actor.getBounds(), padPct);
    }

    /**
     * Gets the value of the actor property with the given name
     * @param {string} name - the name of the property
     * @returns {*}
     */
    getActorProperty(name) {
        return this.actorProperties[`get${SIREPO.UTILS.capitalize(name)}`]();
    }

    /**
     * Set a group of properties.
     */
    setActorProperties(values) {
        for (const p in values) {
            this.setActorProperty(p, values[p]);
        }
    }

    /**
     * Sets the actor property with the given name to the given value
     * @param {string} name - the name of the property
     * @param {*} value - the value to set
     */
    setActorProperty(name, value) {
        // special handling for colors
        if (name === 'color') {
            this.setColor(value);
            return;
        }
        this.actorProperties[`set${SIREPO.UTILS.capitalize(name)}`](value);
    }

    /**
     * Convenience method for setting the color. Uses colorToFloat to convert
     * @param {string|[number]} color
     */
    setColor(color) {
        this.actorProperties.setColor(VTKUtils.colorToFloat(color));
    }

    /**
     *
     * @param {[int]} colors - array of unsigned ints (0-255).
     * @param {int} numColorComponents - the number of components in a color (3 for rgb or 4 for rgb + alpha)
     */
    setColorScalarsForCells(colors, numColorComponents) {
        const pd = this.mapper.getInputData();
        pd.getCellData().setScalars(
            vtk.Common.Core.vtkDataArray.newInstance({
                dataType: vtk.Common.Core.vtkDataArray.VtkDataTypes.UNSIGNED_CHAR,
                numberOfComponents: numColorComponents,
                values: colors,
            })
        );
        pd.modified();
    }

    /**
     * Sets the mapper for this bundle as well as the actor
     * @param {vtk.Rendering.Core.vtkMapper} mapper
     */
    setMapper(mapper) {
        this.mapper = mapper;
        this.actor.setMapper(mapper);
    }

    /**
     * Sets the source for this bundle. Also sets the mapper's input connection to the source's output
     * @param {*} source - vtk source
     */
    setSource(source) {
        if (source) {
            this.source = source;
            this.mapper.setInputConnection(source.getOutputPort());
        }
    }
}

/**
 * A bundle for a cube source
 */
class BoxBundle extends ActorBundle {
    /**
     * @param {[number]} labSize - array of the x, y, z sides of the box in the lab
     * @param {[number]} labCenter - array of the x, y, z coords of the box's center in the lab
     * @param {SIREPO.GEOMETRY.Transform} transform - a Transform to translate between "lab" and "local" coordinate systems
     * @param {{}} actorProperties - a map of actor properties (e.g. 'color') to values
     */
    constructor(
        labSize = [1, 1, 1],
        labCenter = [0, 0, 0],
        transform = new SIREPO.GEOMETRY.Transform(),
        actorProperties = {}
    ) {
        super(
            vtk.Filters.Sources.vtkCubeSource.newInstance(),
            transform,
            actorProperties
        );
        this.setCenter(labCenter);
        this.setSize(labSize);
    }

    /**
     * Sets the center of the box
     * @param {[number]} labCenter - array of the x, y, z coords of the box's center in the lab
     */
    setCenter(labCenter) {
        this.source.setCenter(labCenter);
    }

    /**
     * Sets the size of the box
     * @param {[number]} labSize- array of the x, y, z lengths of the box
     */
    setSize(labSize) {
        this.source.setXLength(labSize[0]);
        this.source.setYLength(labSize[1]);
        this.source.setZLength(labSize[2]);
    }

}

/**
 * A bundle for generic polydata
 */
class PolyDataBundle extends ActorBundle {
    /**
     * @param vtk.Common.DataModel.vtkPolyData polyData
     * @param {SIREPO.GEOMETRY.Transform} transform - a Transform to translate between "lab" and "local" coordinate systems
     * @param {{}} actorProperties - a map of actor properties (e.g. 'color') to values
     */
    constructor(
        polyData,
        transform = new SIREPO.GEOMETRY.Transform(),
        actorProperties = {}
    ) {
        super(
            null,
            transform,
            actorProperties
        );
        this.polyData = polyData;
        this.mapper.setInputData(polyData);
    }
}

/**
 * A bundle for a sphere source
 */
class SphereBundle extends ActorBundle {
    /**
     * @param {[number]} labCenter - center in the lab
     * @param {number} radius
     * @param {SIREPO.GEOMETRY.Transform} transform - a Transform to translate between "lab" and "local" coordinate systems
     * @param {Object} actorProperties - a map of actor properties (e.g. 'color') to values
     */
    constructor(
        labCenter = [0, 0, 0],
        radius = 1.0,
        transform= new SIREPO.GEOMETRY.Transform(),
        actorProperties= {}
    ) {
        super(
            vtk.Filters.Sources.vtkSphereSource.newInstance(),
            transform,
            actorProperties
        );
        this.setCenter(labCenter);
        this.setRadius(radius);
        this.setRes();
    }

    /**
     * Sets the center of the sphere
     * @param {[number]} labCenter - center in the lab
     */
    setCenter(labCenter) {
        this.source.setCenter(labCenter);
    }

    /**
     * Sets the radius of the sphere
     * @param {number} radius
     */
    setRadius(radius) {
        this.source.setRadius(radius);
    }

    /**
     * Sets the resolution in each angular direction
     * @param {number} thetaRes - number of latitude divisions
     * @param {number} phiRes - number of longitude divisions
     */
    setRes(thetaRes = 16, phiRes = 16) {
        this.source.setThetaResolution(thetaRes);
        this.source.setPhiResolution(phiRes);
    }
}

/**
 * A bundle for a vector field
 */
class VectorFieldBundle extends ActorBundle {
    /**
     * @param {[[number]]} vectors - array of 3-dimensional arrays containing the vectors
     * @param {[[number]]} positions - array of 3-dimensional arrays containing the coordinates of the vectors
     * @param {number} scaleFactor - scales the length of the arrows
     * @param {string} colormapName - name of a color map for the arrows
     * @param {SIREPO.GEOMETRY.Transform} transform - a Transform to translate between "lab" and "local" coordinate systems
     * @param {{}} actorProperties - a map of actor properties (e.g. 'color') to values
     */
    constructor(
        scalars,
        vectors,
        positions,
        scaleFactor = 1.0,
        useTailAsOrigin = false,
        colormapName = 'jet',
        transform = new SIREPO.GEOMETRY.Transform(),
        actorProperties = {}
    ) {
        super(
            null,
            transform,
            actorProperties
        );
        this.formula = new VTKVectorFormula(scalars, vectors, colormapName);
        this.polyData = vtk.Common.DataModel.vtkPolyData.newInstance();
        this.polyData.getPoints().setData(
            new window.Float32Array(positions.flat()),
            3
        );

        const vectorCalc = vtk.Filters.General.vtkCalculator.newInstance();
        vectorCalc.setFormula(this.formula);
        vectorCalc.setInputData(this.polyData);

        this.setMapper(vtk.Rendering.Core.vtkGlyph3DMapper.newInstance());

        this.mapper.setInputConnection(vectorCalc.getOutputPort(), 0);
        const s = vtk.Filters.Sources.vtkArrowSource.newInstance();
        if (useTailAsOrigin) {
            // this undoes a translation in the arrowSource instantiation
            vtk.Common.Core.vtkMatrixBuilder
                .buildFromRadian()
                .translate(0.5 - 0.5 * s.getTipLength(), 0.0, 0.0)
                .apply(s.getOutputData().getPoints().getData());
        }

        this.mapper.setInputConnection(
            s.getOutputPort(), 1
        );
        this.mapper.setOrientationArray(VTKVectorFormula.ARRAY_NAMES().orientation);

        // this scales by a constant - the default is to use scalar data
        this.setScaleFactor(scaleFactor);
        this.mapper.setColorModeToDefault();

        this.setScaling('uniform');
    }

    setScaleFactor(scaleFactor) {
        this.scaleFactor = scaleFactor;
        this.mapper.setScaleFactor(this.scaleFactor);
    }

    setScaling(scaleType) {
        if (scaleType === 'uniform') {
            this.mapper.setScaleModeToScaleByConstant();
        }
        else {
            this.mapper.setScaleArray(VTKVectorFormula.FLOAT_ARRAY_NAMES()[scaleType]);
            this.mapper.setScaleModeToScaleByComponents();
        }
    }
}


/**
 * Provides a mapping from "lab" coordinates to vtk's coordinates via a SIREPO.GEOMETRY.Transform.
 * Also wraps the creation of various Bundles so the transform gets applied automatically
 */
class CoordMapper {
    /**
     * @param {SIREPO.GEOMETRY.Transform} transform - a Transform to translate between "lab" and "local" coordinate systems
     */
    constructor(transform = new SIREPO.GEOMETRY.Transform()) {
        this.transform = transform;
    }

    /**
     * Creates a Bundle from an arbitrary source
     * @param {*} source - a vtk source, reader, etc.
     * @param {SIREPO.GEOMETRY.Transform} transform - a Transform to translate between "lab" and "local" coordinate systems
     * @param {{}} actorProperties - a map of actor properties (e.g. 'color') to values
     */
    buildActorBundle(source, actorProperties) {
        return new ActorBundle(source, this.transform, actorProperties);
    }

    /**
     * Builds a box
     * @param {[number]} labSize - array of the x, y, z sides of the box in the lab
     * @param {[number]} labCenter - array of the x, y, z coords of the box's center in the lab
     * @param {{}} actorProperties - a map of actor properties (e.g. 'color') to values
     * @returns {BoxBundle}
     */
    buildBox(labSize, labCenter, actorProperties) {
        return new BoxBundle(labSize, labCenter, this.transform, actorProperties);
    }

    /**
     * Creates a Bundle from PolyData
     * @param {vtk.Common.DataModel.vtkPolyData} polyData
     * @param {{}} actorProperties - a map of actor properties (e.g. 'color') to values
     */
    buildPolyData(polyData, actorProperties) {
        return new PolyDataBundle(polyData, this.transform, actorProperties);
    }

    /**
     * Builds a sphere
     * @param {[number]} labCenter - center in the lab
     * @param {number} radius
     * @param {Object} actorProperties - a map of actor properties (e.g. 'color') to values
     * @returns {SphereBundle}
     */
    buildSphere(labCenter, radius, actorProperties) {
        return new SphereBundle(labCenter, radius, this.transform, actorProperties);
    }

    /**
     * Creates a Bundle from vectors
     * @param {[[number]]} vectors - array of 3-dimensional arrays containing the vectors
     * @param {[[number]]} positions - array of 3-dimensional arrays containing the coordinates of the vectors
     * @param {number} scaleFactor - scales the length of the arrows
     * @param {boolean} useTailAsOrigin - when true, the origin is the vector's tail. Otherwise, the center
     * @param {string} colormapName - name of a color map for the arrows
     * @param {{}} actorProperties - a map of actor properties (e.g. 'color') to values
     */
    buildVectorField(scalars, vectors, positions, scaleFactor, useTailAsOrigin=false, colormapName='jet', actorProperties={}) {
        return new VectorFieldBundle(scalars, vectors, positions, scaleFactor, useTailAsOrigin, colormapName, this.transform, actorProperties);
    }
}

/**
 * A 2-dimensional representation of a 3-dimensional vtk object
 */
class ViewPortObject {
    /**
     * @param {*} source - a vtk source, reader, etc.
     * @param {vtk.Rendering.Core.vtkRenderer} renderer - a vtk renderer
     */
    constructor(source, renderer) {
        /** @member {*} - vtk source */
        this.source = source;

        /** @member {vtk.Rendering.Core.vtkCoordinate} - vtk coordinate system */
        this.worldCoord = vtk.Rendering.Core.vtkCoordinate.newInstance({
            renderer: renderer
        });
        this.worldCoord.setCoordinateSystemToWorld();
    }

    /**
     * Calculates the rectangle surrounding the vtk object, projected into the viewport
     * @returns {Rect}
     */
    boundingRect() {
        const e = this.extrema();
        const xCoords = [];
        const yCoords = [];
        e.x.concat(e.y).forEach(arr => {
            arr.forEach(p => {
                xCoords.push(p.x);
                yCoords.push(p.y);
            });
        });
        return new SIREPO.GEOMETRY.Rect(
            new SIREPO.GEOMETRY.Point(SIREPO.UTILS.arrayMin(xCoords), SIREPO.UTILS.arrayMin(yCoords)),
            new SIREPO.GEOMETRY.Point(SIREPO.UTILS.arrayMax(xCoords), SIREPO.UTILS.arrayMax(yCoords))
        );
    }

    /**
     * An external edge has all other corners on the same side of the line it defines
     * @param {string} dim - dimension (x|y|z)
     * @returns {[LineSegment]}
     */
    externalViewportEdgesForDimension(dim) {
        const edges = [];
        for (const edge of this.viewportEdges()[dim]) {
            let numCorners = 0;
            let compCount = 0;
            for (const otherDim of SIREPO.GEOMETRY.GeometryUtils.BASIS()) {
                if (otherDim === dim) {
                    continue;
                }
                for (const otherEdge of this.viewportEdges()[otherDim]) {
                    const otherEdgeCorners = otherEdge.points;
                    for (let k = 0; k <= 1; ++k) {
                        const n = edge.comparePoint(otherEdgeCorners[k]);
                        compCount += n;
                        if (n !== 0) {
                            numCorners++;
                        }
                    }
                }
            }
            edges.push(Math.abs(compCount) === numCorners ? edge : null);
        }
        return edges;
    }

    /**
     * points on the screen that have the largest and smallest values in each dimension
     * @returns {{}} - mapping of dimension to the extrema, e.g. {x: [p1, p2, ...], ...}
     */
    extrema() {
        const ex = {};
        for (const dim of SIREPO.GEOMETRY.GeometryUtils.BASIS().slice(0, 2)) {
            ex[dim] = [];
            for (const x of [false, true]) {
                ex[dim].push(SIREPO.GEOMETRY.GeometryUtils.extrema(this.viewPortCorners(), dim, x));
            }
        }
        return ex;
    }

    /**
     * Translates a 3-dimensional Point in the vttk world corresponding to the given 2-dimensional point in the viewport
     * @param {Point} worldPoint
     * @returns {Point}
     */
    viewPortPoint(worldPoint) {
        // this is required to do conversions for different displays/devices
        const pixels = window.devicePixelRatio;
        this.worldCoord.setCoordinateSystemToWorld();
        this.worldCoord.setValue(worldPoint.coords());
        const lCoord = this.worldCoord.getComputedLocalDisplayValue()
            .map(x => x / pixels);
        return new SIREPO.GEOMETRY.Point(lCoord[0], lCoord[1]);
    }

    /**
     * Translates the given Points from vtk world to viewport
     * @param {[Point]} coords - 3d points
     * @returns {[Point]} - 2d points
     */
    viewPortPoints(coords) {
        return coords.map(x => this.viewPortPoint(x));
    }

    /**
     * Translates corners from vtk world to viewport
     * @returns {[Point]}
     */
    viewPortCorners() {
        return this.viewPortPoints(this.worldCorners());
    }

    /**
     * Translates edges from vtk world to viewport
     * @returns {{}} - mapping of dimension to the edges, e.g. {x: [LineSegment1, LineSegment2], ...}
     */
    viewportEdges() {
        const ee = {};
        const es = this.worldEdges();
        for (const e in es) {
            const lEdges = [];
            for (let edge of es[e]) {
                const lpts = this.viewPortPoints(edge.points);
                lEdges.push(new SIREPO.GEOMETRY.LineSegment(lpts[0], lpts[1]));
            }
            ee[e] = lEdges;
        }
        return ee;
    }

    /**
     * Gets the center of the vtk object
     * @returns {Point}
     */
    worldCenter() {
        return new SIREPO.GEOMETRY.Point(...this.source.getCenter());
    }

    /**
     * Gets the corners of the vtk object. Subclasses should override
     * @returns {[Point]}
     */
    worldCorners() {
        return [];
    }

    /**
     * Gets the edges - that is, the lines connecting corners. Subclasses should override
     * @returns {{}}
     */
    worldEdges() {
        return {};
    }
}

/**
 * A ViewPortObject for a cube source
 */
class ViewPortBox extends ViewPortObject {
    /**
     * @param {vtk.Filters.Sources.vtkCubeSource} source - vtk cube source
     * @param {vtk.Rendering.Core.vtkRenderer} renderer - vtk renderer
     */
    constructor(source, renderer) {
        super(source, renderer);
        this.arrangeEdges();
    }

    /**
     * Puts the edges into suitable order
     */
    arrangeEdges() {
        const edgeCfg = {
            x: {
                edgeCornerPairs: [[0, 1], [4, 5], [2, 3], [6, 7]],
                sense: 1
            },
            y: {
                edgeCornerPairs: [[0, 2], [1, 3], [4, 6], [5, 7]],
                sense: 1
            },
            z: {
                edgeCornerPairs: [[4, 0], [5, 1], [6, 2], [7, 3]],
                sense: -1
            },
        };
        for (const dim in edgeCfg) {
            const c = edgeCfg[dim];
            for (let i = 0; i < c.edgeCornerPairs.length; ++i) {
                if (c.sense < 0) {
                    c.edgeCornerPairs[i].reverse();
                }
            }
        }
        this.edgeCfg = edgeCfg;
    }

    /**
     * Gets the lines through the center of the object for each dimension
     * @returns {{}} - mapping of dimension to the lines, e.g. {x: LineSegment1, ...}
     */
    centerLines() {
        return this.coordLines(this.worldCenter().coords());
    }

    /**
     * Gets coordinate axis lines through the given point
     * @param {[number]} origin
     * @returns {{}} - mapping of dimension to the lines, e.g. {x: LineSegment1, ...}
     */
    coordLines(origin=[0, 0, 0]) {
        const ctr = new SIREPO.GEOMETRY.Matrix(origin);
        const cls = {};
        const sz = this.worldSize();
        const tx = new SIREPO.GEOMETRY.Transform(new SIREPO.GEOMETRY.Matrix(
            [
                [sz[0] / 2, 0, 0],
                [0, sz[1] / 2, 0],
                [0, 0, sz[2] / 2]
            ]
        ));
        for(const dim in SIREPO.GEOMETRY.GeometryUtils.BASIS_VECTORS()) {
            const txp = tx.apply(new SIREPO.GEOMETRY.Matrix(SIREPO.GEOMETRY.GeometryUtils.BASIS_VECTORS()[dim]));
            cls[dim] = new SIREPO.GEOMETRY.LineSegment(
                this.viewPortPoint(new SIREPO.GEOMETRY.Point(...ctr.subtract(txp).val)),
                this.viewPortPoint(new SIREPO.GEOMETRY.Point(...ctr.add(txp).val))
            );
        }
        return cls;
    }

    /**
     * Gets the lines through the world origin for each dimension
     * @returns {{}} - mapping of dimension to the edges, e.g. {x: LineSegment1, ...}
     */
    originLines() {
        return this.coordLines();
    }

    /**
     * Gets the corners of the box
     * @returns {[Point]}
     */
    worldCorners() {
        const ctr = this.worldCenter();
        let corners = [];

        const sides = [-0.5, 0.5];
        const sz = this.worldSize();
        for(const i in sides) {
            for (const j in sides) {
                for (const k in sides) {
                    const s = [sides[k], sides[j], sides[i]];
                    const c = [];
                    for(let l = 0; l < 3; ++l) {
                        c.push(ctr.coords()[l] + s[l] * sz[l]);
                    }
                    corners.push(new SIREPO.GEOMETRY.Point(...c));
                }
            }
        }
        return corners;
    }

    /**
     * Gets the edges of the box in each dimension
     * @returns {{}} - mapping of dimension to the edges, e.g. {x: [LineSegment1, LineSegment2], ...}
     */
    worldEdges() {
        const c = this.worldCorners();
        const e = {};
        for (const dim in this.edgeCfg) {
            const cp = this.edgeCfg[dim].edgeCornerPairs;
            const lines = [];
            for (const j in cp) {
                const p = cp[j];
                lines.push(new SIREPO.GEOMETRY.LineSegment(c[p[0]], c[p[1]]));
            }
            e[dim] = lines;
        }
        return e;
    }

    /**
     * Gets the size of the box
     * @returns {[number]}
     */
    worldSize() {
        return [
            this.source.getXLength(),
            this.source.getYLength(),
            this.source.getZLength()
        ];
    }
}

SIREPO.app.factory('vtkPlotting', function(errorService, geometry, plotting, requestSender, utilities, $rootScope) {

    let self = {};
    let stlReaders = {};

    self.COORDINATE_PLANES = {
        'xy': [0, 0, 1],
        'yz': [1, 0, 0],
        'zx': [0, 1, 0],
    };

    self.addSTLReader = function(file, reader) {
        stlReaders[file] = reader;
    };

    self.adjustContainerSize = function(container, rect, ctrAspectRatio, thresholdPct) {
        const fsAspectRatio = window.screen.availWidth / window.screen.availHeight;

        container.height(container.width() / (utilities.isFullscreen() ? fsAspectRatio : ctrAspectRatio));

        const w = container.width();
        const h = container.height();
        return Math.abs(h - rect.height) > Math.max(thresholdPct * h, 1) ||
            Math.abs(w - rect.width) > Math.max(thresholdPct * w, 1);

    };

    self.coordMapper = function(transform) {

        // "Bundles" a source, mapper, and actor together
        function actorBundle(source) {
            var m = vtk.Rendering.Core.vtkMapper.newInstance();
            if (source) {
                m.setInputConnection(source.getOutputPort());
            }
            var a = vtk.Rendering.Core.vtkActor.newInstance({
                mapper: m
            });

            return {
                actor: a,
                source: source,
                mapper: m,
                setActor: function (actor) {
                    actor.setMapper(this.m);
                    this.actor = actor;
                },
                setMapper: function (mapper) {
                    this.mapper = mapper;
                    this.actor.setMapper(mapper);
                },
                setSource: function (source) {
                    this.mapper.setInputConnection(source.getOutputPort());
                    this.source = source;
                }
            };
        }

        return {

            xform: transform || geometry.transform(),

            buildActorBundle: function(source) {
                return actorBundle(source);
            },

            buildBox: function(labSize, labCenter) {
                var vsize = labSize ? this.xform.doTransform(labSize) :  [1, 1, 1];
                var cs = vtk.Filters.Sources.vtkCubeSource.newInstance({
                    xLength: vsize[0],
                    yLength: vsize[1],
                    zLength: vsize[2],
                    center: labCenter ? this.xform.doTransform(labCenter) :  [0, 0, 0]
                });
                var ab = actorBundle(cs);

                ab.setCenter = function (arr) {
                    ab.source.setCenter(arr);
                };
                ab.setLength = function (arr) {
                    ab.source.setXLength(arr[0]);
                    ab.source.setYLength(arr[1]);
                    ab.source.setZLength(arr[2]);
                };

                return ab;
            },

            // arbitrary vtk source, transformed
            buildFromSource: function(src) {
                // add transform
                return actorBundle(src);
            },

            buildPlane: function(labOrigin, labP1, labP2) {
                var src = vtk.Filters.Sources.vtkPlaneSource.newInstance();
                var b = actorBundle(src);
                if (labOrigin && labP1 && labP2) {
                    this.setPlane(b, labOrigin, labP1, labP2);
                }
                return b;
            },

            buildSphere: function(lcenter, radius, colorArray) {
                var ps = vtk.Filters.Sources.vtkSphereSource.newInstance({
                    center: lcenter ? this.xform.doTransform(lcenter) : [0, 0, 0],
                    radius: radius || 1,
                    thetaResolution: 16,
                    phiResolution: 16
                });

                var ab = actorBundle(ps);
                //ab.actor.getProperty().setColor(...(colorArray || [1, 1, 1]));
                var ca = colorArray || [1, 1, 1];
                ab.actor.getProperty().setColor(ca[0], ca[1], ca[2]);
                ab.actor.getProperty().setLighting(false);
                return ab;
            },

            buildSTL: function(file, callback) {
                var cm = this;
                var r = self.getSTLReader(file);

                if (r) {
                    setSTL(r);
                    return;
                }
                self.loadSTLFile(file).then(function (r) {
                    r.loadData()
                        .then(function (res) {
                            self.addSTLReader(file, r);
                            setSTL(r);
                        }, function (reason) {
                            throw new Error(file + ': Error loading data from .stl file: ' + reason);
                        }
                    ).catch(function (e) {
                        errorService.alertText(e);
                    });
                });

                function setSTL(r) {
                    var b = actorBundle(r);
                    var a = b.actor;
                    var userMatrix = [];
                    cm.xform.matrix.forEach(function (row) {
                        userMatrix = userMatrix.concat(row);
                        userMatrix.push(0);
                    });
                    userMatrix = userMatrix.concat([0, 0, 0, 1]);
                    a.setUserMatrix(userMatrix);
                    callback(b);
                }

            },

            setPlane: function(planeBundle, labOrigin, labP1, labP2) {
                var vo = labOrigin ? this.xform.doTransform(labOrigin) : [0, 0, 0];
                var vp1 = labP1 ? this.xform.doTransform(labP1) : [0, 0, 1];
                var vp2 = labP2 ? this.xform.doTransform(labP2) : [1, 0, 0];
                planeBundle.source.setOrigin(vo[0], vo[1], vo[2]);
                planeBundle.source.setPoint1(vp1[0], vp1[1], vp1[2]);
                planeBundle.source.setPoint2(vp2[0], vp2[1], vp2[2]);
            },

            userMatrix: function () {
                // Array.flat() doesn't exist in MS browsers
                // var m = transform.matrix.flat();
                var matrix = transform.matrix;
                var m = [];
                for (var i = 0; i < matrix.length; i++) {
                    for (var j = 0; j < matrix[i].length; j++) {
                        m.push(matrix[i][j]);
                    }
                }
                m.splice(3, 0, 0);
                m.splice(7, 0, 0);
                m.push(0);
                m.push (0, 0, 0, 1);
                return m;
            }
        };
    };

    self.getSTLReader = function(file) {
        return stlReaders[file];
    };

    self.isSTLUrlValid = function(url) {
        return self.loadSTLURL(url).then(function (r) {
            return ! ! r;
        });
    };

    self.loadSTLFile = function(file) {
        var fileName = file.name || file;

        var url = requestSender.formatUrl('downloadLibFile', {
            '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
            '<filename>': self.stlFileType + '.' + fileName,
        });
        return self.loadSTLURL(url).then(function (r) {
            return r;
        });
    };

    self.loadSTLURL = function(url) {
        var r = vtk.IO.Geometry.vtkSTLReader.newInstance();
        return r.setUrl(url)
            .then(function() {
                return r;
        }, function (err) {
            throw new Error(url + ': Invalid or missing .stl: ' +
            (err.xhr ? err.xhr.status + ' (' + err.xhr.statusText + ')' : err));
        })
            .catch(function (e) {
                $rootScope.$apply(function () {
                    errorService.alertText(e);
                });
            });
    };

    self.plotLine = function(id, name, line, color, alpha, strokeStyle, dashes) {
        var shape = plotting.plotLine(id, name, line, color, alpha, strokeStyle, dashes);
        return shape;
    };

    self.stlFileType = 'stl-file';

    self.addActors = function(renderer, actorArr) {
        actorArr.forEach(function(actor) {
            self.addActor(renderer, actor);
        });
    };

    self.addActor = function(renderer, actor) {
        if (! actor) {
            return;
        }
        renderer.addActor(actor);
    };

    self.removeActors = function(renderer, actorArr) {
        if (! actorArr) {
            renderer.getActors().forEach(function(actor) {
                renderer.removeActor(actor);
            });
            return;
        }
        actorArr.forEach(function(actor) {
            self.removeActor(renderer, actor);
        });
        actorArr.length = 0;
    };

    self.removeActor = function(renderer, actor) {
        if (! actor ) {
            return;
        }
        renderer.removeActor(actor);
    };

    self.showActors = function(renderWindow, arr, doShow, visibleOpacity, hiddenOpacity) {
        arr.forEach(function (a) {
            self.showActor(renderWindow, a, doShow, visibleOpacity, hiddenOpacity, true);
        });
        renderWindow.render();
    };

    self.showActor = function(renderWindow, a, doShow, visibleOpacity, hiddenOpacity, waitToRender) {
        a.getProperty().setOpacity(doShow ? visibleOpacity || 1.0 : hiddenOpacity || 0.0);
        if (! waitToRender) {
            renderWindow.render();
        }
    };

    return self;
});

SIREPO.app.directive('vtkAxes', function(geometry, layoutService, plotting) {
    return {
        restrict: 'A',
        scope: {
            axisCfg: '<',
            boundObj: '<',
            height: '<',
            width: '<',
        },
        template: `
            <svg class="sr-vtk-axes" data-ng-attr-width="{{ width }}" data-ng-attr-height="{{ height }}">
            <g class="vtk-axes">
                <g data-ng-repeat="dim in dimensions">
                    <g class="{{ dim }} axis"></g>
                    <text class="{{ dim }}-axis-label"></text>
                </g>
                <g data-ng-repeat="dim in dimensions">
                    <g class="{{ dim }}-axis-central" data-ng-if="axisCfg[dim].showCentral">
                        <line style="stroke: gray;" stroke-dasharray="5,5"
                          data-ng-attr-x1="{{ centralAxes[dim].x[0] }}"
                          data-ng-attr-y1="{{ centralAxes[dim].y[0] }}"
                          data-ng-attr-x2="{{ centralAxes[dim].x[1] }}"
                          data-ng-attr-y2="{{ centralAxes[dim].y[1] }}" />
                    </g>
                </g>
            </g>
            </svg>
        `,
        controller: function($scope, $element) {
            $scope.dimensions = geometry.basis;
            $scope.centralAxes = Object.fromEntries(
                $scope.dimensions.map(d => [d, { x: [-0.5, 0.5], y: [-0.5, 0.5] }]),
            );
            const axes = Object.fromEntries(
                $scope.dimensions.map(d => [d, layoutService.plotAxis({}, d, 'bottom', refresh)]),
            );
            let axisCfg, d3self;

            function axisSelector(dim, suffix) {
                return `.${dim}.axis${suffix || ''}`;
            }

            function computeEdgeStats(edge) {
                const slope = edge.slope();
                const screenDim = Number.isFinite(slope) && Math.abs(slope) < 3 ? 'x' : 'y';
                const sortedPts = SIREPO.GEOMETRY.GeometryUtils.sortInDimension(
                    edge.points,
                    screenDim,
                    false
                );
                let radAngle = Math.atan(slope);
                if (screenDim === 'y') {
                    radAngle -= Math.PI / 2;
                    if (radAngle < -Math.PI / 2) {
                        radAngle += Math.PI;
                    }
                }
                return {
                    reverseOnScreen: edge.points[1][screenDim] < edge.points[0][screenDim],
                    newRange: edge.length(),
                    isHorizontal: screenDim === 'x',
                    bottomOrLeft: isBottomOrLeft(screenDim, edge, sortedPts),
                    axis: {
                        left: sortedPts[0].x,
                        top: sortedPts[0].y,
                        right: sortedPts[1].x,
                        bottom: sortedPts[1].y,
                    },
                    radAngle: radAngle,
                    angle: SIREPO.GEOMETRY.GeometryUtils.toDegrees(radAngle),
                };
            }

            function init() {
                d3self = select();
                for (const dim in axes) {
                    axes[dim].init();
                    axes[dim].svgAxis.tickSize(0);
                }
            }

            function isBottomOrLeft(screenDim, edge, sortedPts) {
                // this places the axis tick labels on the appropriate side of the axis
                const outsideCorners = SIREPO.GEOMETRY.GeometryUtils.sortInDimension(
                    $scope.boundObj.viewPortCorners(),
                    screenDim === 'x' ? 'y' : 'x',
                    screenDim === 'x',
                );
                return outsideCorners[0].equals(sortedPts[0]) || outsideCorners[0].equals(sortedPts[1])
                    || outsideCorners[1].equals(sortedPts[0]) || outsideCorners[1].equals(sortedPts[1]);
            }

            function rebuildAxes() {
                for (const dim in axes) {
                    const cfg = axisCfg[dim];
                    axes[dim].scale.domain([cfg.min, cfg.max]);
                    axes[dim].parseLabelAndUnits(cfg.label);
                }
            }

            function refresh() {
                const screenRect = new SIREPO.GEOMETRY.Rect(
                    new SIREPO.GEOMETRY.Point(0, 0),
                    new SIREPO.GEOMETRY.Point($scope.width, $scope.height),
                );

                for (const dim in axes) {
                    updateCentralAxis(screenRect, dim);
                    const edge = geometry.bestEdgeInBounds(
                        $scope.boundObj.externalViewportEdgesForDimension(dim),
                        screenRect,
                    );
                    if (! edge) {
                        d3self.select(axisSelector(dim)).style('opacity', 0.0);
                        d3self.select(`.${dim}-axis-label`).style('opacity', 0.0);
                        continue;
                    }
                    const e = computeEdgeStats(edge);
                    updateAxis(dim, e);
                    updateAxisLabels(dim, e);
                }
            }

            function select(selector) {
                const e = d3.select($element[0]);
                return selector ? e.select(selector) : e;
            }

            function updateAxis(dim, e) {
                if (e.isHorizontal) {
                    axes[dim].svgAxis.orient(e.bottomOrLeft ? 'bottom' : 'top');
                }
                else {
                    axes[dim].svgAxis.orient(e.bottomOrLeft ? 'left' : 'right');
                }
                axes[dim].scale.range([e.reverseOnScreen ? e.newRange : 0, e.reverseOnScreen ? 0 : e.newRange]);
                axes[dim].updateLabelAndTicks({
                    width: e.newRange,
                    height: e.newRange
                }, select);

                d3self.select(axisSelector(dim)).attr(
                    'transform',
                    `translate(${e.axis.left}, ${e.axis.top}) rotate(${e.angle})`,
                );
            }

            function updateAxisLabels(dim, e) {
                // If an axis is shorter than this, don't display it -- the ticks will
                // be cramped and unreadable
                const minAxisDisplayLen = 75;

                // counter-rotate the tick labels
                d3self.selectAll(axisSelector(dim, ' text')).attr('transform', `rotate(${-e.angle})`);
                d3self.select(axisSelector(dim, ' .domain')).style({'stroke': 'none'});
                d3self.select(axisSelector(dim)).style('opacity', e.newRange < minAxisDisplayLen ? 0 : 1);

                const labelSpace = 3 * plotting.tickFontSize(d3self.select(axisSelector(dim, '-label')));
                const labelSpaceX = (e.isHorizontal ? Math.sin(e.radAngle) : Math.cos(e.radAngle)) * labelSpace;
                const labelSpaceY = (e.isHorizontal ? Math.cos(e.radAngle) : Math.sin(e.radAngle)) * labelSpace;
                const labelX = e.axis.left + (e.bottomOrLeft ? -1 : 1) * labelSpaceX + (e.axis.right - e.axis.left) / 2.0;
                const labelY = e.axis.top + (e.bottomOrLeft ? 1 : -1) * labelSpaceY + (e.axis.bottom - e.axis.top) / 2.0;
                d3self.select(`.${dim}-axis-label`)
                    .attr('x', labelX)
                    .attr('y', labelY)
                    .attr('transform', `rotate(${e.isHorizontal ? 0 : -90} ${labelX} ${labelY})`)
                    .style('opacity', e.newRange < minAxisDisplayLen ? 0 : 1);
            }

            function updateCentralAxis(screenRect, dim) {
                const cli = screenRect.boundaryIntersectionsWithSeg(
                    $scope.boundObj.originLines()[dim]
                );
                if (cli && cli.length === 2) {
                    $scope.centralAxes[dim].x = [cli[0].x, cli[1].x];
                    $scope.centralAxes[dim].y = [cli[0].y, cli[1].y];
                }
            }

            $scope.$on('axes.refresh', refresh);

            $scope.$watch('width', (width) => {
                if (width && axisCfg) {
                    refresh();
                }
            });

            $scope.$watch('axisCfg', (d) => {
                if (d && $scope.axisCfg) {
                    axisCfg = $scope.axisCfg;
                    rebuildAxes();
                    refresh();
                }
            }, true);

            init();
        },
    };
});

// General-purpose vtk display
SIREPO.app.directive('vtkDisplay', function(appState, utilities, $window) {

    return {
        restrict: 'A',
        scope: {
            axisCfg: '<',
            axisObj: '<',
            enableAxes: '=',
            enableSelection: '=',
            modelName: '@',
            resetDirection: '@',
            resetSide: '@',
        },
        templateUrl: '/static/html/vtk-display.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope, $element) {
            $scope.GeometryUtils = SIREPO.GEOMETRY.GeometryUtils;
            $scope.isOrtho = false;
            $scope.selection = null;
            const canvasHolder = $($element).find('.vtk-canvas-holder').eq(0);
            let isPointerUp = true;

            // supplement or override these event handlers
            const eventHandlers = {
                onpointerdown: function (evt) {
                    isPointerUp = false;
                },
                onpointermove: function (evt) {
                    if (isPointerUp) {
                        return;
                    }
                    $scope.vtkScene.viewSide = null;
                    utilities.debounce(refresh, 100)();
                },
                onpointerup: function (evt) {
                    isPointerUp = true;
                    refresh();
                },
                onwheel: utilities.debounce(refresh, 100),
            };

            function asyncRefresh() {
                $scope.$applyAsync(refresh);
            }

            function ondblclick() {
                $scope.vtkScene.resetView();
                refresh();
                $scope.$apply();
            }

            function refresh() {
                if ($scope.axisObj) {
                    $scope.$broadcast('axes.refresh', $scope.axisObj);
                }
            }

            $scope.canvasGeometry = function() {
                return {
                    pos: canvasHolder.position(),
                    size: {
                        width: Math.max(0, canvasHolder.width()),
                        height: Math.max(0, canvasHolder.height()),
                    }
                };
            };

            $scope.init = function() {
                const rw = canvasHolder[0];
                $scope.vtkScene = new VTKScene(rw, $scope.resetSide, $scope.resetDirection);
                // all listeners need to be cleaned up in $destroy
                rw.addEventListener('dblclick', ondblclick);
                for (const k in eventHandlers) {
                    const f = eventHandlers[k];
                    if (k == 'onpointermove') {
                        $('.sr-view-content')[0][k] = f;
                        continue;
                    }
                    rw[k] = f;
                }
                // remove global VTK key listeners
                for (const n of ['KeyPress', 'KeyDown', 'KeyUp']) {
                    document.removeEventListener(
                        n.toLowerCase(),
                        $scope.vtkScene.fsRenderer.getInteractor()[`handle${n}`],
                    );
                }
                $scope.$emit('vtk-init', $scope.vtkScene);
                refresh();
            };

            $scope.rotate = angle => {
                $scope.vtkScene.rotate(angle);
                refresh();
            };

            $scope.showSide = side => {
                $scope.vtkScene.showSide(side);
                refresh();
            };

            $scope.toggleOrtho = () => {
                $scope.isOrtho = ! $scope.isOrtho;
                $scope.vtkScene.cam.setParallelProjection($scope.isOrtho);
                $scope.vtkScene.render();
                refresh();
            };

            $scope.$on('$destroy', function() {
                const rw = canvasHolder[0];
                rw.removeEventListener('dblclick', ondblclick);
                for (const k in eventHandlers) {
                    if (k == 'onpointermove') {
                        $('.sr-view-content')[0][k] = null;
                        continue;
                    }
                    rw[k] = null;
                }
                $element.off();
                $($window).off('resize', asyncRefresh);
                $scope.vtkScene.teardown();
            });
            $scope.$on('vtk.selected', function (e, d) {
                $scope.$applyAsync(() => {
                    $scope.selection = d;
                });
            });
            $scope.$on('vtk.showLoader', function (e, d) {
                $scope.vtkScene.setBgColor('#dddddd');
                $($element).find('.vtk-load-indicator img').css('display', 'block');
            });
            $scope.$on('vtk.hideLoader', function (e, d) {
                $scope.vtkScene.setBgColor(appState.models[$scope.modelName].bgColor || '#ffffff');
                $($element).find('.vtk-load-indicator img').css('display', 'none');
            });
            $scope.$on('sr-window-resize', () => {
                // ensure full-screen and exit full-screen resize the renderer
                $scope.vtkScene.fsRenderer.resize();
                refresh();
            });

            $scope.init();
            // ensure the axes update on each resize event
            $($window).resize(asyncRefresh);
        },
    };
});

SIREPO.VTK = {
    CoordMapper: CoordMapper,
    CuboidViews: CuboidViews,
    CylinderViews: CylinderViews,
    ExtrudedPolyViews: ExtrudedPolyViews,
    RacetrackViews: RacetrackViews,
    SphereViews: SphereViews,
    ViewPortBox: ViewPortBox,
    VTKUtils: VTKUtils,
};
