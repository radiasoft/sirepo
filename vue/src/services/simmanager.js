
import { reactive } from 'vue';
import { requestSender } from '@/services/requestsender.js';
import { singleton } from '@/services/singleton.js';

const COMPOUND_PATH_SEPARATOR = ':';

class SimManager{

    state = reactive({
        tree: null,
        folders: null,
    });

    //TODO(pjm): need better API for this
    selectedFolder = {
        path: '',
    };

    addFolder(parentPath, folderName) {
        this.#getOrCreateFolder(
            this.openFolder(parentPath),
            folderName,
        );
        this.state.folders = this.#sortTree(this.root);
    }

    formatFolderPath(folderPath) {
        return folderPath.substring(1).replaceAll('/', COMPOUND_PATH_SEPARATOR);
    }

    getFolders() {
        return this.state.folders;
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
        if (! this.state.tree) {
            await this.loadSims();
        }
    }

    async loadSims() {
        this.state.tree = [
            {
                name: '/',
                children: [],
                isFolder: true,
                path: '',
            },
        ];
        this.root = this.state.tree[0];
        const r = await requestSender.sendRequest('listSimulations', {});
        for (const s of r) {
            this.#addToTree(s.simulation);
        }
        this.state.folders = this.#sortTree(this.root);
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
        this.#removeSim(simulationId, this.root.children);
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
            path: parent.path
                ? `${parent.path}${COMPOUND_PATH_SEPARATOR}${folderName}`
                : folderName,
            isFolder: true,
        };
        n.key = n.path;
        parent.children.push(n);
        return n;
    }

    #removeSim(simulationId, children) {
        for (let i = 0; i < children.length; i++) {
            const c = children[i];
            if (c.isFolder) {
                this.#removeSim(simulationId, c.children);
            }
            else if (c.simulationId === simulationId) {
                children.splice(i, 1);
                return;
            }
        }
    }

    #sortTree(node, folders) {
        if (! folders) {
            folders = []
        }
        if (node.isFolder) {
            folders.push('/' + node.path.replaceAll(COMPOUND_PATH_SEPARATOR, '/'));
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
                this.#sortTree(c, folders);
            }
        }
        return folders;
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

export const simManager = singleton.add('simManager', () => new SimManager());
