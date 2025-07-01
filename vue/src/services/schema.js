
class Schema {
    init(simulationType, schema) {
        if (this.simulationType) {
            throw new Error('Schema already initialized');
        }
        this.simulationType = simulationType;
        Object.assign(this, schema);
    }
}

export const schema = new Schema();
