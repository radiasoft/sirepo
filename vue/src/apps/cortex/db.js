
import { pubSub } from '@/services/pubsub.js';
import { requestSender } from '@/services/requestsender.js';

export const DB_UPDATED = 'DbUpdated';

class DB {
    async loadMaterials() {
        return (await requestSender.sendStatefulCompute({
            method: 'list_materials',
        })).result;
    }

    async deleteMaterial(material_id) {
        await requestSender.sendStatefulCompute({
            method: 'delete_material',
            args: {
                material_id,
            },
        });
    }

    async materialDetail(material_id) {
        return (await requestSender.sendStatefulCompute({
            method: 'material_detail',
            args: {
                material_id,
            },
        })).result;
    }

    updated() {
        pubSub.publish(DB_UPDATED);
    }
}

export const db = new DB();
