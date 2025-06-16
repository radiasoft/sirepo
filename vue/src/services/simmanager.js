
import { requestSender } from '@/services/requestsender.js';

const COMPOUND_PATH_SEPARATOR = ':';

class SimManager{

    //TODO(pjm): need better API for this
    selectedFolder = {
        path: '',
    };

    addFolder(parentNode, folderPath) {
    }

    formatFolderPath(folderPath) {
        return folderPath.substring(1).replaceAll('/', COMPOUND_PATH_SEPARATOR);
    }

    getFolders() {
        return this.folders;
    }

    getFolderPathFromRoute(route) {
        let p = route.params.folderPath;
        if (p) {
            p = decodeURIComponent(p).replaceAll(COMPOUND_PATH_SEPARATOR, '/');
            return p;
        }
        return this.root.name;
    }

    getFolderPath(folder) {
        return '/' + folder.path.replaceAll(COMPOUND_PATH_SEPARATOR, '/');
    }

    getRelatedSims(sim) {
    }

    async getSims() {
        if (! this.tree) {
            await this.loadSims();
        }
    }

    async loadSims() {
        this.tree = [
            {
                name: '/',
                children: [],
                isFolder: true,
                path: '',
            },
        ];
        this.root = this.tree[0];
        this.folders = [];
        const r = await requestSender.sendRequest('listSimulations', {});
        for (const s of r) {
            this.#addToTree(s.simulation);
        }
        this.#sortTree(this.root);
    }

    openFolder(folderPath) {
        let c = this.root;
        for (const f of this.#splitFolderPath(folderPath)) {
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

    removeSim(simulationId) {
    }

    #addToTree(sim) {
        let c = this.root;
        for (const f of this.#splitFolderPath(sim.folder)) {
            c = this.#getOrCreateFolder(c, f);
        }
        sim.key = sim.simulationId;
        c.children.push(sim);
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
        if (node.isFolder) {
            this.folders.push('/' + node.path.replace(COMPOUND_PATH_SEPARATOR, '/'));
        }
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

    #splitFolderPath(folderPath) {
        const p = [];
        for (const f of folderPath.split('/')) {
            if (f !== '') {
                p.push(f);
            }
        }
        return p;
    }
}

export const simManager = new SimManager();
