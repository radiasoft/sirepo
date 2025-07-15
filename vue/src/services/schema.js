
import { singleton } from '@/services/singleton.js';

class Schema {
    init(simulationType, schema) {
        if (this.simulationType) {
            throw new Error('Schema already initialized');
        }
        this.simulationType = simulationType;
        Object.assign(this, schema);
    }
}

export const schema = singleton.add('schema', () => new Schema());
