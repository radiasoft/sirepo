'use strict';

var srlog = SIREPO.srlog;
var srdbg = SIREPO.srdbg;


// Math.hypot polyfill for Internet Explorer and karma tests
if (! Math.hypot) {
    Math.hypot = function() {
        var y = 0, i = arguments.length;
        while (i--) {
            y += arguments[i] * arguments[i];
        }
        return Math.sqrt(y);
    };
}

/**
 * Collection of static methods and fields related to geometric objects
 */
class GeometryUtils {

    /**
     * Names of basis directions
     * @returns {[string]}
     */
    static BASIS() {
        return ['x', 'y', 'z'];
    }

    /**
     * Vectors keyed by basis direction
     * @returns {{}} - mapping of basis direction to a vector in that direction
     */
    static BASIS_VECTORS() {
        return {
            x: [1, 0, 0],
            y: [0, 1, 0],
            z: [0, 0, 1]
        };
    }

    static axisIndex(axis) {
        return GeometryUtils.BASIS().indexOf(axis);
    }

    static bounds(points, useRadius=false) {
        let b = {
            x: [Number.MAX_VALUE, -Number.MAX_VALUE],
            y: [Number.MAX_VALUE, -Number.MAX_VALUE],
        };
        if (points[0].dimension === 3) {
            b.z = [Number.MAX_VALUE, -Number.MAX_VALUE];
        }
        const ex = GeometryUtils.extrema;
        for (const dim in b) {
            b[dim] = [ex(points, dim, false)[0][dim], ex(points, dim, true)[0][dim]];
        }
        return useRadius ? GeometryUtils.boundsRadius(b) : b;
    }

    static boundsRadius(b) {
        const r = Math.hypot(
            (b.x[1] - b.x[0]) / 2,
            (b.y[1] - b.y[0]) / 2,
            ((b.z ? b.z[1] : 0) - (b.z ? b.z[0] : 0)) / 2,
        );
        for (const dim in b) {
            const c = b[dim][0] + (b[dim][1] - b[dim][0]) / 2;
            b[dim][0] = c - r;
            b[dim][1] = c + r;
        }
        return b;
    }

    /**
     * Get the indices of the given axis and the two axes in BASIS that comes after it, wrapping around
     * @param {string} axis - start axis (x|y|z)
     * @returns {[number]}
     */
    static axisIndices(axis) {
        return ([axis, ...GeometryUtils.nextAxes(axis)]).map(x => GeometryUtils.BASIS().indexOf(x));
    }

    /**
     * Find the points with the largest or smallest value in the given dimension
     * @param {[Point]} points - the points to sort
     * @param {string} dim - the dimension in which to sort (x|y|z)
     * @param {boolean} doReverse [false] - if true, reverses the sort order
     * @returns {[Point]}
     */
    static extrema(points, dim, doReverse = false) {
        const arr = GeometryUtils.sortInDimension(points, dim, doReverse);
        return arr.filter(p =>  p[dim] === arr[0][dim]);
    }

    /**
     * Get the two axes in BASIS that comes after the given axis, wrapping around
     * @param {string} axis - start axis (x|y|z)
     * @returns {[string]}
     */
    static nextAxes(axis) {
        const w = GeometryUtils.nextAxis(axis);
        return [w, GeometryUtils.nextAxis(w)];
    }

    /**
     * Get the axis in BASIS that comes after the given axis, wrapping around
     * @param {string} axis - start axis (x|y|z)
     * @returns {string}
     */
    static nextAxis(axis) {
        const b = GeometryUtils.BASIS();
        return b[(GeometryUtils.axisIndex(axis) + 1) % b.length];
    }

    /**
     * Get the index of the axis in BASIS that comes after the given axis, wrapping around
     * @param {string} axis - start axis (x|y|z)
     * @returns {number}
     */
    static nextAxisIndex(axis) {
        return GeometryUtils.BASIS().indexOf(GeometryUtils.nextAxis(axis));
    }

    /**
     * Get the indices of the two axes in BASIS that comes after the given axis, wrapping around
     * @param {string} axis - start axis (x|y|z)
     * @returns {[number]}
     */
    static nextAxisIndices(axis) {
        return GeometryUtils.nextAxes(axis).map(x => GeometryUtils.BASIS().indexOf(x));
    }

    /**
     * Sort (with optional reversal) the point array by the values in the given dimension.
     * Array is cloned first so the original is unchanged
     * @param {[Point]} points - the points to sort
     * @param {string} dim - the dimension in which to sort (x|y|z)
     * @param {boolean} doReverse [false] - if true, reverses the sort order
     * @returns {[Point]}
     */
    static sortInDimension(points, dim, doReverse = false) {
        return points.slice().sort((p1, p2) => {
            // throws an exception if the points have different dimensions
            p1.dist(p2);
            return (doReverse ? -1 : 1) * (p1[dim] - p2[dim]) / Math.abs(p1[dim] - p2[dim]);
        });
    }

    static toDegrees(rad) {
        return 180.0 * rad / Math.PI;
    }

    static toRadians(deg) {
        return Math.PI * deg / 180.0;
    }

}

/**
 * Base class of geometric objects
 */
class GeometricObject {
    /**
     * @param {number} equalityTolerance [1e-4] - the margin within which two values are "equal". This is necessary
     * because various numerical operations can cause values to differ by amounts that are negligible for
     * practical purposes but nonetheless large enough to be unequal according to "==".
     */
    constructor(equalityTolerance= 1e-4) {
        this.equalityTolerance = equalityTolerance;
    }

    /**
     * String representation of an array of GeometricObjects
     * @param {[GeometricObject]} arr - the GeometricObjects to render as strings
     * @returns {string}
     */
    static arrayString(arr) {
        return `[${arr.map(e => e.toString())}]`;
    }

    /**
     * A formatted error message with related object
     * @param {*} obj - the object or value of interest
     * @param {string} msg - the message
     * @returns {string}
     */
    errorMessage(obj, msg) {
        return `${obj}: ${msg}`;
    }

    /**
     * Determines if two values are equal relative to the equalityTolerance of this object
     * @param {number} val1 - 1st value
     * @param {number} val2 - 2nd value
     * @returns {boolean}
     */
    equalWithin(val1, val2) {
        return Math.abs(val2 - val1) < (this.equalityTolerance * Math.max(Math.abs(val1), Math.abs(val2)));
    }

    /**
     * Determines if one value is greater than another, or equal to it relative to the equalityTolerance of this object
     * @param {number} val1 - 1st value
     * @param {number} val2 - 2nd value
     * @returns {boolean}
     */
    gtOrEqualWithin(val1, val2) {
        return val1 > val2 || this.equalWithin(val1, val2);
    }

    /**
     * Determines if one value is less than another, or equal to it relative to the equalityTolerance of this object
     * @param {number} val1 - 1st value
     * @param {number} val2 - 2nd value
     * @returns {boolean}
     */
    ltOrEqualWithin(val1, val2) {
        return val1 < val2 || this.equalWithin(val1, val2);
    }

    /**
     * String representation of this GeometricObject. Subclasses should override
     * @returns {string}
     */
    toString() {
        return '<OBJ>';
    }
}

/**
 * A two or three dimensional matrix and associated methods
 */
class Matrix extends GeometricObject {

    static dot(v1, v2) {
        return v1.reduce((sum, x, i) => sum + x * v2[i], 0);
    }

    static mult(m1, m2) {
        let m = [];
        for(let i in m1) {
            let c = [];
            for(let j in m2) {
                c.push(m2[j][i]);
            }
            m.push(Matrix.vect(m1, c));
        }
        return m;
    }

    static vect(m, v) {
        let r = [];
        for (let x of m) {
            r.push(Matrix.dot(x, v));
        }
        return r;
    }

