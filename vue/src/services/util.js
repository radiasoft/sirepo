import { singleton } from '@/services/singleton.js';

class Util {
    uniqueIdCount = 0;
    _dateFormat = Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: 'numeric',
    });

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
        return v1 === v2;
    }

    formatDate(pythonTime) {
        return this._dateFormat.format(pythonTime * 1000);
    }

    formatExponential(value) {
        return (value ? value.toExponential(3) : '').replace(/e\+0$/, '');
    }

    formatTime(unixTime) {
        function format(val) {
            return leftPadZero(Math.floor(val));
        }

        function leftPadZero(num) {
            return num >= 10 ? num : ('0' + num);
        }

        const d = Math.floor(unixTime / (3600*24));
        const h = format(unixTime % (3600*24) / 3600);
        const m = format(unixTime % 3600 / 60);
        const s = format(unixTime % 60);
        let res = d > 0 ? d : '';
        if (res) {
            res += d === 1 ? ' day ': ' days ';
        }
        return res + h + ':' + m + ':' + s;
    }

    isArray(arr) {
        return Array.isArray(arr) || arr instanceof Array;
    }

    isObject(value) {
        return value !== null && typeof value === 'object';
    }

    uniqueId() {
        return `srid${this.uniqueIdCount += 1}`;
    }
}

export const util = singleton.add('util', () => new Util());
