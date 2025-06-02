

import { requestSender } from '@/services/requestsender.js';

const COMPOUND_PATH_SEPARATOR = ':';

class SimManager{

    addFolder(parentNode, folderName) {
    }

    openFolder(folderName) {
        let c = this.root;
        for (const f of this.#folderPath(folderName)) {
            let nc = null;
            for (const n of c.children) {
                if (n.isFolder && n.name === f) {
                    n.isOpen = true;
                    nc = n;
                    break;
                }
            }
            if (! nc) {
                return null;
            }
            c = nc;
        }
        return c;
    }

    getFolderNameFromRoute(route) {
        let p = route.params.folderName;
        if (p) {
            p = decodeURIComponent(p).replaceAll(COMPOUND_PATH_SEPARATOR, '/');
            return p;
        }
        return this.root.name;
    }

    getRelatedSims(sim) {
    }

    loadSims(callback) {
        this.tree = [
            {
                name: '/',
                children: [],
                path: '',
            },
        ];
        this.root = this.tree[0];
        requestSender.sendRequest(
            'listSimulations',
            (response) => {
                for (const s of response) {
                    this.#addToTree(s.simulation);
                }
                this.#sortTree(this.root);
                callback();
            },
            {},
        );
    }

    #addToTree(sim) {
        let c = this.root;
        for (const f of this.#folderPath(sim.folder)) {
            c = this.#getOrCreateFolder(c, f);
        }
        sim.key = sim.simulationId;
        c.children.push(sim);
    }

    #folderPath(folderName) {
        const p = [];
        for (const f of folderName.split('/')) {
            if (f !== '') {
                p.push(f);
            }
        }
        return p;
    }

    #getOrCreateFolder(parent, folderName) {
        for (const n of parent.children) {
            if (n.isFolder && n.name === folderName) {
                return n;
            }
        }
        const n = {
            name: folderName,
            children: [],
            key: folderName,
            path: parent.path
                ? `${parent.path}${COMPOUND_PATH_SEPARATOR}${folderName}`
                : folderName,
            isFolder: true,
        };
        parent.children.push(n);
        return n;
    }

    #sortTree(node) {
        node.children.sort((a, b) => {
            if (a.isFolder) {
                if (b.isFolder) {
                    return a.name.localeCompare(b.name);
                }
                return -1;
            }
            if (b.isFolder) {
                return 1;
            }
            return a.name.localeCompare(b.name);
        });
        for (const c of node.children) {
            if (c.isFolder) {
                this.#sortTree(c);
            }
        }
    }
}

export const simManager = new SimManager();