    /**
     * @param {[number] | [[number]]} val - an array representing the matrix
     * @throws - if the dimension is > 2
     */
    constructor(val) {
        super();

        /** @member {[number] | [[number]]} - the array */
        this.val = val;

        /** @member {number} - the dimension of this Matrix */
        this.dimension = this.getDimension();

        /** @member {number} - the number of rows in this Matrix */
        this.numRows = 0;

        /** @member {number} - the number of columns in this Matrix */
        this.numCols = 0;

        if (this.dimension > 2) {
            throw new Error(this.errorMessage(`Arrays with dimension ${this.dimension} not supported`));
        }

        if (this.dimension === 1) {
            this.numRows = 1;
            this.numCols = val.length;
        }
        if (this.dimension === 2) {
            const n = val[0].length;
            if (! val.every(x => x.length === n)) {
                throw new Error(this.errorMessage('Rows must contain the same number of elements'));
            }
            this.numRows = val.length;
            this.numCols = n;
        }
    }

    /**
     * Adds this matrix to another
     * @param {Matrix} matrix - the addend
     * @returns {Matrix}
     */
    add(matrix) {
        return this.linearCombination(matrix, 1);
    }

    /**
     * Determines if this matrix is equal to another, according to the following criteria:
     * - if the two have unequal dimension, they are unequal
     * - if the two have different numbers of rows or columns, they are unequal
     * - finally, if all the values in each position are equal within <equalityTolerance>, they are equal
     * @param {Matrix} matrix - another matrix
     * @returns {boolean}
     */
    equals(matrix) {
        if (this.dimension !== matrix.dimension) {
            return false;
        }
        if (['numRows', 'numCols'].some(x => this[x] !== matrix[x])) {
            return false;
        }
        if (this.dimension === 1) {
            return this.val.every((x, i) => this.equalWithin(x, matrix.val[i]));
        }
        for(let i in this.val) {
            for(let j in matrix.val) {
                if (! this.equalWithin(this.val[i][j], matrix.val[i][j])) {
                    return false;
                }
            }
        }
        return true;
    }

    /**
     * Formatted error
     * @param {string} msg - a message
     * @returns {string}
     */
    errorMessage(msg) {
        return super.errorMessage(this.val, msg);
    }

    /**
     * The number of dimensions of this Matrix
     * @returns {number}
     */
    getDimension() {
        if (! Array.isArray(this.val)) {
            return 0;
        }
        return 1 + new Matrix(this.val[0]).dimension;
    }

    /**
     * Combines this Matrix additively with another, multiplied by a constant, that is:
     *  S = this + c * M2
     * The two Matrices must have the same dimension and an equal number of rows and columns
     * @param {Matrix} matrix - another Matrix
     * @param {number} constant - a constant
     * @returns {Matrix}
     * @throws - if the two matrices cannot be combined
     */
    linearCombination(matrix, constant) {
        if (matrix.dimension !== this.dimension) {
            throw new Error(this.errorMessage(`Argument must have same dimension (${matrix.dimension} != ${this.dimension})`));
        }
        if (matrix.numRows !== this.numRows || matrix.numCols !== this.numCols) {
            throw new Error(this.errorMessage(`Argument must have same number of rows and columns (rows ${matrix.numRows} vs ${this.numRows}, cols ${matrix.numCols} vs ${this.numCols})`));
        }

        if (this.dimension === 1) {
            return new Matrix(this.val.map((x, i) => x + constant * matrix.val[i]));
        }
        return new Matrix(
            this.val.map((x, i) => new Matrix(x).linearCombination(new Matrix(matrix.val[i]), constant))
        );
    }

    /**
     * Multiplies this Matrix with another, that is:
     *  P = this * M2
     * Note that matrix multiplication is not commutative, that is, the order matters. Accordingly, the following
     * restrictions apply:
     * - the dimension of the argument must be less than or equal to that of this Matrix
     * - if both Matrices are vectors (1-dimensional), they must have the same number of entries. The result is the
     *      dot product (that is, a number)
     * - otherwise the number of rows in this Matrix must equal the number of columns of the argument
     * - outer product (vector1 * vector2 -> matrix) is not supported
     * @param {Matrix} matrix - another Matrix
     * @returns {Matrix|number}
     * @throws - if the two matrices cannot be multiplied
     */
    multiply(matrix) {
        if (matrix.dimension > this.dimension) {
            throw new Error(this.errorMessage(`Argument must have lesser or equal dimension (${matrix.dimension} > ${this.dimension})`));
        }

        // vector * vector (dot product)
        if (this.dimension === 1) {
            if (this.numCols !== matrix.numCols) {
                throw new Error(this.errorMessage(`Vectors must have same length (${this.numCols} != ${matrix.numCols})`));
            }
            return Matrix.dot(this.val, matrix.val);
        }

        if (this.numRows !== matrix.numCols) {
            throw new Error(this.errorMessage(`numRows must equal argument's numCols (${this.numRows} != ${matrix.numCols})`));
        }

        // matrix * vector
        if (matrix.dimension === 1) {
            return new Matrix(Matrix.vect(this.val, matrix.val));
        }

        // matrix * matrix
        return (new Matrix(Matrix.mult(this.val, matrix.val))).transpose();
    }

    /**
     * Subtracts a Matrix from this one
     * @param {Matrix} matrix - the subtrahend
     * @returns {Matrix}
     */
    subtract(matrix) {
        return this.linearCombination(matrix, -1);
    }

    /**
     * Transposes this Matrix from (m x n) to (n x m)
     * @returns {Matrix}
     */
    transpose() {
        let m = [];
        const ll = this.val[0].length;
        if (! ll) {
            this.val.forEach(entry => {
                m.push([entry]);
            });
            return new Matrix(m);
        }
        for(let j = 0; j < this.numCols; ++j) {
            let r = [];
            for(let i = 0; i < this.numRows; ++i) {
                r.push(this.val[i][j]);
            }
            m.push(r);
        }
        return new Matrix(m);
    }
}

/*
 * A 2-dimensional matrix with an equal number of rows and columns, and associated methods
 */
class SquareMatrix extends Matrix {
    /**
     * @param {[[number]]} val - an array representing the matrix
     * @throws - if the number of rows and columns differ
     */
    constructor(val) {
        super(val);
        if (this.numRows !== this.numCols) {
            throw new Error(this.errorMessage(`Not square: ${this.numRows} != ${this.numCols}`));
        }

        /** @member {number} - the size of this Matrix */
        this.size = this.numRows;
    }

    /**
     * Computes the determinant of this Matrix
     * @returns {number}
     */
    det() {
        if (this.size === 2) {
            return this.val[0][0] * this.val[1][1] - this.val[1][0] * this.val[0][1];
        }
        let d = 0;
        for(let i in this.val) {
            let t = 1;
            let s = 1;
            for(let j in this.val) {
                const k = (i + j) % this.size;
                const l = (i + this.size - j) % this.size;
                t *= this.val[j][k];
                s *= this.val[j][l];
            }
            d += (t - s);
        }
        return d;
    }

    /**
     * Computes the inverse of this Matrix
     * @returns {SquareMatrix}
     * @throws - if this Matrix cannot be inverted (that is, has a determinant of 0)
     */
    inverse() {
        let d = this.det();
        if (! d) {
            throw new Error(this.errorMessage('Matrix is not invertible'));
        }
        const mx = this.transpose();
        let inv = [];
        for (let i = 0; i < mx.size; ++i) {
            let invRow = [];
            let mult = 1;
            for(let j = 0; j < mx.size; ++j) {
                mult = Math.pow(-1,i + j);
                invRow.push((mult / d) * mx.minor(i, j).det());
            }
            inv.push(invRow);
        }
        return new SquareMatrix(inv);
    }

