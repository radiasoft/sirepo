
import { singleton } from '@/services/singleton.js';

//TODO(pjm): logging service
const srlog = console.log;

class BrowserStorage {
    getBoolean(name, defaultValue=false) {
        const s = this.getString(name, null);
        if (s === null) {
             return defaultValue;
        }
        if (s === 'true') {
            return true;
        }
        if (s === 'false') {
            return false;
        }
        srlog(`browserStorage.getBoolean(${name}) invalid value=${s}`);
        this.removeItem(name);
        return defaultValue;
    }

    getString(name, defaultValue=null) {
        const rv = localStorage.getItem(name);
        return rv == null ? defaultValue : rv;
    }

    removeItem(name) {
        localStorage.removeItem(name);
    }

    setBoolean(name, value) {
        this.setString(name, value ? 'true' : 'false');
    }

    setString(name, value) {
        localStorage.setItem(name, value);
    }
}

export const browserStorage = singleton.add('browserStorage', new BrowserStorage());
