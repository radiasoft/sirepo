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
     * Sort (with optional reversal) the point array by the values in the given dimension.
     * Array is cloned first so the original is unchanged
     * @param {[Point]} points - the points to sort
     * @param {string} dim - the dimension in which to sort (x|y|z)
     * @param {boolean} doReverse [false] - if true, reverses the sort order
     * @returns {[Point]}
     */
    static sortInDimension(points, dim, doReverse = false) {
        return points.slice(0).sort((p1, p2) => {
            // throws an exception if the points have different dimensions
            p1.dist(p2);
            return (doReverse ? -1 : 1) * (p1[dim] - p2[dim]) / Math.abs(p1[dim] - p2[dim]);
        });
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
        return Math.abs(val2 - val1) < this.equalityTolerance;
    }

    /**
     * Determines if one value is greater than another relative to the equalityTolerance of this object
     * @param {number} val1 - 1st value
     * @param {number} val2 - 2nd value
     * @returns {boolean}
     */
    gtOutside(val1, val2) {
        return val1 - val2 > this.equalityTolerance;
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
     * Determines if one value is less than another relative to the equalityTolerance of this object
     * @param {number} val1 - 1st value
     * @param {number} val2 - 2nd value
     * @returns {boolean}
     */
    ltOutside(val1, val2) {
        return val2 - val1 > this.equalityTolerance;
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
            return new Matrix(this.val.map((x, i) => x * constant * matrix.val[i]));
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
            return this.val.reduce((sum, x, i) => sum + x * matrix.val[i], 0);
        }

        if (this.numRows !== matrix.numCols) {
            throw new Error(this.errorMessage(`numRows must equal argument's numCols (${this.numRows} != ${matrix.numCols})`));
        }

        // matrix * vector
        if (matrix.dimension === 1) {
            let v = [];
            for (let x of this.val) {
                v.push((new Matrix(x)).multiply(matrix));
            }
            return new Matrix(v);
        }

        // matrix * matrix
        let m = [];
        for(let i in this.val) {
            let c = [];
            for(let j in matrix.val) {
                c.push(matrix.val[j][i]);
            }
            m.push(this.multiply(new Matrix(c)).val);
        }
        return (new Matrix(m)).transpose();
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
        for (let i = 0; i < mx.length; ++i) {
            let invRow = [];
            let mult = 1;
            for(let j = 0; j < mx.length; ++j) {
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
}

/*
 * The 2-dimensional identity matrix
 */
class IdentityMatrix extends SquareMatrix {
    constructor() {
        super([[1, 0, 0], [0, 1, 0], [0, 0, 1]]);
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
        return [this.x, this.y, this.z];
    }

    /**
     * Distance to another Point
     * @param {Point} point - another Point
     * @returns {number}
     * @throws - if the two points have different dimensions
     */
    dist(point) {
        if (this.dimension != point.dimension) {
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
     * Compares a given Point to this line, in the following sense:
     * - if the Point is on this Line, return 0
     * - if the Line is vertical, return 1 if the x coordinate of the Point is greater than the Line's, else -1
     * - otherwise, return 1 if the y coordinate of the Point lies above the Line, else -1
     * @returns {number} - -1|0|1
     */
    comparePoint(point) {
        if (this.contains(point)) {
            return 0;
        }
        if (this.slope() === Infinity) {
            return point.x > this.points[0].x ? 1 : -1;
        }
        return point.y > this.slope() * point.x + this.intercept() ? 1 : -1;
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
     * The intersection of this LineSegment and another, or null if they do not intersect. Note that
     * they must intersect in the sense of Lines, and that intersection must line on the segments
     * @param {LineSegment} lineSegment - a LineSegment
     * @returns {Point|null}
     */
    intersectionWithSegment(lineSegment) {
        const p = this.intersection(lineSegment);
        return p ? (this.contains(p) && lineSegment.contains(p) ? p : null) : null;
    }

    /**
     * The length of this LineSegment
     * @returns {number}
     */
    length() {
        return this.points[0].dist(this.points[1]);
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
        return this.points.map(p => p.toString());
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

    this.bestEdgeAndSectionInBounds = function(edges, boundingRect, dim, reverse) {
        let edge;
        let section;
        for(const i in edges) {
            edge = edges[i];
            section = sectionOfEdgeInBounds(edge, boundingRect, dim, reverse);
            if (section) {
                return {
                    full: edge,
                    clipped: section,
                    index: i
                };
            }
        }
        return null;
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
    this.lineSegmentFromArr = function (arr) {
        return this.lineSegment(arr[0], arr[1]);
    };

    this.matrixAdd = function (matrix1, matrix2) {
        var m = [];
        matrix1.forEach(function (row1, i) {
            m.push(this.vectorAdd(row1, matrix2[i]));
        });
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

    // norm is a vector (array), point is a geometry.point
    // planes have the equation Ax + By + Cz = D
    this.plane = function(norm, point) {
        if (isVectorZero(norm)) {
            throw new Error('Must specify a non-zero plane normal: ' + norm);
        }
        var pCoords = point.coords();
        var pl = {
            A: norm[0],
            B: norm[1],
            C: norm[2],
            D: svc.vectorDot(norm, pCoords),
            norm: norm,
            point: point,
            pointCoords: pCoords,
        };
        pl.closestPointToPoint = function(p) {
            var d = this.distToPoint(p, true);
            var n = this.normalized();
            var pc = p.coords();
            return svc.pointFromArr([
                pc[0] - d * n[0], pc[1] - d * n[1], pc[2] - d * n[2]
            ]);
        };
        pl.containsPoint = function(p) {
            return equalWithin(svc.vectorDot(norm, p.coords()), this.D);
        };
        pl.distToPoint = function(p, signed) {
            var pc = p.coords();
            var d = (1 / Math.hypot(norm[0], norm[1], norm[2])) *
                (norm[0] * pc[0] + norm[1] * pc[1] + norm[2] * pc[2] - this.D);
            return signed ? d : Math.abs(d);
        };
        pl.equals = function(pl2) {
            if (! this.isParallelTo(pl2)) {
                return false;
            }
            return this.D === pl2.D;
        };
        pl.intersection = function (pl2) {
            if (this.equals(pl2)) {
                // planes are equal, return an arbitrary line containing the point
                // need ensure they are not the same point!  Use random number?
                return svc.line(point, this.pointInPlane());
            }
            // parallel but not equal, there is no intersection
            if (this.isParallelTo(pl2)) {
                return null;
            }
            var p1 = this.paramLine(pl2)(0);  // random t?
            var p2 = this.paramLine(pl2)(1);
            return svc.line(svc.pointFromArr(p1), svc.pointFromArr(p2));
        };
        pl.intersectsLine = function (l) {
            var pts = l.points();
            var p1 = pts[0].coords();
            var p2 = pts[1].coords();
            var lv = [p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]];
            var dp = svc.vectorDot(lv, norm);
            if (dp !== 0) {
                return true;
            }
            var pp = this.pointInPlane().coords();
            var d = [pp[0] - p1[0], pp[1] - p1[1], pp[2] - p1[2]];
            dp = svc.vectorDot(d, norm);
            return dp === 0;
        };
        pl.isParallelTo = function(pl2) {
            return equalWithin(this.A, pl2.A) &&
                equalWithin(this.B, pl2.B) &&
                equalWithin(this.C, pl2.C);
        };
        pl.mirrorPoint = function(p) {
            var cp = this.closestPointToPoint(p).coords();
            var d = this.distToPoint(p, true);
            var n = this.normalized();
            return svc.pointFromArr([
                cp[0] - d * n[0],  cp[1] - d * n[1],  cp[2] - d * n[2]
            ]);
        };
        pl.normalized = function() {
            return svc.normalize([this.A, this.B, this.C]);
            //var n = Math.hypot(this.A, this.B, this.C);
            //return [this.A / n, this.B / n, this.C / n];
        };
        pl.paramLine = function(pl2, t) {
            // makes for symmetric equations below
            var pl1 = this;
            var freeIndex = 0;
            var i = 1;
            var j = 2;
            var d = 0;
            for (freeIndex = 0; freeIndex < 3; ++freeIndex) {
                i = (freeIndex + 1) % 3;
                j = (freeIndex + 2) % 3;
                d = pl1.norm[i] * pl2.norm[j] - pl1.norm[j] * pl2.norm[i];
                if (d !== 0) {
                    break;
                }
            }
            return function (t) {
                var p = [0, 0, 0];
                p[freeIndex] = t;
                p[i] = ((pl2.norm[j] * pl1.D - pl1.norm[j] * pl2.D) +
                    t * (pl1.norm[j] * pl2.norm[freeIndex] - pl2.norm[j] * pl1.norm[freeIndex])) / d;
                p[j] = ((pl1.norm[i] * pl2.D - pl2.norm[i] * pl1.D) +
                    t * (pl1.norm[i] * pl2.norm[freeIndex] - pl2.norm[i] * pl1.norm[freeIndex])) / d;
                return p;
            };
        };
        pl.pointInPlane = function(fixedVal) {
            if (fixedVal !==0 && ! fixedVal) {
                fixedVal = 1;
            }
            // check if plane norm is along a basis vector - if so, any values in the remaining coords
            // satisfy the plane's equation
            var ones = [1, 1, 1];
            for (var dim in svc.basisVectors) {
                var v = svc.basisVectors[dim];
                if (svc.vectorDot(v, this.normalized()) === 1) {
                    return svc.pointFromArr(svc.vectorSubtract(ones, v));
                }
            }
            // if a coord is 0 - can't all be 0 so at most one - the equation of the plane
            // is also the equation of a line.  If no coords are 0 we can arbitrarily set z to 0
            var non0 = [[1, 2], [0, 2], [0, 1]];
            var ptArr = [0, 0, 0];
            var zIdx = norm.indexOf(0);
            zIdx = zIdx >= 0 ? zIdx : 2;
            var nzIdxs = non0[zIdx];
            ptArr[nzIdxs[0]] = fixedVal;
            ptArr[nzIdxs[1]] = -fixedVal * norm[nzIdxs[0]] / norm[nzIdxs[1]];
            return svc.pointFromArr(ptArr);
        };
        if (! pl.containsPoint(point)) {
            throw new Error('Plane does not contain point: ' + point.coords());
        }
        return pl;
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

    // construct from array of points, assumed to be in "drawing order"
    this.polygon = function (pts) {

        if (pts.length < 3) {
            throw new Error('A polygon requires at least 3 points (' + pts.length + ' provided)');
        }

        /*
        var bounds = {};
        svc.basis.forEach(function (dim) {
            bounds[dim] = {};
            var d = pts.map(function (pt) {
                return pt[dim];
            });
            bounds[dim].min = Math.min.apply(null, d);
            bounds[dim].max = Math.max.apply(null, d);
        });
        */

        //var boundaryRect = svc.rect(svc.point(bounds.x.min, bounds.y.min), svc.point(bounds.x.max, bounds.y.max));

        var sides = Array(pts.length);
        pts.forEach(function (pt, ptIdx) {
            //sides[ptIdx] = svc.lineSegment(pts[(ptIdx + 1) % pts.length], pt);
            sides[ptIdx] = [pts[(ptIdx + 1) % pts.length], pt];
        });

        // static properties set at init
        var poly = {
            //bounds: bounds,
            points: pts,
            //boundaryRect: boundaryRect,
            sides: sides,
        };

        // "ray casting" simplified
        poly.containsPoint = function(pt) {
            // count sides whose endpoints are above/below the input point and have least one endpoint to the left
            // - implies a ray starting at -Infinity crosses that many sides
            return sides.filter(function (ls) {
                return (ls[0][1] > pt[1] !== ls[1][1] > pt[1]) &&
                    (ls[0][0] < pt[0] || ls[1][0] < pt[0]);
                //return (ls.p1.y > pt.y !== ls.p2.y > pt.y) &&
                //    (ls.p1.x < pt.x || ls.p2.x < pt.x);
            }).length  % 2 === 1;
        };

        // should start separating "dynamic" from "static" - if points are not expected to change there is
        // no reason to recalculate everything.  Maybe an argument?
        /*
        poly.getBoundaryRect = function() {
            var b = this.bounds();
            return svc.rect(svc.point(b.x.min, b.y.min), svc.point(b.x.max, b.y.max));
        };

        poly.getBounds = function() {
            var b = {};
            svc.basis.forEach(function (dim) {
                var d = pts.map(function (pt) {
                    return pt[dim];
                });
                b[dim] = {};
                b[dim].min = Math.min.apply(null, d);
                b[dim].max = Math.max.apply(null, d);
            });
            return b;
        };

        poly.getPoints = function () {
            return pts;
        };

        poly.getSides = function() {
            var ls = Array(pts.length);
            pts.forEach(function (pt, ptIdx) {
                ls[ptIdx] = svc.lineSegment(pts[(ptIdx + 1) % pts.length], pt);
            });
            return ls;
        };
        */
        return poly;
    };

    this.polyFromArr = function (arr) {
        return this.polygon(arr.map(function (c) {
            return svc.pointFromArr(c);
        }));
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

    this.rectFromArr = function (arr) {
        return svc.rect(svc.pointFromArr(arr[0]), svc.pointFromArr(arr[1]));
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

    // for rotation about arbitrary axis - note this is 4 x 4 and will need to multiply a vector [x, y, z, 0]
    this.rotationMatrix = function(pointCoords, vector, angle) {
        var cs = Math.cos(angle);
        var cs1 = 1 - cs;
        var s = Math.sin(angle);

        var A = pointCoords[0];
        var B = pointCoords[1];
        var C = pointCoords[2];

        var nv = svc.normalize(vector);
        var u = nv[0];
        var v = nv[1];
        var w = nv[2];
        return [
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

    // we will use "vector" to mean an array of numbers, and "point" to be an object
    // that wraps coordinates and defines methods to manipulated them
    this.vectorAdd = function (vector1, vector2) {
        return this.vectorLinearCombination(vector1, vector2, 1);
    };


    this.vectorCross = function (vector1, vector2) {
        if (vector1.length !== 3 || vector2.length !== 3) {
            throw new Error('Vectors must be dimension 3: ' + vector1, vector2);
        }
        var c = [];
        for (var dim in svc.basisVectors) {
            var v = svc.basisVectors[dim];
            var d = svc.matrixDet([v, vector1, vector2]);
            c.push(d);
        }
        return c;
    };

    this.vectorDot = function (vector1, vector2) {
        return vector1[0] * vector2[0] + vector1[1] * vector2[1] + vector1[2] * vector2[2];
    };

    this.vectorLinearCombination = function (vector1, vector2, constant) {
        var v = [];
        vector1.forEach(function (el1, i) {
            v.push(el1 + constant * vector2[i]);
        });
        return v;
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

    this.vectorSubtract = function (vector1, vector2) {
        return this.vectorLinearCombination(vector1, vector2, -1);
    };


    // numbers are to be considered equal if they differ by less than this
    function equalWithin(val1, val2, tolerance) {
        var tol = tolerance || svc.tolerance;
        return Math.abs(val2 - val1) < tol;
    }

    function gtOutside(val1, val2, tolerance) {
        var tol = tolerance || svc.tolerance;
        return val1 - val2 > tol;
    }

    function gtOrEqualWithin(val1, val2, tolerance) {
        return val1 > val2 || equalWithin(val1, val2, tolerance);
    }

    function isVectorZero(vector) {
        return vector.every(function (c) {
            return c === 0;
        });
    }

    function ltOutside(val1, val2, tolerance) {
        var tol = tolerance || svc.tolerance;
        return val2 - val1 > tol;
    }

    function ltOrEqualWithin(val1, val2, tolerance) {
        return val1 < val2 || equalWithin(val1, val2, tolerance);
    }

    function sectionOfEdgeInBounds(edge, boundingRect, dim, reverse) {

        if (! edge) {
            return null;
        }

        // edgeEndsInBounds are the coordinates of the ends of the selected edge are on or inside the
        // boundary rectangle
        const edgeEndsInBounds = edge.points.filter(boundingRect.pointFilter());

        // projectedEnds are the 4 points where the boundary rectangle intersects the
        // *line* defined by the selected edge
        const projectedEnds = boundingRect.boundaryIntersectionsWithSeg(edge);

        // if the selected edge does not intersect the boundary, it
        // means both ends are off screen; so, reject it
        if (projectedEnds.length === 0) {
            return null;
        }

        // now we have any edge endpoint that is in or on the boundary, plus
        // the points projected to the boundary
        // get all of those points that also lie on the selected edge
        const ap = edgeEndsInBounds.concat(projectedEnds);
        const allPoints = edgeEndsInBounds.concat(projectedEnds).filter(edge.pointFilter());
        const uap = utilities.unique(allPoints, (p1, p2) => p1.equals(p2));
        if (uap.length < 2) {  // need 2 points to define the line segment
            return null;
        }
        const section = new SIREPO.GEOMETRY.LineSegment(
            ...SIREPO.GEOMETRY.GeometryUtils.sortInDimension(uap, dim, reverse)
        );

        if (edgeEndsInBounds.length === 0) {
            return section;
        }

        // if the edge is showing and the line segment is too short (here half the length of the actual edge),
        // do not use it
        if (section.length() / edge.length() > 0.5) {
            return section;
        }
        return null;
    }


});

SIREPO.GEOMETRY = {
    GeometricObject: GeometricObject,
    GeometryUtils: GeometryUtils,
    IdentityMatrix: IdentityMatrix,
    LineSegment: LineSegment,
    Matrix: Matrix,
    Point: Point,
    Rect: Rect,
    SquareMatrix: SquareMatrix,
    Transform: Transform,
};