    /**
     * Computes the minor of this Matrix, that is, the sub-matrix obtained by removing the given row and column
     * @param {number} rowNum - the row to remove
     * @param {number} colNum - the columns to remove
     * @returns {SquareMatrix}
     */
    minor(rowNum, colNum) {
        let m = [];
        for(let i = 0; i < this.size; ++i) {
            let r = [];
            for(let j = 0; j < this.size; ++j) {
                if (i !== rowNum && j !== colNum) {
                    r.push(this.val[i][j]);
                }
            }
            if (r.length > 0) {
                m.push(r);
            }
        }
        return new SquareMatrix(m);
    }

    /**
     * Trace of this matrix
     */
    trace() {
        return this.val.reduce((p, n, i) => p + n[i], 0);
    }

    /**
     * Transpose of this matrix, as a SquareMatrix
     * @returns {SquareMatrix}
     */
    transpose() {
        return new SquareMatrix(super.transpose().val);
    }
}

/*
 * The n-dimensional identity matrix
 */
class IdentityMatrix extends SquareMatrix {
    /**
     * @param {number} size - number of rows/columms
     */
    constructor(size=3) {
        const m = [];
        for (let i = 0; i < size; ++i) {
            const n = [];
            for (let j = 0; j < size; ++j) {
                n.push(i === j ? 1 : 0);
            }
            m.push(n);
        }
        super(m);
    }
}

/**
 * 4-dimensional transformation matrix
 */
class AffineMatrix extends SquareMatrix {
    constructor(val=new IdentityMatrix(4).val) {
        if (val.length !== 4) {
            throw new Error ('Affine Matrix must be 4x4: ' + val);
        }
        super(val);
    }

    multiplyAffine(matrix) {
        return new AffineMatrix(this.multiply(matrix).val);
    }

    getLinearMinor() {
        return this.minor(3, 3);
    }

    getRotation() {
        return RotationMatrix.fromVal(this.val);
    }

    getTranslation() {
        return new TranslationMatrix(this.transpose().val[3].slice(0, 3));
    }
}

/*
 * Rotation about arbitrary axis - note this is 4 x 4 and will need to multiply a vector [x, y, z, 0]
 */
class RotationMatrix extends AffineMatrix {

    static fromVal(val) {
        const r = new RotationMatrix();
        r.val = val;
        const m = r.minor(3, 3);
        if (! m.equalWithin(m.det(), 1) || ! m.inverse().equals(m.transpose())) {
            throw new Error('Not a rotation: ' + val);
        }
        return r;
    }

    /**
     * @param {[number]} axis - axis of rotation
     * @param {[number]} point - a point that the axis contains
     * @param {number} angle - rotation angle in radians
     */
    constructor(axis=[0, 0, 1], point=[0, 0, 0], angle=0.0) {
        const cs = Math.cos(angle);
        const cs1 = 1 - cs;
        const s = Math.sin(angle);

        const A = point[0];
        const B = point[1];
        const C = point[2];

        const nv = VectorUtils.normalize(axis);
        const u = nv[0];
        const v = nv[1];
        const w = nv[2];
        const m = [
            [
                u * u + (v * v + w * w) * cs,
                u * v * cs1 - w * s,
                u * w * cs1 + v * s,
                (A * (v * v + w * w) - u * (B * v + C * w)) * cs1 + (B * w - C * v) * s
            ],
            [
                u * v * cs1 + w * s,
                v * v + (u * u + w * w) * cs,
                v * w * cs1 - u * s,
                (B * (u * u + w * w) - v * (A * u + C * w)) * cs1 + (C * u - A * w) * s
            ],
            [
                u * w * cs1 - v * s,
                v * w * cs1 + u * s,
                w * w + (u * u + v * v) * cs,
                (C * (u * u + v * v) - w * (A * u + B * v)) * cs1 + (A * v - B * u) * s
            ],
            [0, 0, 0, 1]
        ];
        super(m);
    }

    toEuler(toDegrees=false) {
        let theta = -Math.asin(this.val[2][0]);
        const c = Math.cos(theta);
        let psi = 0;
        let phi = 0;
        if (c === 0) {
            if (this.val[2][0] === -1) {
                theta = Math.PI / 2;
                psi = phi + Math.atan2(this.val[0][1], this.val[0][0]);
            }
            else {
                theta = -Math.PI / 2;
                psi = -phi + Math.atan2(-this.val[0][1], -this.val[0][0]);
            }
        }
        else {
            psi = Math.atan2(this.val[2][1] / c, this.val[2][2] / c);
            phi = Math.atan2(this.val[1][0] / c, this.val[0][0] / c);
        }
        return [psi, theta, phi].map(x => toDegrees ? GeometryUtils.toDegrees(x) : x);
    }
}

/**
 * Affine transformation for reflections through an arbitrary plane
 */
class ReflectionMatrix extends AffineMatrix {
    /**
     * @param {Plane} plane - reflection plane
     */
    constructor(plane) {
        const n = plane.norm;
        const p = plane.point.coords();
        const d = -n[0] * p[0] - n[1] * p[1] - n[2] * p[2];
        const m = [
            [1 - 2 * n[0] * n[0], -2 * n[0] * n[1], -2 * n[0] * n[2], -2 * n[0] * d],
            [-2 * n[1] * n[0], 1 - 2 * n[1] * n[1], -2 * n[1] * n[2], -2 * n[1] * d],
            [-2 * n[2] * n[0], -2 * n[2] * n[1], 1 - 2 * n[2] * n[2], -2 * n[2] * d],
            [0, 0, 0, 1]
        ];
        super(m);
        this.plane = plane;
    }
}

/**
 * Affine transformation for translations
 */
class TranslationMatrix extends AffineMatrix {
    /**
     * @param {[number]} deltas - translation in each direction
     */
    constructor(deltas) {
        super();
        for (let i in deltas) {
            this.val[i][3] = deltas[i];
        }
        this.deltas = deltas;
    }
}


/*
 * A transform built from the provided SquareMatrix. Currently supports only 3 x 3.
 */
class Transform extends GeometricObject {
    /**
     * @param {SquareMatrix} matrix - the Matrix
     * @throws - if the matrix is not square or not 3 x 3, or cannot be inverted
    */
    constructor(matrix = new IdentityMatrix()) {
        super();
        const size = matrix.numRows;
        if (size !== 3) {
            throw new Error(this.errorMessage(`Matrix has bad size (${size})`));
        }
        if (matrix.numRows !== matrix.numCols) {
            throw new Error(this.errorMessage(`Matrix is not square (rows ${matrix.numRows} != cols ${matrix.numCols})`));
        }

        // "cast" to square matrix
        this.matrix = new SquareMatrix(matrix.val);
        if (this.matrix.det() === 0) {
            throw new Error(this.errorMessage('Matrix is not invertible'));
        }
    }

    /**
     * Transforms the given Matrix via multiplication
     * @param {Matrix} matrix - the Matrix to transform
     * @returns {Matrix}
   */
    apply(matrix) {
        return this.matrix.multiply(matrix);
    }

    /**
     * Composes this Transform and another via matrix multiplication
     * @param {Transform} transform - the Transform to compose with this one
     * @returns {Transform}
     * @throws - if the wrapped Matrices have different sizes
   */
    compose(transform) {
        if (transform.matrix.size !== this.matrix.size) {
            throw new Error(this.errorMessage('Matrices must be same size (' + this.matrix.size + ' != ' + transform.matrix.size));
        }
        return new Transform(new SquareMatrix(this.apply(transform.matrix).val));
    }

    /**
     * Formatted error
     * @param {string} msg - a message
     * @returns {string}
     */
    errorMessage(msg) {
        return super.errorMessage(this.matrix.val, msg);
    }

