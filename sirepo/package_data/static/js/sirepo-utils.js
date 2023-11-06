'use strict';

class SirepoUtils {

    static camelToKebabCase(v) {
        v = v.charAt(0).toLowerCase() + v.slice(1);
        return v.replace(/([A-Z])/g, '-$1').toLowerCase();
    }

    static capitalize(s) {
        return s.charAt(0).toUpperCase() + s.slice(1);
    }

    static orderOfMagnitude(val, binary=false) {
        const MAGS = ['', 'k', 'M', 'G', 'T', 'P', 'E'];
        const v = Math.abs(val);
        const base = binary ? 1024 : 1000;
        const i = binary ? Math.floor(Math.log2(v) / 10) : Math.floor(Math.log10(v) / 3);
        return {
            order: i,
            suffix: MAGS[Math.max(Math.min(i, MAGS.length - 1), 0)] + ((binary && i > 0) ? 'i' : ''),
            mantissa: Math.sign(val) * v / Math.pow(base, i),
        };
    }

    static formatFloat(val, decimals) {
        return +parseFloat(val).toFixed(decimals);
    }

    static formatToThousands(val, decimals, binary=false) {
        return SirepoUtils.formatFloat(SirepoUtils.orderOfMagnitude(val, binary).mantissa, decimals);
    }

    static indexArray(size, offset=0) {
        const res = [];
        for (let i = 0; i < size; res.push(offset + i++)) {}
        return res;
    }

    /**
     * The min value of an array
     * @param {number[]} array
     * @returns {number}
     */
    static arrayMin(array) {
        return this.applyInChunks(Math.min, array, Number.MAX_VALUE);
    }

    /**
     * The max value of an array
     * @param {number[]} array
     * @returns {number}
     */
    static arrayMax(array) {
        return this.applyInChunks(Math.max, array, -Number.MAX_VALUE);
    }

    // regular cloning etc. does not include methods on class instances
    static copyInstance(o, excludedProperties=[]) {
        const c = new o.constructor();
        // NOTE: structuredClone is recommended, but not defined according to the current jslinter
        const s = JSON.parse(JSON.stringify(o));  //structuredClone(o);
        for (const p in s) {
            if (excludedProperties.includes(p)) {
                continue;
            }
            c[p] = s[p];
        }
        return c;
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

    static linearToLog(val, min, max, step) {
        const bin = Math.floor(Math.abs(val - min) / step);
        const n = Math.abs(max - min) / step;
        const lv = (bin * Math.log10(max) + (n - bin) * Math.log10(min)) / n;
        return 10**lv;
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

    static randomString(length=32) {
        const BASE62 = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz';
        return new Array(length)
            .fill('')
            .map(x => BASE62[Math.floor(BASE62.length * Math.random())])
            .join('');
    }

    static roundToPlaces(val, p) {
        if (p < 0) {
            return val;
        }
        const r = Math.pow(10, p);
        return Math.round(val * r) / r;
    }

    /**
     * Functions that take "varargs" (e.g. Math.min) can break the stack if the number of args is too
     * large. This applies the function to an array in chunks to avoid such cases
     * @param {function} fn - the function to apply
     * @param {*[]} array - the array of interest
     * @param {*} initVal - default return value for empty arrays
     * @returns {*}
     */
    static applyInChunks(fn, arr, initVal) {
        let res = initVal;
        let i = 0;
        while (i < arr.length) {
            const j = Math.min(i + 1000, arr.length);
            const sub = fn.apply(null, arr.slice(i, j));
            res = fn.apply(null, [res, sub]);
            i = j;
        }
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

    static reshape(arr, dims) {
        if (dims.length === 0) {
            return arr;
        }
        const a = Array.from(arr).slice();
        if (dims.length === 1) {
            return a;
        }
        const n = dims.reduce((p, c) => p * c, 1);
        if (a.length !== n) {
            throw new Error(`Product of shape dimensions must equal array length: ${a.length} != ${n}`);
        }
        const b = [];
        const d = dims[0];
        const m = a.length / d;
        for (let i = 0; i < d; ++i) {
            const s = a.slice(m * i, m * (i + 1));
            b.push(SirepoUtils.reshape(s, dims.slice(1)));
        }
        return b;
    }

    static wordSplits(s) {
        const wds = s.split(/(\s+)/);
        return wds.map(function (value, index) {
            return wds.slice(0, index).join('') + value;
        });
    }
}

SIREPO.UTILS = SirepoUtils;
