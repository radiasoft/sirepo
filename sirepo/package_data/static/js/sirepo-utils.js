'use strict';

class SirepoUtils {

    static camelToKebabCase(v) {
        v = v.charAt(0).toLowerCase() + v.slice(1);
        return v.replace(/([A-Z])/g, '-$1').toLowerCase();
    }

    static capitalize(s) {
        return s.charAt(0).toUpperCase() + s.slice(1);
    }

    static indexArray(size) {
        const res = [];
        for (let i = 0; i < size; res.push(i++)) {}
        return res;
    }

    /**
     * The min value of an array too large for Math.min
     * @param {number[]} array
     * @returns {number}
     */
    static largeMin(array) {
        return this.seqApply(Math.min, array, Number.MAX_VALUE);
    }

    /**
     * The max value of an array too large for Math.max
     * @param {number[]} array
     * @returns {number}
     */
    static largeMax(array) {
        return this.seqApply(Math.max, array, -Number.MAX_VALUE);
    }

    static linearlySpacedArray(start, stop, nsteps) {
        if (nsteps < 1) {
            throw new Error("linearlySpacedArray: steps " + nsteps + " < 1");
        }
        const delta = (stop - start) / (nsteps - 1);
        const res = d3.range(nsteps).map(function(d) { return start + d * delta; });
        res[res.length - 1] = stop;

        if (res.length !== nsteps) {
            throw new Error("linearlySpacedArray: steps " + nsteps + " != " + res.length);
        }
        return res;
    }

    static normalize(seq) {
        const sMax = Math.max.apply(null, seq);
        const sMin = Math.min.apply(null, seq);
        let sRange = sMax - sMin;
        sRange = sRange > 0 ? sRange : 1.0;
        return seq.map(function (v) {
            return (v - sMin) / sRange;
        });
    }

    static roundToPlaces(val, p) {
        if (p < 0) {
            return val;
        }
        const r = Math.pow(10, p);
        return Math.round(val * r) / r;
    }

    /**
     * Some functions that take array arguments (e.g. Math.min) can break the stack if the array is too
     * large. This applies the function in chunks to avoid such cases
     * @param {function} fn - the function to apply
     * @param {*[]} array - the array of interest
     * @param {*} initVal - default return value for empty arrays
     * @returns {*}
     */
    static seqApply(fn, arr, initVal) {
        let start = 0;
        const inc = 1000;
        let res = initVal;
        do {
            const sub = fn.apply(null, arr.slice(start, Math.min(arr.length, start + inc)));
            res = fn.apply(null, [res, sub]);
            start += inc;
        } while (start < arr.length);

        return res;
    }

    // returns an array containing the unique elements of the input,
    // according to a two-input equality function (null means use ===)
    static unique(arr, equals) {
        const uniqueArr = [];
        arr.forEach(function (a, i) {
            let found = false;
            for(let j = 0; j < uniqueArr.length; ++j) {
                const b = uniqueArr[j];
                found = equals ? equals(a, b) : a === b;
                if (found) {
                    break;
                }
            }
            if (! found) {
                uniqueArr.push(a);
            }
        });
        return uniqueArr;
    }

    static maxForIndex(arr, i) {
        return Math.max(...arr.map(x => x[i]));
    }

    static minForIndex(arr, i) {
        return Math.min(...arr.map(x => x[i]));
    }

    static wordSplits(s) {
        const wds = s.split(/(\s+)/);
        return wds.map(function (value, index) {
            return wds.slice(0, index).join('') + value;
        });
    }
}

SIREPO.UTILS = SirepoUtils;
