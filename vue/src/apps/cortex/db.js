
import { pubSub } from '@/services/pubsub.js';
import { requestSender } from '@/services/requestsender.js';

export const DB_UPDATED = 'DbUpdated';

class DB {
    async loadMaterials() {
        const r = await requestSender.sendStatefulCompute({
            op_name: 'list_materials',
            op_args: {},
        });
        if (r.op_result) {
            for (const row of r.op_result) {
                // convert python datetime to javascript datetime
                row.created *= 1000;
            }
            return r.op_result;
        }
        return [];
    }

    async deleteMaterial(material_id) {
        const r = await requestSender.sendStatefulCompute({
            op_name: 'delete_material',
            op_args: {material_id},
        });
    }

    updated() {
        pubSub.publish(DB_UPDATED);
    }
}

export const db = new DB();
