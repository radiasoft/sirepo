
class Util {
    clone(obj) {
        return window.structuredClone
             ? window.structuredClone(obj)
             : JSON.parse(JSON.stringify(obj));
    }

    deepEquals(v1, v2) {
        if (v1 === v2) {
            return true;
        }
        if (this.isArray(v1) && this.isArray(v2)) {
            if (v1.length !== v2.length) {
                return false;
            }
            for (let i = 0; i < v1.length; i++) {
                if (! this.deepEquals(v1[i], v2[i])) {
                    return false;
                }
            }
            return true;
        }
        if (this.isObject(v1) && this.isObject(v2)) {
            const keys = Object.keys(v1);
            if (keys.length !== Object.keys(v2).length) {
                return false;
            }
            return ! keys.some(k => ! this.deepEquals(v1[k], v2[k]));
        }
        return v1 == v2;
    }

    isArray(arr) {
        return Array.isArray(arr) || arr instanceof Array;
    }

    isObject(value) {
        return value !== null && typeof value === 'object';
    }
}

export const util = new Util();
