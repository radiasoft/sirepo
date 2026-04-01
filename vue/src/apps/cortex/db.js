
import { pubSub } from '@/services/pubsub.js';
import { requestSender } from '@/services/requestsender.js';

export const DB_UPDATED = 'DbUpdated';

class DB {
    async canSetMaterialPublic(material_id) {
        return Object.keys((await this.loadSummary(material_id, false)).sim).length === 2;
    }

    async deleteMaterial(material_id) {
        return await this.#send('delete_material', {material_id});
    }

    async featuredMaterials() {
        return (await this.#send('featured_materials')).op_result;
    }

    async insertMaterial(file) {
        return await this.#send('insert_material', {}, file);
    }

    async listMaterials() {
        const r = await this.#send('list_materials');
        if (r.op_result) {
            return r.op_result.rows;
        }
        //TODO(robnagler) should no op_result be logged?
        return [];
    }

    async loadSummary(material_id, is_public) {
        return (await this.#send('load_summary', {material_id, is_public})).op_result;
    }

    async materialDetail(material_id, is_public) {
        const r = await this.#send('material_detail', {material_id, is_public});
        if (r.error) {
            return r;
        }
        return r.op_result;
    }

    async publicMaterials() {
        return (await this.#send('public_materials')).op_result;
    }

    async setMaterialPublic(material_id, is_public) {
        return await this.#send('set_material_public', {material_id, is_public});
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
