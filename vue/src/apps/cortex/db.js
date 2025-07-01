
import { simManager } from '@/services/simmanager.js';

class DB {
    async loadMaterials() {
        //TODO(pjm): replace with real server db api call
        await simManager.loadSims();
        return simManager
            .openFolder('').children
            .filter(
                (n) => ! n.isFolder// && n.isConfirmed === '1',
            ).map(
                (m) => {
                    m.material_id = m.simulationId;
                    return m;
                },
            );
    }
}

export const db = new DB();
