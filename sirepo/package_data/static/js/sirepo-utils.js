class SirepoUtils {

    static camelToKebabCase(v) {
        v = v.charAt(0).toLowerCase() + v.slice(1);
        return v.replace(/([A-Z])/g, '-$1').toLowerCase();
    }

    static capitalize(s) {
        return s.charAt(0).toUpperCase() + s.slice(1);
    }

    static wordSplits(s) {
        const wds = s.split(/(\s+)/);
        return wds.map(function (value, index) {
            return wds.slice(0, index).join('') + value;
        });
    }

    static indexArray(size) {
        const res = [];
        for (let i = 0; i < size; res.push(i++)) {}
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

}

SIREPO.UTILS = SirepoUtils;
