class SRApp {
    constructor(name, schema) {
        this.name = name;

        // keep the schema or just build from it?
        this.enums = {};
        for (let e in schema.enum) {
            this.enums[e] = new SREnum(e);
        }
    }
}

class SREnum {
    constructor(enumName) {
        let em = SIREPO.APP_SCHEMA.enumModels[enumName];
        if (! em) {
            throw new Error(`${enumName}: no such enum in schema`);
        }
        this.name = enumName;
        this.entries = em.entries;
        this.layout = em.layout || 'auto';
    }
}

SIREPO.APP = {
    SRApp: SRApp,
    SREnum: SREnum,
};
