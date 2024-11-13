'use strict';

class SirepoUtils {

    static arrayMax(array) {
        let m;
        for (const v of array) {
            if (m === undefined || v > m) {
                m = v;
            }
        }
        return m;
    }

    static arrayMin(array) {
        let m;
        for (const v of array) {
            if (m === undefined || v < m) {
                m = v;
            }
        }
        return m;
    }

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

    static linearToLog(val, min, max, nsteps) {
        if (val === min || val === max) {
            return val;
        }
        const bin = Math.floor(Math.abs(val - min) / ((max - min) / nsteps));
        const n = (Math.log10(max) - Math.log10(min)) / nsteps;
        return 10 ** (Math.log10(min) + bin * n);
    }

    static normalize(seq) {
        const sMax = SirepoUtils.arrayMax(seq);
        const sMin = SirepoUtils.arrayMin(seq);
        let sRange = sMax - sMin;
        sRange = sRange > 0 ? sRange : 1.0;
        return seq.map(function (v) {
            return (v - sMin) / sRange;
        });
    }

    static randomId() {
        return 'sr' + SirepoUtils.randomString();
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

    static minForIndex(arr, i) {
        return SirepoUtils.arrayMin(arr.map(x => x[i]));
    }

    static wordSplits(s) {
        const wds = s.split(/(\s+)/);
        return wds.map(function (value, index) {
            return wds.slice(0, index).join('') + value;
        });
    }
}

SIREPO.UTILS = SirepoUtils;