    /**
     * String representation of this Transform
     * @returns {string}
     */
    toString() {
        let str = '[';
        for(let i in this.matrix.val) {
            let rstr = '[';
            for(let j in this.matrix.val[i]) {
                rstr += this.matrix.val[i][j];
                rstr += (j < this.matrix.val[i].length - 1 ? ', ' : ']');
            }
            str += rstr;
            str += (i < this.matrix.val.length -1  ? ', ' : ']');
        }
        return str;
    }
}

/*
 * A point in 2 or 3 dimensions
 */
class Point extends GeometricObject {

    /**
     * @param {number} x - the x coordinate
     * @param {number} y - the y coordinate
     * @param {number} z - the z coordinate
    */
    constructor(x, y, z) {
        super();

        /** @member {number} - the x coordinate */
        this.x = x || 0;

        /** @member {number} - the y coordinate */
        this.y = y || 0;

        /** @member {number} - the z coordinate */
        this.z = z || 0;

        /** @member {number} - the dimension: 3 if a z value is provided, 2 otherwise */
        this.dimension = 2 + (z === undefined ? 0 : 1);
    }

    /**
     * Array of the coordinates
     * @returns {[number]}
     */
    coords() {
        return [this.x, this.y, this.z].slice(0, this.dimension);
    }

    /**
     * Determines whether the coordinate at the given index of this point and the given point are
     * equal according to equalWithin
     * @param {Point} point - another Point
     * @param {number} index - index of the coordinate
     * @returns {boolean}
     */
    coordEquals(point, index) {
        return this.equalWithin(this.coords()[index], point.coords()[index]);
    }

    /**
     * Distance to another Point
     * @param {Point} point - another Point
     * @returns {number}
     * @throws - if the two points have different dimensions
     */
    dist(point) {
        if (this.dimension !== point.dimension) {
            throw new Error('Points in array have different dimensions: ' + this.dimension + ' != ' + point.dimension);
        }
        return Math.hypot(point.x - this.x, point.y - this.y, point.z - this.z);
    }

    /**
     * Determines whether this Point equals another, according to the following criteria:
     * - if the two have different dimensions, they are unequal
     * - otherwise, if the distance between the points divided by their average "size"
     *   (distance to origin) is within <equalityTolerance>, they are equal. This
     *   calculation is done to compare points with values below the tolerance
     * @param {Point} point - another Point
     * @returns {boolean}
     */
    equals(point) {
        if (this.dimension !== point.dimension) {
            return false;
        }
        const z = this.zero();
        const d = 0.5 * (this.dist(z) + point.dist(z)) || 1.0;
        return this.dist(point) / d < this.equalityTolerance;
    }

    /**
     * Determines whether this Point is inside the given Rectangle
     * @param {Rect} rect - a Rect
     * @returns {boolean}
     */
    isInRect(rect) {
        return rect.containsPoint(this);
    }

    /**
     * String value of this Point
     * @returns {string}
     */
    toString() {
        return `(${this.coords()})`;
    }

    /**
     * Convenience method to create a Point with all 0s, of the same dimension as this Point
     * @returns {Point}
     */
    zero() {
        if (this.dimension === 2) {
            return new Point(0, 0);
        }
        return new Point(0, 0, 0);
    }
}

/**
 * A plane defined by a normal vector and a point
 */
class Plane extends GeometricObject {
    /**
     * @param {[number]} normal vector - will be normalized
     * @param {Point} point
     */
    constructor(norm, point=new Point()) {
        if (VectorUtils.isZero(norm)) {
            throw new Error('Must specify a non-zero plane normal: ' + norm);
        }
        super();
        this.norm = VectorUtils.normalize(norm);
        this.point = point;
        this.pointCoords = point.coords();
        this.A = this.norm[0];
        this.B = this.norm[1];
        this.C = this.norm[2];
        this.D = VectorUtils.dot(this.norm, this.pointCoords);
    }

    closestPointToPoint(p) {
        const d = this.distToPoint(p, true);
        const pc = p.coords();
        return new Point(...[pc[0] - d * this.A, pc[1] - d * this.B, pc[2] - d * this.C]);
    }

    containsPoint(p) {
        return this.equalWithin(VectorUtils.dot(this.norm, p.coords()), this.D);
    }

    distToPoint(p, signed) {
        const d = (1 / Math.hypot(...this.norm) *
            (VectorUtils.dot(this.norm, p.coords()) - this.D));
        return signed ? d : Math.abs(d);
    }

    equals(otherPlane) {
        if (! this.isParallelTo(otherPlane)) {
            return false;
        }
        return this.D === otherPlane.D;
    }

    intersection(otherPlane) {
        if (this.equals(otherPlane)) {
            // planes are equal, return an arbitrary line containing the point
            // need ensure they are not the same point!  Use random number?
            return new Line(this.point, this.pointInPlane());
        }
        // parallel but not equal, there is no intersection
        if (this.isParallelTo(otherPlane)) {
            return null;
        }
        const p1 = this.paramLine(otherPlane)(0);
        const p2 = this.paramLine(otherPlane)(1);
        return new Line(new Point(...p1), new Point(...p2));
    }

    intersectsLine(l) {
        const pts = l.points();
        const p1 = pts[0].coords();
        const p2 = pts[1].coords();
        let dp = VectorUtils.dot(
            [p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]],
            this.norm
        );
        if (dp !== 0) {
            return true;
        }
        const pp = this.pointInPlane().coords();
        const d = [pp[0] - p1[0], pp[1] - p1[1], pp[2] - p1[2]];
        dp = VectorUtils.dot(d, this.norm);
        return dp === 0;
    }

    isParallelTo(otherPlane) {
        return this.equalWithin(this.A, otherPlane.A) &&
            this.equalWithin(this.B, otherPlane.B) &&
            this.equalWithin(this.C, otherPlane.C);
    }

    mirrorPoint(p) {
        const cp = this.closestPointToPoint(p).coords();
        const d = this.distToPoint(p, true);
        return new Point(...[cp[0] - d * this.A,  cp[1] - d * this.B,  cp[2] - d * this.C]);
    }

    paramLine(otherPlane, t) {
        let freeIndex = 0;
        let i = 1;
        let j = 2;
        let d = 0;
        for (freeIndex = 0; freeIndex < 3; ++freeIndex) {
            i = (freeIndex + 1) % 3;
            j = (freeIndex + 2) % 3;
            d = this.norm[i] * otherPlane.norm[j] - this.norm[j] * otherPlane.norm[i];
            if (d !== 0) {
                break;
            }
        }
        return t => {
            const p = [0, 0, 0];
            p[freeIndex] = t;
            p[i] = ((otherPlane.norm[j] * this.D - this.norm[j] * otherPlane.D) +
                t * (this.norm[j] * otherPlane.norm[freeIndex] - otherPlane.norm[j] * this.norm[freeIndex])) / d;
            p[j] = ((this.norm[i] * otherPlane.D - otherPlane.norm[i] * this.D) +
                t * (this.norm[i] * otherPlane.norm[freeIndex] - otherPlane.norm[i] * this.norm[freeIndex])) / d;
            return p;
        };
    }

    pointInPlane(fixedVal) {
        if (fixedVal !== 0 && ! fixedVal) {
            fixedVal = 1;
        }
        // check if plane norm is along a basis vector - if so, any values in the remaining coords
        // satisfy the plane's equation
        for (let v of GeometryUtils.BASIS_VECTORS()) {
            if (VectorUtils.dot(v, this.norm) === 1) {
                return new Point(VectorUtils.subtract([1, 1, 1], v));
            }
        }
        // if a coord is 0 - can't all be 0 so at most one - the equation of the plane
        // is also the equation of a line.  If no coords are 0 we can arbitrarily set z to 0
        const non0 = [[1, 2], [0, 2], [0, 1]];
        const ptArr = [0, 0, 0];
        let zIdx = this.norm.indexOf(0);
        zIdx = zIdx >= 0 ? zIdx : 2;
        const nzIdxs = non0[zIdx];
        ptArr[nzIdxs[0]] = fixedVal;
        ptArr[nzIdxs[1]] = -fixedVal * this.norm[nzIdxs[0]] / this.norm[nzIdxs[1]];
        return new Point(...ptArr);
    }
}

