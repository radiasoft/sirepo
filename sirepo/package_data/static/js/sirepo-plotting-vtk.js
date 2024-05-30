'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;
SIREPO.DEFAULT_COLOR_MAP = 'viridis';
SIREPO.ZERO_ARR = [0, 0, 0];
SIREPO.ZERO_STR = '0, 0, 0';

/**
 *
 */
class Elevation {

    static NAMES() {
        return {
            x: 'side',
            y: 'top',
            z: 'front',
        };
    }

    static PLANES() {
        return {
            x: 'yz',
            y: 'zx',
            z: 'xy',
        };
    }

    constructor(axis) {
        if (! SIREPO.GEOMETRY.GeometryUtils.BASIS().includes(axis)) {
            throw new Error('Invalid axis: ' + axis);
        }
        this.axis = axis;
        this.class = `.plot-viewport elevation-${axis}`;
        this.coordPlane = Elevation.PLANES()[this.axis];
        this.name = Elevation.NAMES()[axis];
        this.labDimensions = {
            x: {
                axis: this.coordPlane[0],
                axisIndex: SIREPO.GEOMETRY.GeometryUtils.axisIndex(this.coordPlane[0]),
            },
            y: {
                axis: this.coordPlane[1],
                axisIndex: SIREPO.GEOMETRY.GeometryUtils.axisIndex(this.coordPlane[1]),
            }
        };
    }

    labAxis(dim) {
        return this.labDimensions[dim].axis;
    }

    labAxes() {
        return [this.labAxis('x'), this.labAxis('y')];
    }

    labAxisIndex(dim) {
        return this.labDimensions[dim].axisIndex;
    }

