
import { appState } from '@/services/appstate.js';
import { singleton } from '@/services/singleton.js';

const INDEX_DB_NAME = 'srCache2';
const STORE = 'db';
const FRAME = 'frame';
// 30 days until expired
const EXPIRY_TIME = 30 * 24 * 60 * 60 * 1000;

class ObjectStore {

    // Browser side caching implemented using indexedDB
    // - Caches sim frame responses
    // - Allows cache to be cleared by simId or (simId, modelName)
    // - Keeps updateTime on item access and deletes expired records at startup

    #db = null;

    constructor() {
        this.#initializeDatabase();
    }

    #deleteKeys(keys) {
        if (! keys.length) {
            return;
        }
        this.#withObjectStore('readwrite', (o) => {
            for (const k of keys) {
                o.delete(k);
            }
        });
    }

    #initializeDatabase = () => {
        if (! window.indexedDB) {
            return;
        }
        const r = window.indexedDB.open(INDEX_DB_NAME, 1);
        r.onsuccess = (event) => {
            this.#db = event.target.result;
            this.#removeOldRecords();
        };
        r.onupgradeneeded = (event) => {
            const d = event.target.result;
            if (d.objectStoreNames.contains(STORE)) {
                d.deleteObjectStore(STORE);
            }
            const o = d.createObjectStore(STORE);
            o.createIndex('simId', '_srcache_simId', { unique: false });
            o.createIndex('updateTime', '_srcache_updateTime', { unique: false });
        };
    }

    #invokeCallback(callback, value) {
        callback(value);
    }

    #objectKey(prefix, value) {
        return prefix + ':' + value;
    }

    #getObjectStore(mode) {
        // Returns null if the objectStore is not accessible
        try {
            if (this.#db) {
                return this.#db.transaction(STORE, mode).objectStore(STORE);
            }
        }
        catch (e) {
            // at any point the browser can remove the object store
            // and the transaction() would raise a NotFoundError
        }
        return null;
    }

    #removeOldRecords() {
        this.#withObjectStore('readonly', (o) => {
            const expired = [];
            const d = new Date().getTime();
            o.index('updateTime').openKeyCursor().onsuccess = (event) => {
                const c = event.target.result;
                if (c) {
                    if ((d - c.key) > EXPIRY_TIME) {
                        expired.push(c.primaryKey);
                    }
                    c.continue();
                }
                else {
                    this.#deleteKeys(expired);
                }
            };
        });
    }

    #withObjectStore(mode, callback) {
        const o = this.#getObjectStore(mode);
        if (o) {
            callback(o);
        }
    }

    clearFrames(simId, modelName) {
        // deletes frames by simId, or (simId, modelName)
        this.#withObjectStore('readonly', (o) => {
            const keys = [];
            o.index('simId').openCursor(window.IDBKeyRange.only(simId)).onsuccess = (event) => {
                const c = event.target.result;
                if (c) {
                    if ((! modelName) || modelName === c.value._srcache_modelName) {
                        keys.push(c.primaryKey);
                        c.continue();
                    }
                }
                else {
                    this.#deleteKeys(keys);
                }
            };
        });
    }

    getFrame(frameId, modelName, callback) {
        const o = this.#getObjectStore('readonly');
        if (! o) {
            this.#invokeCallback(callback, null);
            return;
        }
        const c = o.get(this.#objectKey(FRAME, frameId));
        c.onsuccess = (event) => {
            const d = event.target.result;
            this.#invokeCallback(callback, d);
            if (d) {
                // sets updateTime
                this.saveFrame(frameId, modelName, d);
            }
        };
        c.onerror = () => {
            this.#invokeCallback(callback, null);
        };
    }

    saveFrame(frameId, modelName, data) {
        if (data.error) {
            return;
        }
        this.#withObjectStore('readwrite', (o) => {
            data._srcache_updateTime = new Date().getTime();
            data._srcache_modelName = modelName;
            data._srcache_simId = appState.models.simulation.simulationId;
            o.put(data, this.#objectKey(FRAME, frameId));
        });
    }
}

export const objectStore = singleton.add('objectStore', () => new ObjectStore());