/*
 * A 2-dimensional line defined by 2 points
 */
class Line extends GeometricObject {
    /**
     * @param {Point} point1 - the 1st Point
     * @param {Point} point2 - the 2nd Point
    */
    constructor(point1, point2) {
        super();

        /** @member {[Point]} - an array of the given Points */
        this.points = [point1, point2];
    }

    /**
     * Compares a given Point to this line, in the following sense:
     * - if the Point is on this Line, return 0
     * - if the Line is vertical, return 1 if the x coordinate of the Point is greater than the Line's, else -1
     * - if the Line is horizontal, return 1 if the y coordinate of the Point is greater than the Line's, else -1
     * - otherwise, return 1 if the y coordinate of the Point lies above the Line, else -1
     * @param {Point} point - the point to compare
     * @returns {number} - -1|0|1
     */
    comparePoint(point) {
        if (this.contains(point)) {
            return 0;
        }
        if (this.slope() === Infinity) {
            return point.x > this.points[0].x ? 1 : -1;
        }
        if (this.slope() === 0) {
            return point.y > this.points[0].y ? 1 : -1;
        }
        return point.y > this.slope() * point.x + this.intercept() ? 1 : -1;
    }

    /**
     * Determines whether the given Point is on this Line, that is it satisfies:
     *  y = slope * x + intercept
     * @param {Point} point - a Point
     * @returns {boolean}
     */
    contains(point) {
        const s = this.slope();
        if (s === Infinity) {
            return this.equalWithin(point.x, this.points[0].x);
        }
        return this.equalWithin(point.y, s * point.x + this.intercept());
    }

    /**
     * Determines whether this Line is equal to another, according to the following criteria:
     *  - if the slopes of each are Infinite, and they have the same x coordinate, they are equal
     *  - otherwise, if they have the same slope and intercept, they are equal
     * @param {Line} line - a Line
     * @returns {boolean}
     */
    equals(line) {
        if (this.slope() === Infinity && line.slope() === Infinity) {
            return this.equalWithin(this.points[0].x, line.points[0].x);
        }
        return this.slope() === line.slope() && this.intercept() === line.intercept();
    }

    /**
     * The intercept of this Line. That is, "b" in the equation y = m * x + b
     * @returns {Point}
     */
    intercept() {
        return this.points[0].y - this.points[0].x * this.slope();
    }

    /**
     * The intersection of this Line and another
     * @returns {Point|null} - the intersection, or null if they do not intersect
     */
    intersection(line) {
        if (this.slope() === line.slope()) {
            if (this.equals(line)) {
                return this.points[0].x;
            }
            return null;
        }
        if (this.slope() === Infinity) {
            return new Point(this.points[0].x, line.slope() * this.points[0].x + line.intercept());
        }
        if (line.slope() === Infinity) {
            return new Point(line.points[0].x, this.slope() * line.points[0].x + this.intercept());
        }
        return new Point(
            (this.intercept() - line.intercept()) / (line.slope() - this.slope()),
            (line.slope() * this.intercept() - this.slope() * line.intercept()) / (line.slope() - this.slope())
        );
    }

    /**
     * The slope of this Line. That is, "m" in the equation y = m * x + b. If the Points defining the Line
     * have the same x coordinate, the slope is Infinite
     * @returns {number|Infinity}
     */
    slope() {
        return this.points[1].x === this.points[0].x ? Infinity :
            (this.points[1].y - this.points[0].y) / (this.points[1].x - this.points[0].x);
    }

    /**
     * String value of this Line
     * @returns {string}
     */
    toString() {
        return `
            slope ${this.slope()} intercept ${this.intercept()} (
            ${this.points.map(p => p.toString())}
            )
        `;
    }

    /**
     * Array comprising the difference between the x and y coordinates of the defining Points. Note that this
     * implies that e.g. [[0, 0], [1, 1]] and [[1, 1], [2, 2]] have the same toVector() value
     * @returns {[number]}
     */
    toVector() {
        return [this.points[0].x - this.points[1].x, this.points[0].y - this.points[1].y];
    }
}

/*
 * A 2-dimensional line segment defined by 2 points
 */
class LineSegment extends Line {
    /**
     * @param {Point} point1 - the 1st Point
     * @param {Point} point2 - the 2nd Point
    */
    constructor(point1, point2) {
        super(point1, point2);
    }

    /**
     * Determines whether the given Point is in this LineSegment
     * @param {Point} point - a Point
     * @returns {boolean}
     */
    contains(point) {
        const ext = this.extents();
        return super.contains(point) &&
            (this.gtOrEqualWithin(point.x, ext[0][0]) && this.ltOrEqualWithin(point.x, ext[0][1])) &&
            (this.gtOrEqualWithin(point.y, ext[1][0]) && this.ltOrEqualWithin(point.y, ext[1][1]));
    }

    /**
     * Determines whether this LineSegment is equal to another. Unlike Lines, equality is based only on
     * the equality of the Points
     * @param {LineSegment} lineSegment - a LineSegment
     * @returns {boolean}
     */
    equals(lineSegment) {
        return (this.points[0].equals(lineSegment.points[0]) && this.points[1].equals(lineSegment.points[1])) ||
            (this.points[0].equals(lineSegment.points[1]) && this.points[1].equals(lineSegment.points[0]));
    }

    /**
     * The extents of this LineSegment, that is [[minimum x, maximum x], [minimum y, maximum y]]
     * @returns {[[number]]}
     */
    extents() {
        const p = this.points;
        return [
            [Math.min(p[0].x, p[1].x), Math.max(p[0].x, p[1].x)],
            [Math.min(p[0].y, p[1].y), Math.max(p[0].y, p[1].y)]
        ];
    }

    /**
     * The length of this LineSegment
     * @returns {number}
     */
    length() {
        return this.points[0].dist(this.points[1]);
    }

    midpoint() {
        return new Point(
            (this.points[0].x + this.points[1].x) / 2,
            (this.points[0].y + this.points[1].y) / 2,
        );
    }

    /**
     * A filter to exclude Points not contained by this LineSegment
     * @returns {function}
     */
    pointFilter() {
        return p => this.contains(p);
    }

    /**
     * String value of this Line
     * @returns {string}
     */
    toString() {
        return this.points.map(p => p.toString()).join(' ');
    }
}


/*
 * A rectangle defined by 2 points
 */
class Rect extends GeometricObject {
    /**
     * @param {Point} diagPoint1 - the 1st Point
     * @param {Point} diagPoint2 - the 2nd Point
    */
    constructor(diagPoint1, diagPoint2) {
        super();

        /** @member {Point} - the 1st Point */
        this.diagPoint1 = diagPoint1;

        /** @member {Point} - the 2nd Point */
        this.diagPoint2 = diagPoint2;

        /** @member {[Point]} - array containing the Points */
        this.points = [diagPoint1, diagPoint2];
    }

    /**
     * The area of this Rect
     * @returns {number}
     */
    area() {
        return Math.abs(this.diagPoint2.x - this.diagPoint1.x) * Math.abs(this.diagPoint2.y - this.diagPoint1.y);
    }

    /**
     * Intersections of the given Line with the sides of this Rect
     * @param {Line} line - a Line
     * @returns {[Point]}
     */
    boundaryIntersectionsWithLine(line) {
        return this.sides()
            .map(s => s.intersection(line))
            .filter(p => p && this.containsPoint(p));
    }

