
import { pubSub } from '@/services/pubsub.js';
import { requestSender } from '@/services/requestsender.js';

export const DB_UPDATED = 'DbUpdated';

class DB {
    async loadMaterials() {
        const r = await requestSender.sendStatefulCompute({
            method: 'cortex_db',
            args: {
                api_name: 'list_materials',
                api_args: {},
            },
        });
        if (r.api_result) {
            for (const row of r.api_result) {
                // convert python datetime to javascript datetime
                row.created *= 1000;
            }
            return r.api_result;
        }
        return [];
    }

    async deleteMaterial(material_id) {
        await requestSender.sendStatefulCompute({
            method: 'cortex_db',
            args: {
                api_name: 'delete_material',
                api_args: {
                    material_id,
                },
            },
        });
    }

    async materialDetail(material_id) {
        return (await requestSender.sendStatefulCompute({
            method: 'cortex_db',
            args: {
                api_name: 'material_detail',
                api_args: {
                    material_id,
                },
            },
        })).api_result;
    }

    updated() {
        pubSub.publish(DB_UPDATED);
    }
}

export const db = new DB();