    labAxisIndices() {
        return [this.labAxisIndex('x'), this.labAxisIndex('y')];
    }
}

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

    constructor(vectors, colorMapName='jet') {
        this.vectors = vectors;
        this.colorMapName = colorMapName;
        this.colorMap = SIREPO.PLOTTING.Utils.COLOR_MAP()[colorMapName];

        this.magnitudes = this.vectors.map(x => Math.hypot(...x));
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
        this.cam.setPosition(...position);
        this.cam.setFocalPoint(0, 0, 0);
        this.cam.setViewUp(...viewUp);
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
 * A bundle for a line source defined by two points
 */
class LineBundle extends ActorBundle {
    /**
     * @param {[number]} labP1 - 1st point
     * @param {[number]} labP2 - 2nd point
     * @param {SIREPO.GEOMETRY.Transform} transform - a Transform to translate between "lab" and "local" coordinate systems
     * @param {{}} actorProperties - a map of actor properties (e.g. 'color') to values
     */
    constructor(
        labP1 = [0, 0, 0],
        labP2 = [0, 0, 1],
        transform = new SIREPO.GEOMETRY.Transform(),
        actorProperties = {}
    ) {
        super(
            vtk.Filters.Sources.vtkLineSource.newInstance({
                point1: labP1,
                point2: labP2,
                resolution: 2
            }),
            transform,
            actorProperties
        );
    }
}

/**
 * A bundle for a plane source defined by three points
 */
class PlaneBundle extends ActorBundle {
    /**
     * @param {[number]} labOrigin - origin
     * @param {[number]} labP1 - 1st point
     * @param {[number]} labP2 - 2nd point
     * @param {SIREPO.GEOMETRY.Transform} transform - a Transform to translate between "lab" and "local" coordinate systems
     * @param {Object} actorProperties - a map of actor properties (e.g. 'color') to values
     */
    constructor(
        labOrigin = [0, 0, 0],
        labP1 = [1, 0, 0],
        labP2 = [0, 1, 0],
        transform = new SIREPO.GEOMETRY.Transform(),
        actorProperties = {}
    ) {
        super(vtk.Filters.Sources.vtkPlaneSource.newInstance(), transform, actorProperties);
        this.setPoints(labOrigin, labP1, labP2);
        this.setResolution();
    }

    /**
     * Set the defining points of the plane
     * @param {[number]} labOrigin - origin
     * @param {[number]} labP1 - 1st point
     * @param {[number]} labP2 - 2nd point
     */
    setPoints(labOrigin, labP1, labP2) {
        this.source.setOrigin(...this.transform.apply(new SIREPO.GEOMETRY.Matrix(labOrigin)).val);
        this.source.setPoint1(...this.transform.apply(new SIREPO.GEOMETRY.Matrix(labP1)).val);
        this.source.setPoint2(...this.transform.apply(new SIREPO.GEOMETRY.Matrix(labP2)).val);
    }

    /**
     * Set the resolution in each direction
     * @param {number} xRes - resolution (number of divisions) in the direction of the origin to p1
     * @param {number} yRes - resolution (number of divisions) in the direction of the origin to p2
     */
    setResolution(xRes = 1, yRes = 1) {
        this.source.setXResolution(xRes);
        this.source.setYResolution(yRes);
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
        this.formula = new VTKVectorFormula(vectors, colormapName);
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
     * Builds a line
     * @param {[number]} labP1 - 1st point
     * @param {[number]} labP2 - 2nd point
     * @param {Object} actorProperties - a map of actor properties (e.g. 'color') to values
     * @returns {LineBundle}
     */
    buildLine(labP1, labP2, actorProperties) {
        return new LineBundle(labP1, labP2, this.transform, actorProperties);
    }

    /**
     * Builds a plane
     * @param {[number]} labOrigin - origin
     * @param {[number]} labP1 - 1st point
     * @param {[number]} labP2 - 2nd point
     * @param {Object} actorProperties - a map of actor properties (e.g. 'color') to values
     * @returns {LineBundle}
     */
    buildPlane(labOrigin, labP1, labP2, actorProperties) {
        return new PlaneBundle(labOrigin, labP1, labP2, this.transform, actorProperties);
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
    buildVectorField(vectors, positions, scaleFactor=1.0, useTailAsOrigin=false, colormapName='jet', actorProperties={}) {
        return new VectorFieldBundle(vectors, positions, scaleFactor, useTailAsOrigin, colormapName, this.transform, actorProperties);
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

SIREPO.app.factory('vtkPlotting', function(appState, errorService, geometry, plotting, panelState, requestSender, utilities, $location, $rootScope, $timeout, $window) {

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

            buildLine: function(labP1, labP2, colorArray) {
                var vp1 = this.xform.doTransform(labP1);
                var vp2 = this.xform.doTransform(labP2);
                var ls = vtk.Filters.Sources.vtkLineSource.newInstance({
                    point1: [vp1[0], vp1[1], vp1[2]],
                    point2: [vp2[0], vp2[1], vp2[2]],
                    resolution: 2
                });

                var ab = actorBundle(ls);
                ab.actor.getProperty().setColor(colorArray[0], colorArray[1], colorArray[2]);
                return ab;
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

    self.buildSTL = (coordMapper, file, callback) => {
        let r = self.getSTLReader(file);
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
            const b = new ActorBundle(r, coordMapper.transform);
            let m = [];
            coordMapper.transform.matrix.val.forEach(x =>  {
                m = m.concat(x);
                m.push(0);
            });
            m = m.concat([0, 0, 0, 1]);
            b.actor.setUserMatrix(m);
            callback(b);
        }

    };

    self.clearSTLReaders = function() {
        stlReaders = {};
    };

    self.getSTLReader = function(file) {
        return stlReaders[file];
    };

    self.isSTLFileValid = function(file) {
        return self.loadSTLFile(file).then(function (r) {
            return ! ! r;
        });
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

    // create a 3d shape
    self.plotShape = function(id, name, center, size, color, alpha, fillStyle, strokeStyle, dashes, layoutShape, points) {
        var shape = plotting.plotShape(id, name, center, size, color, alpha, fillStyle, strokeStyle, dashes, layoutShape, points);
        shape.axes.push('z');
        shape.center.z = center[2];
        shape.size.z = size[2];
        return shape;
    };

    self.plotLine = function(id, name, line, color, alpha, strokeStyle, dashes) {
        var shape = plotting.plotLine(id, name, line, color, alpha, strokeStyle, dashes);
        return shape;
    };

    self.removeSTLReader = function(file) {
        if (stlReaders[file]) {
            delete stlReaders[file];
        }
    };

    self.cylinderSection = function(center, axis, radius, height, planes) {
        var startAxis = [0, 0, 1];
        var startOrigin = [0, 0, 0];
        var cylBounds = [-radius, radius, -radius, radius, -height/2.0, height/2.0];
        var cyl = vtk.Common.DataModel.vtkCylinder.newInstance({
            radius: radius,
            center: startOrigin,
            axis: startAxis
        });

        var pl = planes.map(function (p) {
            return vtk.Common.DataModel.vtkPlane.newInstance({
                normal: p.norm || startAxis,
                origin: p.origin || startOrigin
            });
        });

        // perform the sectioning
        var section = vtk.Common.DataModel.vtkImplicitBoolean.newInstance({
            operation: 'Intersection',
            functions: [cyl, pl[0], pl[1], pl[2], pl[3]]
        });

        var sectionSample = vtk.Imaging.Hybrid.vtkSampleFunction.newInstance({
            implicitFunction: section,
            modelBounds: cylBounds,
            sampleDimensions: [32, 32, 32]
        });

        var sectionSource = vtk.Filters.General.vtkImageMarchingCubes.newInstance();
        sectionSource.setInputConnection(sectionSample.getOutputPort());
        // this transformation adapted from VTK cylinder source - we don't "untranslate" because we want to
        // rotate in place, not around the global origin
        vtk.Common.Core.vtkMatrixBuilder
            .buildFromRadian()
            //.translate(...center)
            .translate(center[0], center[1], center[2])
            .rotateFromDirections(startAxis, axis)
            .apply(sectionSource.getOutputData().getPoints().getData());
       return sectionSource;
    };

    self.setColorScalars = function(data, color) {
        var pts = data.getPoints();
        var n = color.length * (pts.getData().length / pts.getNumberOfComponents());
        var pd = data.getPointData();
        var s = pd.getScalars();
        var rgb = s ? s.getData() : new window.Uint8Array(n);
        for (var i = 0; i < n; i += color.length) {
            for (var j = 0; j < color.length; ++j) {
                rgb[i + j] = color[j];
            }
        }
        pd.setScalars(
            vtk.Common.Core.vtkDataArray.newInstance({
                name: 'color',
                numberOfComponents: color.length,
                values: rgb,
            })
        );

        data.modified();
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

SIREPO.app.directive('stlFileChooser', function(validationService, vtkPlotting) {
    return {
        restrict: 'A',
        scope: {
            description: '=',
            url: '=',
            inputFile: '=',
            model: '=',
            require: '<',
            title: '@',
        },
        template: `
            <div data-file-chooser=""  data-url="url" data-input-file="inputFile" data-validator="validate" data-title="title" data-file-formats=".stl" data-description="description" data-require="require">
            </div>
        `,
        controller: function($scope) {
            $scope.validate = function (file) {
                $scope.url = URL.createObjectURL(file);
                return vtkPlotting.isSTLUrlValid($scope.url).then(function (ok) {
                    return ok;
                });
            };
            $scope.validationError = '';
        },
        link: function(scope, element, attrs) {

        },
    };
});

SIREPO.app.directive('stlImportDialog', function(appState, fileManager, fileUpload, vtkPlotting, requestSender) {
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
                        <div data-stl-file-chooser="" data-input-file="inputFile" data-url="fileURL" data-title="title" data-description="description" data-require="true"></div>
                          <div class="col-sm-6 pull-right">
                            <button data-ng-click="importStlFile(inputFile)" class="btn btn-primary" data-ng-class="{\'disabled\': isMissingImportFile() }">Import File</button>
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
            $scope.title = $scope.title || 'Import STL File';
            $scope.description = $scope.description || 'Select File';

            $scope.importStlFile = function(inputFile) {
                if (! inputFile) {
                    return;
                }
                newSimFromSTL(inputFile);
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
                        'uploadLibFile',
                        {
                            '<simulation_id>': simId,
                            '<simulation_type>': SIREPO.APP_SCHEMA.simulationType,
                            '<file_type>': vtkPlotting.stlFileType,
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

            function newSimFromSTL(inputFile) {
                var url = $scope.fileURL;
                var model = appState.setModelDefaults(appState.models.simulation, 'simulation');
                model.name = inputFile.name.substring(0, inputFile.name.indexOf('.'));
                model.folder = fileManager.getActiveFolderPath();
                model.conductorFile = inputFile.name;
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
    };});


// elevations tab + vtk tab (or all in 1 tab?)
// A lot of this is 2d and could be extracted
SIREPO.app.directive('3dBuilder', function(appState, geometry, layoutService, panelState, plotting, utilities) {
    return {
        restrict: 'A',
        scope: {
            cfg: '<',
            modelName: '@',
            source: '=controller',
        },
        templateUrl: '/static/html/3d-builder.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope) {
            const ASPECT_RATIO = 1.0;

            const ELEVATIONS = {};
            for (const axis of SIREPO.GEOMETRY.GeometryUtils.BASIS().slice().reverse()) {
                const e = new Elevation(axis);
                ELEVATIONS[e.name] = e;
            }

            // svg shapes
            const LAYOUT_SHAPES = ['circle', 'ellipse', 'line', 'path', 'polygon', 'polyline', 'rect'];

            const SCREEN_INFO = {
                x: {
                    length: $scope.width / 2
                },
                y: {
                    length: $scope.height / 2
                },
            };

            const fitDomainPct = 1.01;

            let screenRect = null;
            let selectedObject = null;
            const objectScale = SIREPO.APP_SCHEMA.constants.objectScale || 1.0;
            const invObjScale = 1.0 / objectScale;

            $scope.alignmentTools = SIREPO.APP_SCHEMA.constants.alignmentTools;
            $scope.elevations = ELEVATIONS;
            $scope.isClientOnly = true;
            $scope.margin = {top: 20, right: 20, bottom: 45, left: 70};
            $scope.settings = appState.models.threeDBuilder;
            $scope.snapGridSizes = appState.enumVals('SnapGridSize');
            $scope.width = $scope.height = 0;

            let didDrag = false;
            let dragShape, dragInitialShape, zoom;
            const dragDelta = {x: 0, y: 0};
            let draggedShape = null;
            const axisScale = {
                x: 1.0,
                y: 1.0,
                z: 1.0
            };
            const axes = {
                x: layoutService.plotAxis($scope.margin, 'x', 'bottom', refresh),
                y: layoutService.plotAxis($scope.margin, 'y', 'left', refresh),
            };

            const snapSettingsFields = [
                'threeDBuilder.snapToGrid',
                'threeDBuilder.snapGridSize',
            ];
            const settingsFields = [
                'threeDBuilder.autoFit',
                'threeDBuilder.elevation',
            ].concat(snapSettingsFields);

            function clearDragShadow() {
                d3.selectAll('.vtk-object-layout-drag-shadow').remove();
            }

            function getElevation() {
                return ELEVATIONS[$scope.settings.elevation];
            }

            function getLabAxis(dim) {
                return getElevation().labAxis(dim);
            }

            function resetDrag() {
                didDrag = false;
                hideShapeLocation();
                dragDelta.x = 0;
                dragDelta.y = 0;
                draggedShape = null;
                selectedObject = null;
            }

            function d3DragShapeEnd(shape) {

                function reset() {
                    resetDrag();
                    d3.select(`.plot-viewport ${shapeSelectionId(shape, true)}`).call(updateShapeAttributes);
                }

                const dragThreshold = 1e-3;
                if (! didDrag || Math.abs(dragDelta.x) < dragThreshold && Math.abs(dragDelta.y) < dragThreshold) {
                    reset();
                    return;
                }
                $scope.$applyAsync(() => {
                    if (isShapeInBounds(shape)) {
                        const o = $scope.source.getObject(shape.id);
                        if (! o) {
                            reset();
                            return;
                        }
                        const e = getElevation();
                        for (const dim of SIREPO.SCREEN_DIMS) {
                            o.center[SIREPO.GEOMETRY.GeometryUtils.axisIndex(e.labAxis(dim))] = invObjScale * shape.center[dim];
                        }
                        $scope.source.saveObject(shape.id, reset);
                    }
                    else {
                        appState.cancelChanges($scope.modelName);
                        reset();
                    }
                });
            }

            function canDrag(dim) {
                const a = d3.event.sourceEvent.shiftKey ?
                    (Math.abs(dragDelta.x) > Math.abs(dragDelta.y) ? 'x' : 'y') :
                    null;
                return ! a || a === dim;
            }

            function d3DragShape(shape) {

                if (! shape.draggable) {
                    return;
                }
                didDrag = true;
                draggedShape = shape;
                SIREPO.SCREEN_DIMS.forEach(dim => {
                    if (appState.models.threeDBuilder.snapToGrid) {
                        dragDelta[dim] = snap(shape, dim);
                        return;
                    }
                    dragDelta[dim] = canDrag(dim) ? d3.event[dim] : 0;
                    const numPixels = scaledPixels(dim, dragDelta[dim]);
                    shape[dim] = dragInitialShape[dim] + numPixels;
                    shape.center[dim] = dragInitialShape.center[dim] + numPixels;
                });
                d3.select(shapeSelectionId(shape)).call(updateShapeAttributes);
                showShapeLocation(shape);
                //TODO(mvk): restore live update of virtual shapes
                shape.runLinks().forEach(linkedShape => {
                    d3.select(shapeSelectionId(linkedShape)).call(updateShapeAttributes);
                });
            }

            function shapeSelectionId(shape, includeHash=true) {
                return `${(includeHash ? '#' : '')}shape-${shape.id}`;
            }

            function d3DragShapeStart(shape) {
                d3.event.sourceEvent.stopPropagation();
                dragInitialShape = appState.clone(shape);
                showShapeLocation(shape);
            }

            function drawObjects(elevation) {
                const shapes = $scope.source.getShapes(elevation);

                // need to split the shapes up by type or the data will get mismatched
                let layouts = {};
                LAYOUT_SHAPES.forEach(l=> {
                    layouts[l] = shapes
                        .filter(s => s.layoutShape === l)
                        .sort((s1, s2) => s2.z - s1.z)
                        .sort((s1, s2) => s1.draggable - s2.draggable);
                });

                for (let l in layouts) {
                    let ds = d3.select('.plot-viewport').selectAll(`${l}.vtk-object-layout-shape`)
                        .data(layouts[l]);
                    ds.exit().remove();
                    // function must return a DOM object in the SVG namespace
                    ds.enter()
                        .append(d => {
                            return document.createElementNS('http://www.w3.org/2000/svg', d.layoutShape);
                        })
                        .on('dblclick', editObject)
                        .on('dblclick.zoom', null)
                        .on('click', null);
                    ds.call(updateShapeAttributes);
                    ds.call(dragShape);
                }
            }

            function drawShapes() {
                drawObjects(getElevation());
            }

            function editObject(shape) {
                d3.event.stopPropagation();
                if (! shape.draggable) {
                    return;
                }
                $scope.$applyAsync(function() {
                    $scope.source.editObjectWithId(shape.id);
                });
            }

            function formatObjectLength(val) {
                return utilities.roundToPlaces(invObjScale * val, 4);
            }

            function getShape(id) {
                return $scope.shapes.filter(x => x.id === id)[0];
            }

            function hideShapeLocation() {
                select('.focus-text').text('');
            }

            function isMouseInBounds(evt) {
                d3.event = evt.event;
                var p = d3.mouse(d3.select('.plot-viewport').node());
                d3.event = null;
                return p[0] >= 0 && p[0] < $scope.width && p[1] >= 0 && p[1] < $scope.height
                     ? p
                     : null;
            }

            function isShapeInBounds(shape) {
                if (! $scope.cfg.fixedDomain) {
                    return true;
                }
                /*
                var vAxis = shape.elev === ELEVATIONS.front ? axes.y : axes.z;
                var bounds = {
                    top: shape.y,
                    bottom: shape.y - shape.height,
                    left: shape.x,
                    right: shape.x + shape.width,
                };
                if (bounds.right < axes.x.domain[0] || bounds.left > axes.x.domain[1]
                    || bounds.top < vAxis.domain[0] || bounds.bottom > vAxis.domain[1]) {
                    return false;
                }

                 */
                return true;
            }

            function refresh() {
                if (! axes.x.domain) {
                    return;
                }
                if (layoutService.plotAxis.allowUpdates) {
                    var elementWidth = parseInt(select('.workspace').style('width'));
                    if (isNaN(elementWidth)) {
                        return;
                    }
                    [$scope.height, $scope.width] = plotting.constrainFullscreenSize($scope, elementWidth, ASPECT_RATIO);
                    SCREEN_INFO.x.length = $scope.width;
                    SCREEN_INFO.y.length = $scope.height;

                    select('svg')
                        .attr('width', $scope.width + $scope.margin.left + $scope.margin.right)
                        .attr('height', $scope.plotHeight());
                    axes.x.scale.range([0, $scope.width]);
                    axes.y.scale.range([$scope.height, 0]);
                    axes.x.grid.tickSize(-$scope.height);
                    axes.y.grid.tickSize(-$scope.width);
                }
                if (plotting.trimDomain(axes.x.scale, axes.x.domain)) {
                    select('.overlay').attr('class', 'overlay mouse-zoom');
                    axes.y.scale.domain(axes.y.domain);
                }
                else {
                    select('.overlay').attr('class', 'overlay mouse-move-ew');
                }

                resetZoom();
                select('.plot-viewport').call(zoom);
                $.each(axes, function(dim, axis) {
                    var d = axes[dim].scale.domain();
                    var r = axes[dim].scale.range();
                    axisScale[dim] = Math.abs((d[1] - d[0]) / (r[1] - r[0]));

                    axis.updateLabelAndTicks({
                        width: $scope.width,
                        height: $scope.height,
                    }, select);
                    axis.grid.ticks(
                        $scope.settings.snapToGrid ?
                            Math.round(Math.abs(d[1] - d[0]) / ($scope.settings.snapGridSize * objectScale)) :
                            axis.tickCount
                    );
                    select('.' + dim + '.axis.grid').call(axis.grid);
                });

                screenRect = geometry.rect(
                    geometry.point(),
                    geometry.point($scope.width, $scope.height, 0)
                );

                drawShapes();
            }

            function replot(doFit=false) {
                const b = $scope.source.shapeBounds(getElevation());
                const newDomain = $scope.cfg.initDomian;
                SIREPO.SCREEN_DIMS.forEach(dim => {
                    const axis = axes[dim];
                    const bd = b[dim];
                    const nd = newDomain[dim];
                    axis.domain = $scope.cfg.fullZoom ? [-Infinity, Infinity] : nd;
                    if (($scope.settings.autoFit || doFit)  && bd[0] !== bd[1]) {
                        nd[0] = fitDomainPct * bd[0];
                        nd[1] = fitDomainPct * bd[1];
                        // center
                        const d = (nd[1] - nd[0]) / 2 - (bd[1] - bd[0]) / 2;
                        nd[0] -= d;
                        nd[1] -= d;
                    }
                    axis.scale.domain(newDomain[dim]);
                });
                $scope.resize();
            }

            function resetZoom() {
                zoom = axes.x.createZoom().y(axes.y.scale);
            }

            function scaledPixels(dim, pixels) {
                const dom = axes[dim].scale.domain();
                return pixels * SIREPO.SCREEN_INFO[dim].direction * (dom[1] - dom[0]) / SCREEN_INFO[dim].length;
            }

            function select(selector) {
                var e = d3.select($scope.element);
                return selector ? e.select(selector) : e;
            }

            function selectObject(d) {
                //TODO(mvk): allow using shift to select more than one (for alignment etc.)
                if (! selectedObject || selectedObject.id !== d.id ) {
                    selectedObject = d;
                }
                else {
                    selectedObject = null;
                }
            }

            function shapeColor(hexColor, alpha) {
                var comp = plotting.colorsFromHexString(hexColor);
                return 'rgb(' + comp[0] + ', ' + comp[1] + ', ' + comp[2] + ', ' + (alpha || 1.0) + ')';
            }

            function showShapeLocation(shape) {
                select('.focus-text').text(
                    'Center: ' +
                    formatObjectLength(shape.center.x) + ', ' +
                    formatObjectLength(shape.center.y) + ', ' +
                    formatObjectLength(shape.center.z)
                );
            }

            function snap(shape, dim) {
                function roundUnits(val, unit) {
                    return unit * Math.round(val / unit);
                }

                if (! canDrag(dim)) {
                    return 0;
                }

                const g = parseFloat($scope.settings.snapGridSize) * objectScale;
                const ctr = dragInitialShape.center[dim];
                const offset = axes[dim].scale(roundUnits(ctr, g)) - axes[dim].scale(ctr);
                const gridSpacing = Math.abs(axes[dim].scale(2 * g) - axes[dim].scale(g));
                const gridUnits = roundUnits(d3.event[dim], gridSpacing);
                const numPixels = scaledPixels(dim, gridUnits + offset);
                shape[dim] = roundUnits(dragInitialShape[dim] + numPixels, g);
                shape.center[dim] = roundUnits(ctr + numPixels, g);
                return Math.round(gridUnits + offset);
            }

            // called when dragging a new object, not an existing object
            function updateDragShadow(o, p) {
                let r = d3.select('.plot-viewport rect.vtk-object-layout-drag-shadow');
                if (r.empty()) {
                    const s = $scope.source.viewShadow(o).getView(getElevation());
                    r = d3.select('.plot-viewport').append('rect')
                        .attr('class', 'vtk-object-layout-shape vtk-object-layout-drag-shadow')
                        .attr('width', shapeSize(s, 'x'))
                        .attr('height', shapeSize(s, 'y'));
                }
                //showShapeLocation(shape);
                r.attr('x', p[0]).attr('y', p[1]);
            }

            function shapeOrigin(shape, dim) {
                return axes[dim].scale(
                    shape.center[dim] - SIREPO.SCREEN_INFO[dim].direction * shape.size[dim] / 2
                );
            }

            function shapePoints(shape) {
                //TODO(mvk): apply transforms to dx, dy
                const [dx, dy] = shape.id === (draggedShape || {}).id ? [dragDelta.x, dragDelta.y] : [0, 0];
                let pts = '';
                for (const p of shape.points) {
                    pts += `${dx + axes.x.scale(p.x)},${dy + axes.y.scale(p.y)} `;
                }
                return pts;
            }

            function linePoints(shape) {
                if (! shape.line || getElevation().coordPlane !== shape.coordPlane) {
                    return null;
                }

                const lp = shape.line.points;
                const labX = getElevation().labAxis('x');
                const labY = getElevation().labAxis('y');

                // same points in this coord plane
                if (lp[0][labX] === lp[1][labX] && lp[0][labY] === lp[1][labY]) {
                    return null;
                }

                var scaledLine = geometry.lineFromArr(
                    lp.map(function (p) {
                        var sp = [];
                        SIREPO.SCREEN_DIMS.forEach(function (dim) {
                            sp.push(axes[dim].scale(p[getElevation().labAxis(dim)]));
                        });
                        return geometry.pointFromArr(sp);
                }));

                var pts = screenRect.boundaryIntersectionsWithLine(scaledLine);
                return pts;
            }

            function shapeSize(shape, dim) {
                let c = shape.center[dim] || 0;
                let s = shape.size[dim] || 0;
                return Math.abs(axes[dim].scale(c + s / 2) - axes[dim].scale(c - s / 2));
            }

            //TODO(mvk): set only those attributes that pertain to each svg shape
            function updateShapeAttributes(selection) {
                selection
                    .attr('class', 'vtk-object-layout-shape')
                    .classed('vtk-object-layout-shape-selected', d => d.id === (selectedObject || {}).id)
                    .classed('vtk-object-layout-shape-undraggable', d => ! d.draggable)
                    .attr('id', d =>  shapeSelectionId(d, false))
                    .attr('href', d => d.href ? `#${d.href}` : '')
                    .attr('points', d => $.isEmptyObject(d.points || {}) ? null : shapePoints(d))
                    .attr('x', d => shapeOrigin(d, 'x') - (d.outlineOffset || 0))
                    .attr('y', d => shapeOrigin(d, 'y') - (d.outlineOffset || 0))
                    .attr('x1', d => {
                        const pts = linePoints(d);
                        return pts ? (pts[0] ? pts[0].coords()[0] : 0) : 0;
                    })
                    .attr('x2', d => {
                        const pts = linePoints(d);
                        return pts ? (pts[1] ? pts[1].coords()[0] : 0) : 0;
                    })
                    .attr('y1', d => {
                        const pts = linePoints(d);
                        return pts ? (pts[0] ? pts[0].coords()[1] : 0) : 0;
                    })
                    .attr('y2', d => {
                        const pts = linePoints(d);
                        return pts ? (pts[1] ? pts[1].coords()[1] : 0) : 0;
                    })
                    .attr('marker-end', d => {
                        if (d.endMark && d.endMark.length) {
                            return `url(#${d.endMark})`;
                        }
                    })
                    .attr('marker-start', d => {
                        if (d.endMark && d.endMark.length) {
                            return `url(#${d.endMark})`;
                        }
                    })
                    .attr('width', d => shapeSize(d, 'x') + 2 * (d.outlineOffset || 0))
                    .attr('height', d => shapeSize(d, 'y') + 2 * (d.outlineOffset || 0))
                    .attr('style', d => {
                        if (d.color) {
                            const a = d.alpha === 0 ? 0 : (d.alpha || 1.0);
                            const fill = `fill:${(d.fillStyle ? shapeColor(d.color, a) : 'none')}`;
                            return `${fill}; stroke: ${shapeColor(d.color)}; stroke-width: ${d.strokeWidth || 1.0}`;
                        }
                    })
                    .attr('stroke-dasharray', d => d.strokeStyle === 'dashed' ? (d.dashes || "5,5") : "");
                let tooltip = selection.select('title');
                if (tooltip.empty()) {
                    tooltip = selection.append('title');
                }
                tooltip.text(function(d) {
                    const ctr = d.getCenterCoords().map(function (c) {
                        return utilities.roundToPlaces(c * invObjScale, 2);
                    });
                    const sz = d.getSizeCoords().map(function (c) {
                        return utilities.roundToPlaces(c * invObjScale, 2);
                    });
                    return `${d.name} center : ${ctr} size: ${sz}`;
                });
            }

            $scope.destroy = () => {
                if (zoom) {
                    zoom.on('zoom', null);
                }
                $('.plot-viewport').off();
            };

            $scope.dragMove = (o, evt) => {
                const p = isMouseInBounds(evt);
                if (p) {
                    d3.select('.sr-drag-clone').attr('class', 'sr-drag-clone sr-drag-clone-hidden');
                    updateDragShadow(o, p);
                }
                else {
                    clearDragShadow();
                    d3.select('.sr-drag-clone').attr('class', 'sr-drag-clone');
                    hideShapeLocation();
                }
            };

            // called when dropping new objects, not existing
            $scope.dropSuccess = (o, evt) => {
                clearDragShadow();
                const p = isMouseInBounds(evt);
                if (p) {
                    const labXIdx = geometry.basis.indexOf(getLabAxis('x'));
                    const labYIdx = geometry.basis.indexOf(getLabAxis('y'));
                    const ctr = [0, 0, 0];
                    ctr[labXIdx] = axes.x.scale.invert(p[0]);
                    ctr[labYIdx] = axes.y.scale.invert(p[1]);
                    o.center = ctr.map(x => x * invObjScale);
                    $scope.$emit('layout.object.dropped', o);
                    drawShapes();
                }
            };

            $scope.editObject = $scope.source.editObject;

            $scope.fitToShapes = () => {
                replot(true);
            };

            $scope.getElevation = getElevation;

            $scope.getObjects = () => {
                return (appState.models[$scope.modelName] || {}).objects;
            };

            $scope.init = () => {
                $scope.shapes = $scope.source.getShapes(getElevation());

                $scope.$on($scope.modelName + '.changed', function(e, name) {
                    $scope.shapes = $scope.source.getShapes();
                    drawShapes();
                    replot();
                });

                select('svg').attr('height', plotting.initialHeight($scope));

                $.each(axes, function(dim, axis) {
                    axis.init();
                    axis.grid = axis.createAxis();
                });
                resetZoom();
                dragShape = d3.behavior.drag()
                    .origin(function(d) { return d; })
                    .on('drag', d3DragShape)
                    .on('dragstart', d3DragShapeStart)
                    .on('dragend', d3DragShapeEnd);
                SIREPO.SCREEN_DIMS.forEach(dim => {
                    axes[dim].parseLabelAndUnits(`${getLabAxis(dim)} [m]`);
                });
                replot();
            };

            $scope.isDropEnabled = () => $scope.source.isDropEnabled();

            $scope.plotHeight = () => $scope.plotOffset() + $scope.margin.top + $scope.margin.bottom;

            $scope.plotOffset = () => $scope.height;

            $scope.resize = () => {
                if (select().empty()) {
                    return;
                }
                refresh();
            };

            $scope.setElevation = elev => {
                $scope.settings.elevation = elev;
                SIREPO.SCREEN_DIMS.forEach(dim => {
                    axes[dim].parseLabelAndUnits(`${getLabAxis(dim)} [m]`);
                });
                replot();
            };

            appState.watchModelFields($scope, settingsFields, () => {
                appState.saveChanges('threeDBuilder');
            });
            appState.watchModelFields($scope, snapSettingsFields, refresh);

            $scope.$on('shapes.loaded', drawShapes);

            $scope.$on('shape.locked', (e, locks) => {
                let doRefresh = false;
                for (const l of locks) {
                    const s = getShape(l.id);
                    if (s) {
                        doRefresh = true;
                        s.draggable = ! l.doLock;
                    }
                }
                if (doRefresh) {
                    refresh();
                }
            });

        },
        link: function link(scope, element) {
            plotting.linkPlot(scope, element);
        },
    };
});

SIREPO.app.directive('objectTable', function(appState, $rootScope) {
    return {
        restrict: 'A',
        scope: {
            elevation: '=',
            modelName: '@',
            overlayButtons: '=',
            source: '=',
        },
        template: `
          <div class="panel panel-info">
            <div class="panel-heading"><span class="sr-panel-heading">Objects</span></div>
            <div class="panel-body">
            <form name="form">
              <table data-ng-show="getObjects().length" style="width: 100%;  table-layout: fixed" class="table table-striped table-condensed radia-table-dialog">
                <thead></thead>
                  <tbody>
                    <tr data-ng-show="areAllGroupsExpanded(o)" data-ng-attr-id="{{ o.id }}" data-ng-repeat="o in getObjects() track by $index">
                      <td style="padding-left: {{ nestLevel(o) }}em; cursor: pointer; white-space: nowrap">
                        <img alt="{{ lockTitle(o) }}" title="{{ lockTitle(o) }}" data-ng-src="/static/svg/lock.svg" data-ng-show="locked[o.id]" data-ng-class="{'sr-disabled-image': ! unlockable[o.id]}" style="padding-left: 1px;"  data-ng-disabled="! unlockable[o.id]" data-ng-click="toggleLock(o)">
                        <img alt="{{ lockTitle(o) }}" title="{{ lockTitle(o) }}" data-ng-src="/static/svg/unlock.svg" data-ng-show="! locked[o.id]" style="padding-left: 1px;"  data-ng-disabled="! unlockable[o.id]" data-ng-click="toggleLock(o)">
                        <span style="font-size: large; color: {{o.color || '#cccccc'}}; padding-left: 1px;">■</span>
                        <span data-ng-if="isGroup(o)" class="glyphicon" data-ng-class="{'glyphicon-chevron-up': expanded[o.id], 'glyphicon-chevron-down': ! expanded[o.id]}"  data-ng-click="toggleExpand(o)"></span>
                        <span>{{ o.name }}</span>
                      </td>
                        <td style="text-align: right">
                          <div class="sr-button-bar-parent">
                            <div class="sr-button-bar sr-button-bar-active">
                               <button data-ng-disabled="isAlignDisabled(o)" type="button" class="dropdown-toggle btn sr-button-action btn-xs" title="align" data-toggle="dropdown"><span class="glyphicon glyphicon-move"></span></button>
                               <ul class="dropdown-menu">
                                 <div class="container col-sm-8">
                                   <div class="row">
                                     <li style="display: inline-block">
                                        <span class="sr-button-bar-parent">
                                          <button data-ng-repeat="t in overlayButtons" title="{{ t.title }}" data-ng-click="align(o, t.type)"><img alt="{{ t.title }}" data-ng-src="/static/svg/{{ t.type }}.svg" width="24px" height="24px"></button>
                                        </span>
                                      </li>
                                   <div>
                                 <div>
                               </ul>
                               <button type="button" class="btn sr-button-action btn-xs" data-ng-disabled="isMoveDisabled(-1, o)" data-ng-click="moveObject(-1, o)" title="move up"><span class="glyphicon glyphicon-arrow-up"></span></button>
                               <button type="button" class="btn sr-button-action btn-xs" data-ng-disabled="isMoveDisabled(1, o)" data-ng-click="moveObject(1, o)" title="move down"><span class="glyphicon glyphicon-arrow-down"></span></button>
                               <button data-ng-disabled="isGroup(o) || locked[o.id]" type="button" class="btn sr-button-action btn-xs" data-ng-click="copyObject(o)" title="copy"><span class="glyphicon glyphicon-duplicate"></span></button>
                               <button data-ng-disabled="locked[o.id]" data-ng-click="editObject(o)" type="button" class="btn sr-button-action btn-xs" title="edit"><span class="glyphicon glyphicon-pencil"></span></button>
                               <button data-ng-disabled="locked[o.id]" data-ng-click="deleteObject(o)" type="button" class="btn btn-danger btn-xs" title="delete"><span class="glyphicon glyphicon-remove"></span></button>
                            </div>
                          </div>
                        </td>
                    </tr>
                  </tbody>
                </table>
            </div>
          </div>
          <div data-buttons="" data-model-name="modelName" data-fields="fields"></div>
          </form>
        `,
        controller: function($scope) {
            $scope.expanded = {};
            $scope.fields = ['objects'];
            $scope.locked = {};
            $scope.unlockable = {};

            const isInGroup = $scope.source.isInGroup;
            const getGroup = $scope.source.getGroup;
            const getMemberObjects = $scope.source.getMemberObjects;
            let areObjectsUnlockable = appState.models.simulation.areObjectsUnlockable;

            function arrange(objects) {

                const arranged = [];

                function addGroup(o) {
                    const p = getGroup(o);
                    if (p && ! arranged.includes(p)) {
                        return;
                    }
                    if (! arranged.includes(o)) {
                        arranged.push(o);
                    }
                    for (const m of getMemberObjects(o)) {
                        if ($scope.isGroup(m)) {
                            addGroup(m);
                        }
                        else {
                            arranged.push(m);
                        }
                    }
                }

                for (const o of objects) {
                    if (arranged.includes(o)) {
                        continue;
                    }
                    if (! isInGroup(o)) {
                        arranged.push(o);
                    }
                    if ($scope.isGroup(o)) {
                        addGroup(o);
                    }
                }
                return arranged;
            }

            function init() {
                if (areObjectsUnlockable === undefined) {
                    areObjectsUnlockable = true;
                }
                for (const o of $scope.getObjects()) {
                    $scope.expanded[o.id] = true;
                    $scope.unlockable[o.id] = areObjectsUnlockable;
                    $scope.locked[o.id] = ! areObjectsUnlockable;

                }
            }

            function setLocked(o, doLock) {
                $scope.locked[o.id] =  doLock;
                let ids = [
                    {
                        id: o.id,
                        doLock: doLock
                    },
                ];
                if ($scope.isGroup(o)) {
                    getMemberObjects(o).forEach(x => {
                        ids = ids.concat(setLocked(x, doLock));
                        if (areObjectsUnlockable) {
                            $scope.unlockable[x.id] = ! doLock;
                        }
                    });
                }
                return ids;
            }

            $scope.align = (o, alignType) => {
                $scope.source.align(o, alignType, $scope.elevation.labAxisIndices());
            };

            $scope.areAllGroupsExpanded = o => {
                if (! isInGroup(o)) {
                    return true;
                }
                const p = getGroup(o);
                if (! $scope.expanded[p.id]) {
                    return false;
                }
                return $scope.areAllGroupsExpanded(p);
            };

            $scope.copyObject = $scope.source.copyObject;

            $scope.deleteObject = $scope.source.deleteObject;

            $scope.editObject = $scope.source.editObject;

            $scope.getObjects = () => {
                return arrange((appState.models[$scope.modelName] || {}).objects);
            };

            $scope.isAlignDisabled = o => $scope.locked[o.id] || ! $scope.isGroup(o) || getMemberObjects(o).length < 2;

            $scope.isGroup = $scope.source.isGroup;

            $scope.isMoveDisabled = (direction, o) => {
                if ($scope.locked[o.id]) {
                    return true;
                }
                const objects = isInGroup(o) ?
                    getMemberObjects(getGroup(o)) :
                    $scope.getObjects().filter(x => ! isInGroup(x));
                let i = objects.indexOf(o);
                return direction === -1 ? i === 0 : i === objects.length - 1;
            };

            $scope.lockTitle = o => {
                if (! areObjectsUnlockable) {
                    return 'designer is read-only for this magnet';
                }
                if (! $scope.unlockable[o.id]) {
                    return 'cannot unlock';
                }
                return `click to ${$scope.locked[o.id] ? 'unlock' : 'lock'}`;
            };

            $scope.moveObject = $scope.source.moveObject;

            $scope.nestLevel = o => {
                let n = 0;
                if (isInGroup(o)) {
                    n += (1 + $scope.nestLevel(getGroup(o)));
                }
                return n;
            };

            $scope.toggleExpand = o => {
                $scope.expanded[o.id] = ! $scope.expanded[o.id];
            };

            $scope.toggleLock = o => {
                if (! $scope.unlockable[o.id]) {
                    return;
                }
                $rootScope.$broadcast('shape.locked', setLocked(o, ! $scope.locked[o.id]));
            };

            init();
        },
    };
});

SIREPO.app.directive('vtkAxes', function(appState, frameCache, panelState, requestSender, plotting, vtkAxisService, vtkPlotting, layoutService, utilities, geometry) {
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
                <g data-ng-repeat="dim in geometry.basis">
                    <g class="{{ dim }} axis"></g>
                    <text class="{{ dim }}-axis-label"></text>
                    <text class="{{ dim }} axis-end low"></text>
                    <text class="{{ dim }} axis-end high"></text>
                </g>
                <g data-ng-repeat="dim in geometry.basis">
                    <g class="{{ dim }}-axis-central" data-ng-if="axisCfg[dim].showCentral">
                        <line style="stroke: gray;" stroke-dasharray="5,5" data-ng-attr-x1="{{ centralAxes[dim].x[0] }}" data-ng-attr-y1="{{ centralAxes[dim].y[0] }}" data-ng-attr-x2="{{ centralAxes[dim].x[1] }}" data-ng-attr-y2="{{ centralAxes[dim].y[1] }}" />
                    </g>
                </g>
            </g>
            </svg>
        `,
        controller: function($scope, $element) {
            $scope.axesMargins = {
                x: { width: 16.0, height: 0.0 },
                y: { width: 0.0, height: 16.0 }
            };
            $scope.centralAxes = {
                x: { x: [-0.5, 0.5], y: [-0.5, 0.5] },
                y: { x: [-0.5, 0.5], y: [-0.5, 0.5] },
                z: { x: [-0.5, 0.5], y: [-0.5, 0.5] },
            };
            $scope.geometry = geometry;
            $scope.margin = {top: 50, right: 23, bottom: 50, left: 75};

            $scope.isDegenerate = function(dim) {
                return $scope.centralAxes[dim].x[0] === $scope.centralAxes[dim].x[1] &&
                    $scope.centralAxes[dim].y[0] === $scope.centralAxes[dim].y[1];
            };

            var axes = {
                x: layoutService.plotAxis($scope.margin, 'x', 'bottom', refresh, utilities),
                y: layoutService.plotAxis($scope.margin, 'y', 'bottom', refresh, utilities),
                z: layoutService.plotAxis($scope.margin, 'z', 'left', refresh, utilities)
            };

            var axisCfgDefault = {};
            geometry.basis.forEach(function (dim) {
                axisCfgDefault[dim] = {};
                axisCfgDefault[dim].color = '#ff0000';
                axisCfgDefault[dim].dimLabel = dim;
                axisCfgDefault[dim].label = dim;
                axisCfgDefault[dim].max = -0.5;
                axisCfgDefault[dim].min = 0.5;
                axisCfgDefault[dim].numPoints = 10;
                axisCfgDefault[dim].screenDim = dim === 'z' ? 'y' : 'x';
                axisCfgDefault[dim].showCentral = false;
            });

            var axisCfg = axisCfgDefault;

            var d3self = select();
            var lastSize = null;

            function select(selector) {
                var e = d3.select($element[0]);
                return selector ? e.select(selector) : e;
            }

            function refresh() {
                let size = [$($element).width(), $($element).height()];
                if (! size[0] || ! size[1] && lastSize) {
                    size = lastSize;
                }
                const screenRect = new SIREPO.GEOMETRY.Rect(
                    new SIREPO.GEOMETRY.Point(
                        $scope.axesMargins.x.width,
                        $scope.axesMargins.y.height
                    ),
                    new SIREPO.GEOMETRY.Point(
                        size[0] - $scope.axesMargins.x.width,
                        size[1] - $scope.axesMargins.y.height
                    )
                );

                // If an axis is shorter than this, don't display it -- the ticks will
                // be cramped and unreadable
                const minAxisDisplayLen = 50;

                for (const dim of SIREPO.GEOMETRY.GeometryUtils.BASIS()) {

                    const cfg = axisCfg[dim];
                    const isHorizontal = cfg.screenDim === 'x';
                    const axisEnds = isHorizontal ? ['◄', '►'] : ['▼', '▲'];
                    const perpScreenDim = isHorizontal ? 'y' : 'x';

                    let showAxisEnds = false;
                    const axisSelector = `.${dim}.axis`;
                    const axisLabelSelector = `.${dim}-axis-label`;

                    // sort the external edges so we'll preferentially pick the left and bottom
                    const externalEdges = $scope.boundObj.externalViewportEdgesForDimension(dim)
                        .sort(vtkAxisService.edgeSorter(perpScreenDim, ! isHorizontal));
                    const seg = geometry.bestEdgeAndSectionInBounds(
                        externalEdges, screenRect, dim, false
                    );
                    const cli = screenRect.boundaryIntersectionsWithSeg(
                        $scope.boundObj.originLines()[dim]
                    );
                    if (cli && cli.length === 2) {
                        $scope.centralAxes[dim].x = [cli[0].x, cli[1].x];
                        $scope.centralAxes[dim].y = [cli[0].y, cli[1].y];
                    }

                    if (! seg) {
                        // param to show arrow ends?
                        /*
                        // all possible axis ends offscreen, so try a centerline
                        var cl = $scope.boundObj.vpCenterLineForDimension(dim);
                        seg = geometry.bestEdgeAndSectionInBounds([cl], $scope.boundObj.boundingRect(), dim, false);
                        if (! seg) {
                            // don't draw axes
                            d3self.select(axisSelector).style('opacity', 0.0);
                            d3self.select(axisLabelSelector).style('opacity', 0.0);
                            continue;
                        }
                        showAxisEnds = true;
                        */
                        d3self.select(axisSelector).style('opacity', 0.0);
                        d3self.select(axisLabelSelector).style('opacity', 0.0);
                        continue;
                    }
                    d3self.select(axisSelector).style('opacity', 1.0);

                    const fullSeg = seg.full;
                    const clippedSeg = seg.clipped;
                    var reverseOnScreen = vtkAxisService.shouldReverseOnScreen(
                        $scope.boundObj.viewportEdges()[dim][seg.index], cfg.screenDim
                    );
                    var sortedPts = SIREPO.GEOMETRY.GeometryUtils.sortInDimension(
                        clippedSeg.points,
                        cfg.screenDim,
                        false
                    );
                    var axisLeft = sortedPts[0].x;
                    var axisTop = sortedPts[0].y;
                    var axisRight = sortedPts[1].x;
                    var axisBottom = sortedPts[1].y;
                    //var axisLeft = sortedPts[0].x * dsz[0];
                    //var axisTop = sortedPts[0].y * dsz[1];
                    //var axisRight = sortedPts[1].x * dsz[0];
                    //var axisBottom = sortedPts[1].y * dsz[1];

                    var newRange = Math.min(fullSeg.length(), clippedSeg.length());
                    var radAngle = Math.atan(clippedSeg.slope());
                    if (! isHorizontal) {
                        radAngle -= Math.PI / 2;
                        if (radAngle < -Math.PI / 2) {
                            radAngle += Math.PI;
                        }
                    }
                    var angle = (180 * radAngle / Math.PI);

                    const allPts = SIREPO.GEOMETRY.GeometryUtils.sortInDimension(
                        fullSeg.points.concat(clippedSeg.points),
                        cfg.screenDim,
                        false
                    );

                    var limits = reverseOnScreen ? [cfg.max, cfg.min] : [cfg.min, cfg.max];
                    var newDom = [cfg.min, cfg.max];
                    // 1st 2, last 2 points
                    for (var m = 0; m < allPts.length; m += 2) {
                        // a point may coincide with its successor
                        var d = allPts[m].dist(allPts[m + 1]);
                        if (d !== 0) {
                            var j = Math.floor(m / 2);
                            var k = reverseOnScreen ? 1 - j : j;
                            var l1 = limits[j];
                            var l2 = limits[1 - j];
                            var part = (l1 - l2) * d / fullSeg.length();
                            var newLimit = l1 - part;
                            newDom[k] = newLimit;
                        }
                    }
                    var xform = 'translate(' + axisLeft + ',' + axisTop + ') ' +
                        'rotate(' + angle + ')';

                    if (axisCfg.doNice) {
                        axes[dim].scale.domain(newDom).nice();
                    }
                    axes[dim].scale.range([reverseOnScreen ? newRange : 0, reverseOnScreen ? 0 : newRange]);

                    // this places the axis tick labels on the appropriate side of the axis
                    var outsideCorner = SIREPO.GEOMETRY.GeometryUtils.sortInDimension(
                        $scope.boundObj.viewPortCorners(),
                        perpScreenDim,
                        isHorizontal
                    )[0];
                    var bottomOrLeft = outsideCorner.equals(sortedPts[0]) || outsideCorner.equals(sortedPts[1]);
                    if (isHorizontal) {
                        axes[dim].svgAxis.orient(bottomOrLeft ? 'bottom' : 'top');
                    }
                    else {
                        axes[dim].svgAxis.orient(bottomOrLeft ? 'left' : 'right');
                    }


                    if (showAxisEnds) {
                        axes[dim].svgAxis.ticks(0);
                        d3self.select(axisSelector).call(axes[dim].svgAxis);
                    }
                    else {
                        axes[dim].updateLabelAndTicks({
                            width: newRange,
                            height: newRange
                        }, select);
                    }

                    d3self.select(axisSelector).attr('transform', xform);

                    var dimLabel = cfg.dimLabel;
                    d3self.selectAll(axisSelector + '-end')
                        .style('opacity', showAxisEnds ? 1 : 0);

                    var tf = axes[dim].svgAxis.tickFormat();
                    if (tf) {
                        d3self.select(axisSelector + '-end.low')
                            .text(axisEnds[0] + ' ' + dimLabel + ' ' + tf(reverseOnScreen ? newDom[1] : newDom[0]) + axes[dim].unitSymbol + axes[dim].units)
                            .attr('x', axisLeft)
                            .attr('y', axisTop)
                            .attr('transform', 'rotate(' + (angle) + ', ' + axisLeft + ', ' + axisTop + ')');

                        d3self.select(axisSelector + '-end.high')
                            .attr('text-anchor', 'end')
                            .text(tf(reverseOnScreen ? newDom[0] : newDom[1]) + axes[dim].unitSymbol + axes[dim].units + ' ' + dimLabel + ' ' + axisEnds[1])
                            .attr('x', axisRight)
                            .attr('y', axisBottom)
                            .attr('transform', 'rotate(' + (angle) + ', ' + axisRight + ', ' + axisBottom + ')');
                    }

                    // counter-rotate the tick labels
                    var labels = d3self.selectAll(axisSelector + ' text');
                    labels.attr('transform', 'rotate(' + (-angle) + ')');
                    d3self.select(axisSelector + ' .domain').style({'stroke': 'none'});
                    d3self.select(axisSelector).style('opacity', newRange < minAxisDisplayLen ? 0 : 1);

                    var labelSpace = 2 * plotting.tickFontSize(d3self.select(axisSelector + '-label'));
                    var labelSpaceX = (isHorizontal ? Math.sin(radAngle) : Math.cos(radAngle)) * labelSpace;
                    var labelSpaceY = (isHorizontal ? Math.cos(radAngle) : Math.sin(radAngle)) * labelSpace;
                    var labelX = axisLeft + (bottomOrLeft ? -1 : 1) * labelSpaceX + (axisRight - axisLeft) / 2.0;
                    var labelY = axisTop + (bottomOrLeft ? 1 : -1) * labelSpaceY + (axisBottom - axisTop) / 2.0;
                    var labelXform = 'rotate(' + (isHorizontal ? 0 : -90) + ' ' + labelX + ' ' + labelY + ')';

                    d3self.select('.' + dim + '-axis-label')
                        .attr('x', labelX)
                        .attr('y', labelY)
                        .attr('transform', labelXform)
                        .style('opacity', (showAxisEnds || newRange < minAxisDisplayLen) ? 0 : 1);

                    // these optional axes go through (0, 0, 0)


                }
                lastSize = size;
            }

            function init() {
                for (var dim in axes) {
                    axes[dim].init();
                    axes[dim].svgAxis.tickSize(0);
                }
                rebuildAxes();
            }

            function rebuildAxes() {
                for (var dim in axes) {
                    var cfg = axisCfg[dim];
                    axes[dim].values = plotting.linearlySpacedArray(cfg.min, cfg.max, cfg.numPoints);
                    axes[dim].scale.domain([cfg.min, cfg.max]);
                    axes[dim].parseLabelAndUnits(cfg.label);
                }
            }

            $scope.$on('axes.refresh', refresh);

            // may not need this refresh?
            $scope.$watch('boundObj', function (d) {
                if (d) {
                    //refresh();
                }
            });

            $scope.$watch('axisCfg', function (d) {
                if (d) {
                    axisCfg = $scope.axisCfg;
                    rebuildAxes();
                    refresh();
                }
            }, true);

            init();
        },
    };
});

// will be axis functions
SIREPO.app.service('vtkAxisService', function(appState, panelState, requestSender, frameCache, plotting, vtkPlotting, layoutService, utilities, geometry) {

    var svc = {};

    svc.edgeSorter = function(dim, shouldReverse) {
        return function(e1, e2) {
            if (! e1) {
                if (! e2) {
                    return 0;
                }
                return 1;
            }
            if (! e2) {
                return -1;
            }
            var pt1 = geometry.sortInDimension(e1.points, dim, shouldReverse)[0];
            var pt2 = geometry.sortInDimension(e2.points, dim, shouldReverse)[0];
            return (shouldReverse ? -1 : 1) * (pt2[dim] - pt1[dim]);
        };
    };

    svc.shouldReverseOnScreen = function(edge, screenDim) {
        return edge.points[1][screenDim] < edge.points[0][screenDim];
    };

    return svc;
});

// General-purpose vtk display
SIREPO.app.directive('vtkDisplay', function(appState, panelState, utilities, $document, $window) {

    return {
        restrict: 'A',
        scope: {
            axisCfg: '<',
            axisObj: '<',
            enableAxes: '=',
            enableSelection: '=',
            eventHandlers: '<',
            modelName: '@',
            resetDirection: '@',
            resetSide: '@',
            showBorder: '@',
        },
        templateUrl: '/static/html/vtk-display.html' + SIREPO.SOURCE_CACHE_KEY,
        controller: function($scope, $element) {

            $scope.GeometryUtils = SIREPO.GEOMETRY.GeometryUtils;
            $scope.VTKUtils = VTKUtils;
            $scope.markerState = {
                enabled: true,
            };
            $scope.modeText = {};
            $scope.isOrtho = false;
            $scope.selection = null;

            let didPan = false;
            let hasBodyEvt = false;
            let hdlrs = {};
            let isDragging = false;
            let isPointerUp = true;

            const canvasHolder = $($element).find('.vtk-canvas-holder').eq(0);

            // supplement or override these event handlers
            let eventHandlers = {
                onpointerdown: function (evt) {
                    isDragging = false;
                    isPointerUp = false;
                },
                onpointermove: function (evt) {
                    if (isPointerUp) {
                        return;
                    }
                    isDragging = true;
                    didPan = didPan || evt.shiftKey;
                    $scope.vtkScene.viewSide = null;
                    utilities.debounce(refresh, 100)();
                },
                onpointerup: function (evt) {
                    isDragging = false;
                    isPointerUp = true;
                    refresh();
                },
                onwheel: utilities.debounce(refresh, 100),
            };

            function ondblclick() {
                $scope.vtkScene.resetView();
                refresh();
                $scope.$apply();
            }

            function resize() {
                refresh();
            }

            $scope.init = function() {
                const rw = angular.element($($element).find('.vtk-canvas-holder'))[0];
                const body = angular.element($($document).find('body'))[0];
                const view = angular.element($($document).find('.sr-view-content'))[0];
                hdlrs = $scope.eventHandlers || {};

                // vtk adds keypress event listeners to the BODY of the entire document, not the render
                // container.
                hasBodyEvt = Object.keys(hdlrs).some(function (e) {
                    return ['keypress', 'keydown', 'keyup'].includes(e);
                });
                if (hasBodyEvt) {
                    const bodyAddEvtLsnr = body.addEventListener;
                    const bodyRmEvtLsnr = body.removeEventListener;
                    body.addEventListener = (type, listener, opts) => {
                        bodyAddEvtLsnr(type, hdlrs[type] ? hdlrs[type] : listener, opts);
                    };
                    // seem to need to do this so listeners get removed correctly
                    body.removeEventListener = (type, listener, opts) => {
                        bodyRmEvtLsnr(type, listener, opts);
                    };
                }

                $scope.vtkScene = new VTKScene(rw, $scope.resetSide, $scope.resetDirection);

                // double click handled separately
                rw.addEventListener('dblclick', function (evt) {
                    ondblclick(evt);
                    if (hdlrs.ondblclick) {
                        hdlrs.ondblclick(evt);
                    }
                });
                Object.keys(eventHandlers).forEach(function (k) {
                    const f = function (evt) {
                        eventHandlers[k](evt);
                        if (hdlrs[k]) {
                            hdlrs[k](evt);
                        }
                    };
                    if (k == 'onpointermove') {
                        view[k] = f;
                        return;
                    }
                    rw[k] = f;
                });
                // remove global VTK key listeners
                for (const n of ['KeyPress', 'KeyDown', 'KeyUp']) {
                    document.removeEventListener(
                        n.toLowerCase(),
                        $scope.vtkScene.fsRenderer.getInteractor()[`handle${n}`],
                    );
                }
                $scope.$emit('vtk-init', $scope.vtkScene);
                resize();
            };

            $scope.canvasGeometry = function() {
                return {
                    pos: $(canvasHolder).position(),
                    size: {
                        width: Math.max(0, $(canvasHolder).width()),
                        height: Math.max(0, $(canvasHolder).height()),
                    }
                };
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
                $element.off();
                $($window).off('resize', resize);
                $scope.vtkScene.teardown();
            });

            function refresh() {
                if ($scope.axisObj) {
                    $scope.$broadcast('axes.refresh', $scope.axisObj);
                }
            }

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
            $scope.init();


            $($window).resize(resize);
        },
    };
});

// general-purpose vtk methods
SIREPO.app.service('vtkService', function(appState, panelState, requestSender, frameCache, plotting, vtkPlotting, layoutService, utilities, geometry) {
    let svc = {};
    return svc;
});

SIREPO.app.factory('vtkUtils', function() {

    var self = {};

    self.INTERACTION_MODE_MOVE = 'move';
    self.INTERACTION_MODE_SELECT = 'select';
    self.INTERACTION_MODES = [self.INTERACTION_MODE_MOVE, self.INTERACTION_MODE_SELECT];

    // Converts vtk colors ranging from 0 -> 255 to 0.0 -> 1.0
    // can't map, because we will still have a UINT8 array
    self.rgbToFloat = rgb => {
        let sc = [];
        for (let i = 0; i < rgb.length; ++i) {
            sc.push(rgb[i] / 255.0);
        }
        return sc;
    };

    // Converts vtk colors ranging from 0 -> 255 to 0.0 -> 1.0
    // can't map, because we will still have a UINT8 array
    self.floatToRGB =  f => {
        const rgb = new window.Uint8Array(f.length);
        for (let i = 0; i < rgb.length; ++i) {
            rgb[i] = Math.floor(255 * f[i]);
        }
        return rgb;
    };

    return self;
});

SIREPO.VTK = {
    ActorBundle: ActorBundle,
    BoxBundle: BoxBundle,
    CoordMapper: CoordMapper,
    CuboidViews: CuboidViews,
    CylinderViews: CylinderViews,
    ExtrudedPolyViews: ExtrudedPolyViews,
    LineBundle: LineBundle,
    ObjectViews: ObjectViews,
    PlaneBundle: PlaneBundle,
    RacetrackViews: RacetrackViews,
    SphereBundle: SphereBundle,
    SphereViews: SphereViews,
    VectorFieldBundle: VectorFieldBundle,
    ViewPortBox: ViewPortBox,
    VTKUtils: VTKUtils,
    VTKVectorFormula: VTKVectorFormula,
};