    /**
     * Intersections of the LineSegment defined by given Points with the sides of this Rect
     * @param {Point} point1 - 1st Point
     * @param {Point} point2 - 2nd Point
     * @returns {[Point]}
     */
    boundaryIntersectionsWithPts(point1, point2) {
        return this.boundaryIntersectionsWithSeg(new LineSegment(point1, point2));
    }

    /**
     * Intersections of the given LineSegment with the sides of this Rect
     * @param {Point} point1 - 1st Point
     * @param {Point} point2 - 2nd Point
     * @returns {[Point]}
     */
    boundaryIntersectionsWithSeg(lineSegment) {
        return this.boundaryIntersectionsWithLine(lineSegment);
    }

    /**
     * The center of this Rect
     * @returns {Point}
     */
    center() {
        return new Point(
            this.points[0].x + (this.points[1].x - this.points[0].x) / 2,
            this.points[0].y + (this.points[1].y - this.points[0].y) / 2
        );
    }

    /**
     * Determines whether the given LineSegment lies entirely within this Rect
     * @param {LineSegment} lineSegment- a LineSegment
     * @returns {boolean}
     */
    containsLineSegment(lineSegment) {
        return this.containsPoint(lineSegment.points[0]) && this.containsPoint(lineSegment.points[1]);
    }

    /**
     * Determines whether the given Point is within this Rect
     * @param {Point} point- a Point
     * @returns {boolean}
     */
    containsPoint(point) {
        const c = this.corners();
        return point.x >= c[0].x && point.x <= c[2].x && point.y >= c[0].y && point.y <= c[2].y;
    }

    /**
     * Determines whether the given Rect lies entirely within this Rect
     * @param {Rect} rect - a Rect
     * @returns {boolean}
     */
    containsRect(rect) {
        const crn = rect.corners();
        for(const i in crn) {
            if (! this.containsPoint(crn[i])) {
                return false;
            }
        }
        return true;
    }

    /**
     * The corners of this Rect, sorted to go clockwise from (minx, miny) assuming standard axes directions
     * @returns {[Point]}
     */
    corners() {
        const c = [];
        for(const i in [0, 1]) {
            const p = this.points[i];
            for(const j in [0, 1]) {
                const q = this.points[j];
                c.push(new Point(p.x, q.y));
            }
        }
        c.sort((p1, p2) => {
            return p1.x > p2.x ? 1 :
                (p2.x > p1.x ? -1 : p1.y >= p2.y);
        });
        const swap = c[2];
        c[2] = c[3];
        c[3] = swap;
        return c;
    }

    /**
     * The height of this Rect
     * @returns {number}
     */
    height() {
        return this.sides()[0].length();
    }

    /**
     * Determines whether any part of the given Rect lies within this Rect
     * @param {Rect} rect - a Rect
     * @returns {boolean}
     */
    intersects(rect) {
        const rs = rect.sides();
        const ts = this.sides();
        for(const i in rs) {
            const rside = rs[i];
            for(const j in ts) {
                const tside = ts[j];
                if (rside.intersection(tside)) {
                    return true;
                }
            }
        }
        return false;
    }

    /**
     * A filter to exclude Points not contained by this Rect
     * @returns {function}
     */
    pointFilter() {
        return p => this.containsPoint(p);
    }

    /**
     * Filters the given LineSegments according to whether they lie inside this Rect
     * @param {[LineSegment]} lineSegments - an array of LineSegments to check
     * @returns {[LineSegment]}
     */
    segmentsInside(lineSegments) {
        return lineSegments.filter(l => this.containsLineSegment(l));
    }

    /**
     * The sides of this Rect as LineSegments between the corners
     * @returns {[LineSegment]}
     */
    sides() {
        const s = [];
        const c = this.corners();
        for(const i of [0, 1, 2, 3]) {
            s.push(new LineSegment(c[i], c[(i + 1) % 4]));
        }
        return s;
    }

    /**
     * String value of this Rect
     * @returns {string}
     */
    toString() {
        return GeometricObject.arrayString(this.points);
    }

    /**
     * The width of this Rect
     * @returns {number}
     */
    width() {
        return this.sides()[1].length();
    }
}

/**
 * Vector-specific utilities
 */
class VectorUtils {

    static dot(v1, v2) {
        return v1.reduce((prev, curr, i) => prev + curr * v2[i], 1);
    }

    static isZero(v) {
        return v.every(c => c === 0);
    }

    /**
     * Normalize a vector
     * @param {[number]} v
     * @returns {[number]}
     */
    static normalize(v) {
        return v.map(c => c / Math.hypot(...v));
    }

    /**
     * Add two vectors
     * @param {[number]} v1
     * @param {[number]} v2
     * @returns {[number]}
     */
    static add(v1, v2) {
        return this.combine(v1, v2, 1);
    }

    static combine(v1, v2, c) {
        return v1.map((x, i) => x + c * v2[i]);
    }

    static subtract(v1, v2) {
        return this.combine(v1, v2, -1);
    }
}

