
import { pubSub } from '@/services/pubsub.js';
import { requestSender } from '@/services/requestsender.js';

export const DB_UPDATED = 'DbUpdated';

class DB {
    async deleteMaterial(material_id) {
        return await this.#send('delete_material', {material_id});
    }

    async insertMaterial(file) {
        return await this.#send('insert_material', {}, file);
    }

    async listMaterials() {
        const r = await this.#send('list_materials');
        if (r.op_result) {
            for (const row of r.op_result.rows) {
                // convert python datetime to javascript datetime
                row.created *= 1000;
            }
            return r.op_result.rows;
        }
        //TODO(robnagler) should no op_result be logged?
        return [];
    }

    updated() {
        pubSub.publish(DB_UPDATED);
    }

    async #send(op_name, op_args = {}, file = undefined) {
        const d = {op_name, op_args};
        if (file) {
            d.reqDataFile = file;
        }
        return await requestSender.sendRequest("cortexDb", d);

    }
}

export const db = new DB();
