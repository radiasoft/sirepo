class SirepoUtils {

    static camelToKebabCase(v) {
        v = v.charAt(0).toLowerCase() + v.slice(1);
        return v.replace(/([A-Z])/g, '-$1').toLowerCase();
    }

    static wordSplits(str) {
        var wds = str.split(/(\s+)/);
        return wds.map(function (value, index) {
            return wds.slice(0, index).join('') + value;
        });
    }


    static indexArray(size) {
        var res = [];
        for (var i = 0; i < size; res.push(i++)) {}
        return res;
    }

    static normalize(seq) {
        var sMax = Math.max.apply(null, seq);
        var sMin = Math.min.apply(null, seq);
        var sRange = sMax - sMin;
        sRange = sRange > 0 ? sRange : 1.0;
        return seq.map(function (v) {
            return (v - sMin) / sRange;
        });
    }

    static roundToPlaces(val, p) {
        if (p < 0) {
            return val;
        }
        var r = Math.pow(10, p);
        return Math.round(val * r) / r;
    }

    // returns an array containing the unique elements of the input,
    // according to a two-input equality function (null means use ===)
    static unique(arr, equals) {
        var uniqueArr = [];
        arr.forEach(function (a, i) {
            var found = false;
            for(var j = 0; j < uniqueArr.length; ++j) {
                var b = uniqueArr[j];
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