//TODO(mvk): change from service to classes
SIREPO.app.service('geometry', function(utilities) {

    var svc = this;

    this.basis = ['x', 'y', 'z'];
    this.basisVectors = {
        x: [1, 0, 0],
        y: [0, 1, 0],
        z: [0, 0, 1]
    };
    this.tolerance = 1e-4;

    // Returns the visible edge which is closest to the lower left corner
    this.bestEdgeInBounds = function(edges, boundingRect) {
        let res;
        const b = new Point(
            boundingRect.points[0].x,
            boundingRect.points[1].y,
        );
        for (const edge of edges) {
            if (edge && edge.points.filter(boundingRect.pointFilter()).length === 2) {
                if (res && b.dist(edge.midpoint()) > b.dist(res.midpoint())) {
                    continue;
                }
                res = edge;
            }
        }
        return res;
    };

    this.coordBounds = function(coords) {
        const l = coords[0].length;
        let b = (new Array(l)).fill({min: Number.MAX_VALUE, max: -Number.MAX_VALUE});
        for (let p of coords) {
            for (let x of ['min', 'max']) {
                for (let i = 0; i < l; ++i) {
                    b[i][x] = Math[x](b[i][x], p[i]);
                }
            }
        }
        return b;
    };

    // Returns the point(s) that have the smallest (reverse == false) or largest value in the given dimension
    this.extrema = function(points, dim, doReverse) {
        var arr = svc.sortInDimension(points, dim, doReverse);
        return arr.filter(function (point) {
            return point[dim] == arr[0][dim];
        });
    };

    this.geomObjArrStr = function(arr) {
        return '[' +
            arr.map(function (e) {
                var strFn = e.str;
                if (! strFn) {
                    return '<OBJ>';
                }
                return strFn();
        }) +
            ']';
    };

    // 2d only
    this.line = function(point1, point2) {
        return {
            containsPoint: function (p, tolerance) {
                // since we do math to see if the point satisfies the line's equation,
                // we need to specify how close we can get to account for rounding errors
                var t = tolerance || svc.tolerance;
                var s = this.slope();
                if (s === Infinity) {
                    return equalWithin(p.x, point1.x, t);
                }
                var y = s * p.x + this.intercept();

                return equalWithin(p.y, y, t);
            },
            equals: function (l2) {
                if (this.slope() === Infinity && l2.slope() === Infinity) {
                    return equalWithin(this.points()[0].x, l2.points()[0].x);
                }
                return this.slope() === l2.slope() && this.intercept() === l2.intercept();
            },
            intercept: function() {
                return point1.y - point1.x * this.slope();
            },
            intersection: function (l2) {
                if (this.slope() === l2.slope()) {
                    if (this.equals(l2)) {
                        return this.points()[0];
                    }
                    return null;
                }
                if (this.slope() === Infinity) {
                    return svc.point(point1.x, l2.slope() * point1.x + l2.intercept());
                }
                if (l2.slope() === Infinity) {
                    return svc.point(l2.points()[0].x, this.slope() * l2.points()[0].x + this.intercept());
                }
                return svc.point(
                    (this.intercept() - l2.intercept()) / (l2.slope() - this.slope()),
                    (l2.slope() * this.intercept() - this.slope() *l2.intercept()) / (l2.slope() - this.slope())
                );
            },
            comparePoint: function(p) {
                if (this.containsPoint(p)) {
                    return 0;
                }
                if (this.slope() === Infinity) {
                    return p.x > point1.x ? 1 : -1;
                }
                var y = this.slope() * p.x + this.intercept();
                return p.y > y ? 1 : -1;
            },
            points: function () {
                return [point1, point2];
            },
            slope: function() {
                return point2.x === point1.x ? Infinity : (point2.y - point1.y) / (point2.x - point1.x);
            },
            str: function () {
                return 'slope ' + this.slope() + ' intercept ' + this.intercept() + ' (' +
                    this.points().map(function (p) {
                    p.str();
                }) + ')';
            },
            vector: function () {
                return [point1.x - point2.x, point1.y - point2.y];
            },
        };
    };
    this.lineFromArr = function (arr) {
        return this.line(arr[0], arr[1]);
    };


    // 2d only
    this.lineSegment = function(point1, point2) {
        var ls = {
            ext: [
                [Math.min(point1.x, point2.x), Math.max(point1.x, point2.x)],
                [Math.min(point1.y, point2.y), Math.max(point1.y, point2.y)]
            ],
            p1: point1,
            p2: point2,
            l: svc.line(point1, point2)
        };

        ls.containsPoint = function (p) {
            var ext = this.extents();
            return this.line().containsPoint(p) &&
                (gtOrEqualWithin(p.x, ext[0][0]) && ltOrEqualWithin(p.x, ext[0][1])) &&
                (gtOrEqualWithin(p.y, ext[1][0]) && ltOrEqualWithin(p.y, ext[1][1]));
        };
        ls.equals = function (ls2) {
            var ps1 = this.points();
            var ps2 = ls2.points();
            return (equalWithin(ps1[0], ps2[0]) && equalWithin(ps1[1], ps2[1])) ||
                (equalWithin(ps1[0], ps2[1]) && equalWithin(ps1[1], ps2[0]));
        };
        ls.extents = function() {
            var pts = this.points();
            return [
                [Math.min(pts[0].x, pts[1].x), Math.max(pts[0].x, pts[1].x)],
                [Math.min(pts[0].y, pts[1].y), Math.max(pts[0].y, pts[1].y)]
            ];
        };
        ls.intercept = function() {
            return this.line().intercept();
        };
        ls.intersection = function (ls2) {
            var p = this.line().intersection(ls2.line());
            return p ? (this.containsPoint(p) && ls2.containsPoint(p) ? p : null) : null;
        };
        ls.length = function () {
            return point1.dist(point2);
        };
        ls.line = function() {
            return svc.line(this.p1, this.p2);
        };
        ls.pointFilter = function() {
            var ls = this;
            return function (point) {
                return ls.containsPoint(point);
            };
        };
        ls.points = function () {
            return [this.p1, this.p2];
        };
        ls.slope = function() {
            return this.line().slope();
        };
        ls.str = function () {
            return this.points().map(function (p) {
                return p.str();
            });
        };
        ls.update = function(newp1, newp2) {
            this.ext = [
                [Math.min(newp1.x, newp2.x), Math.max(newp1.x, newp2.x)],
                [Math.min(newp1.y, newp2.y), Math.max(newp1.y, newp2.y)]
            ];
            this.p1 = newp1;
            this.p2 = newp2;
            this.l = svc.line(newp1, newp2);
        };
        ls.vector = function () {
            return [this.p1.x - this.p2.x, this.p1.y - this.p2.y];
        };

        return ls;
    };

    this.matrixDet = function(matrix) {
        var d = 0;
        var len = matrix.length;
        if (len === 2) {
            d = matrix[0][0] * matrix[1][1] - matrix[1][0] * matrix[0][1];
            return d;
        }
        for(var i in matrix) {
            var t = 1;
            var s = 1;
            for(var j in matrix) {
                var k = (i + j) % len;
                var l = (i + len - j) % len;
                t *= matrix[j][k];
                s *= matrix[j][l];
            }
            d += (t - s);
        }
        return d;
    };

    this.matrixEquals = function(m1, m2) {
        if (m1.length !== m2.length) {
            return false;
        }
        for(var i in m1) {
            for(var j in m2) {
                if (! equalWithin(m1[i][j], m2[i][j])) {
                    return false;
                }
            }
        }
        return true;
    };

    this.matrixInvert = function(matrix) {
        var d = svc.matrixDet(matrix);
        if (! d) {
            return null;
        }
        var mx = svc.transpose(matrix);
        var inv = [];
        for (var i = 0; i < mx.length; ++i) {
            var row = mx[i];
            var invRow = [];
            var mult = 1;
            for(var j = 0; j < mx.length; ++j) {
                mult = Math.pow(-1,i + j);
                invRow.push((mult / d) * svc.matrixDet(svc.matrixMinor(mx, i, j)));
            }
            inv.push(invRow);
        }
        return inv;
    };

    this.matrixMinor = function(matrix, row, col) {
        var m = [];
        for(var i = 0; i < matrix.length; ++i) {
            var r = [];
            for(var j = 0; j < matrix.length; ++j) {
                if (i != row && j != col) {
                    r.push(matrix[i][j]);
                }
            }
            if (r.length > 0) {
                m.push(r);
            }
        }
        return m;
    };

    this.matrixMult = function(m1, m2) {
        var m = [];
        for(var i in m1) {
            var c = [];
            for(var j in m2) {
                c.push(m2[j][i]);
            }
            m.push(svc.vectorMult(m1, c));
        }
        return svc.transpose(m);
    };

    this.normalize = function(vector) {
        var n = Math.hypot(vector[0], vector[1], vector[2]);
        return vector.map(function (c) {
            return c / n;
        });
    };

    // Used for both 2d and 3d
    this.point = function(x, y, z) {
        return {
            x: x || 0,
            y: y || 0,
            z: z || 0,
            coords: function () {
                return [this.x, this.y, this.z];
            },
            dimension: function() {
                return 2 + (z === undefined ? 0 : 1);
            },
            dist: function (p2) {
                if (this.dimension() != p2.dimension()) {
                    throw new Error('Points in array have different dimensions: ' + this.dimension() + ' != ' + p2.dimension());
                }
                return Math.hypot(p2.x - this.x, p2.y - this.y, p2.z - this.z);
            },
            equals: function (p2) {
                var t = svc.tolerance;
                var d = 0.5 * (this.dist(this.zero()) + p2.dist(this.zero())) || 1.0;
                return this.dimension() == p2.dimension() && this.dist(p2) / d < t;
            },
            isInRect: function (r) {
                return r.containsPoint(this);
            },
            str: function () {
                return '(' + this.coords() + ')';  // + ' dimension ' + this.dimension();
            },
            zero: function () {
                if (this.dimension() === 2) {
                    return svc.point(0, 0);
                }
                return svc.point(0, 0, 0);
            }
        };
    };

    this.pointFromArr = function (arr) {
        return this.point(arr[0], arr[1], arr[2]);
    };

    // 2d only
    this.rect = function(diagPoint1, diagPoint2) {
        return {
            area: function () {
                return Math.abs(diagPoint2.x - diagPoint1.x) * Math.abs(diagPoint2.y - diagPoint1.y);
            },
            boundaryIntersectionsWithLine: function (l1) {
                var r = this;
                return r.sides()
                    .map(function (l2) {
                    return l1.intersection(l2);
                })
                    .filter(function (p) {
                        return p && r.containsPoint(p);
                    });
            },
            boundaryIntersectionsWithPts: function (point1, point2) {
                return this.boundaryIntersectionsWithSeg(svc.lineSegment(point1, point2));
            },
            boundaryIntersectionsWithSeg: function (lseg) {
                return this.boundaryIntersectionsWithLine(lseg.line());
            },
            center: function () {
                svc.point(
                    diagPoint1.x + (diagPoint2.x - diagPoint1.x) / 2,
                    diagPoint1.y + (diagPoint2.y - diagPoint1.y) / 2
                );
            },
            containsLineSegment: function (l) {
                return this.containsPoint(l.points()[0]) && this.containsPoint(l.points()[1]);
            },
            containsPoint: function (p) {
                var c = this.corners();
                return p.x >= c[0].x && p.x <= c[2].x && p.y >= c[0].y && p.y <= c[2].y;
            },
            containsRect: function (r) {
                var crn = r.corners();
                for(var i in crn) {
                    if (! this.containsPoint(crn[i])) {
                        return false;
                    }
                }
                return true;
            },
            // corners are sorted to go clockwise from (minx, miny) assuming standard axes directions
            corners: function() {
                var c = [];
                for(var i = 0; i < 2; i++) {
                    var p = this.points()[i];
                    for(var j = 0; j < 2; j++) {
                        var q = this.points()[j];
                        c.push(svc.point(p.x, q.y));
                    }
                }
                c.sort(function (p1, p2) {
                    return p1.x > p2.x ? 1 :
                        (p2.x > p1.x ? -1 : p1.y >= p2.y);
                });
                var swap = c[2];
                c[2] = c[3];
                c[3] = swap;
                return c;
            },
            height: function () {
                return this.sides()[0].length();
            },
            intersectsRect: function (r) {
                var rs = r.sides();
                var ts = this.sides();
                for(var i in rs) {
                    var rside = rs[i];
                    for(var j in ts) {
                        var tside = ts[j];
                        if (rside.intersection(tside)) {
                            return true;
                        }
                    }
                }
                return false;
            },
            pointFilter: function() {
                var r = this;
                return function (point) {
                    return r.containsPoint(point);
                };
            },
            points: function () {
                return [diagPoint1, diagPoint2];
            },
            segmentsInside: function(lines) {
                var r = this;
                return lines.filter(function (l) {
                    return r.containsLineSegment(l);
                });
            },
            sides: function () {
                var s = [];
                var crn = this.corners();
                for(var i = 0; i < 4; ++i) {
                    s.push(svc.lineSegment(crn[i], crn[(i + 1) % 4]));
                }
                return s;
            },
            str: function () {
                return svc.geomObjArrStr(this.points());
            },
            width: function () {
                return this.sides()[1].length();
            }
        };
    };

    // Sort (with optional reversal) the point array by the values in the given dimension;
    // Array is cloned first so the original is unchanged
    this.sortInDimension = function (points, dim, doReverse) {
        if (! points || ! points.length) {
            throw new Error(svc.geomObjArrStr(points) + ': Invalid points');
        }
        return points.slice(0).sort(function (p1, p2) {
            // throws an exception if the points have different dimensions
            p1.dist(p2);
            return (doReverse ? -1 : 1) * (p1[dim] - p2[dim]) / Math.abs(p1[dim] - p2[dim]);
        });
    };

    this.transform = function (matrix) {

        var identityMatrix = [
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1]
        ];
        var xform = {};

        // simple 3d operations, no need to import a whole matrix library
        function det(matrix) {
            return svc.matrixDet(matrix);
        }

        function trans(matrix) {
            return svc.transpose(matrix);
        }

        function vectorMult(m1, v) {
            var v2 = [];
            m1.forEach(function (row) {
                var c = 0;
                for(var i in row) {
                    c += row[i] * v[i];
                }
                v2.push(c);
            });
            return v2;
        }

        // multiplies in provided order ([M1] * [M2]), meaning M2 gets applied to vectors FIRST
        function matrixMult(m1, m2) {
            var m = [];
            for(var i in m1) {
                var c = [];
                for(var j in m2) {
                    c.push(m2[j][i]);
                }
                m.push(vectorMult(m1, c));
            }
            return trans(m);
        }

        function errMsg(s) {
            return matrix + ': ' + s;
        }

        xform.matrix = matrix || identityMatrix;

        var l = xform.matrix.length;
        if (l > 3 || l < 1) {
            throw new Error(errMsg('Matrix has bad size (' + l + ')'));
        }
        if (! xform.matrix.reduce(function (ok, row) {
                return ok && row.length == l;
            }, true)
        ) {
            throw new Error(errMsg('Matrix is not square'));
        }
        if (det(xform.matrix) === 0) {
            throw new Error(errMsg('Matrix is not invertable'));
        }

        xform.compose = function (otherXForm) {
            if (otherXForm.matrix.length !== l) {
                throw new Error(errMsg('Matrices must be same size (' + l + ' != ' + otherXForm.matrix.length));
            }
            return svc.transform(matrixMult(xform.matrix, otherXForm.matrix));
        };

        xform.composeFromMatrix = function(m) {
            return xform.compose(svc.transform(m));
        };

        xform.det = function() {
            return det(xform.matrix);
        };

        xform.doTransform = function(coords) {
            return vectorMult(xform.matrix, coords);
        };

        xform.doTX = function(point) {
            return svc.pointFromArr(
                xform.doTransform(point.coords())
            );
        };

        xform.equals = function(otherXForm) {
            return svc.matrixEquals(xform.matrix, otherXForm.matrix);
        };

        xform.inverse = function() {
            return svc.transform(svc.matrixInvert(xform.matrix));
        };

        xform.str = function () {
            var str = '[';
            for(var i in xform.matrix) {
                var rstr = '[';
                for(var j in xform.matrix[i]) {
                    rstr += xform.matrix[i][j];
                    rstr += (j < xform.matrix[i].length - 1 ? ', ' : ']');
                }
                str += rstr;
                str += (i < xform.matrix.length -1  ? ', ' : ']');
            }
            return str;
        };

        return xform;
    };

    this.transpose = function (matrix) {
        var m = [];
        var l = matrix.length;
        if (! l ) {
            return m;
        }
        // convert 1 x l into l x 1
        var ll = matrix[0].length;
        if (ll == 0) {
            matrix.forEach(function (entry) {
                m.push([entry]);
            });
            return m;
        }
        for(var j = 0; j < ll; ++j) {
            var r = [];
            for(var i = 0; i < l; ++i) {
                r.push(matrix[i][j]);
            }
            m.push(r);
        }
        return m;
    };

    this.vectorMult = function (m1, v) {
        var v2 = [];
        m1.forEach(function (row) {
            var c = 0;
            for(var i in row) {
                c += row[i] * v[i];
            }
            v2.push(c);
        });
        return v2;
    };

    // numbers are to be considered equal if they differ by less than this
    function equalWithin(val1, val2, tolerance) {
        var tol = tolerance || svc.tolerance;
        return Math.abs(val2 - val1) < tol;
    }

    function gtOrEqualWithin(val1, val2, tolerance) {
        return val1 > val2 || equalWithin(val1, val2, tolerance);
    }

    function ltOrEqualWithin(val1, val2, tolerance) {
        return val1 < val2 || equalWithin(val1, val2, tolerance);
    }
});

SIREPO.GEOMETRY = {
    AffineMatrix: AffineMatrix,
    GeometricObject: GeometricObject,
    GeometryUtils: GeometryUtils,
    IdentityMatrix: IdentityMatrix,
    Line: Line,
    LineSegment: LineSegment,
    Matrix: Matrix,
    Plane: Plane,
    Point: Point,
    Rect: Rect,
    ReflectionMatrix: ReflectionMatrix,
    RotationMatrix: RotationMatrix,
    SquareMatrix: SquareMatrix,
    Transform: Transform,
    TranslationMatrix: TranslationMatrix,
};
