import { InputLayout } from "../layout/input/input";
import { TYPE_BASES } from "../layout/input/inputs";
import { mapProperties } from "./object";

export type SchemaLayoutJson = {
    layout: string,
    config: any
} 

export type ScheamFieldJson<T> = {
    displayName: string,
    type: string,
    defaultValue?: T,
    description?: string,
    shown?: string,
    min?: number,
    max?: number
}

export type SchemaModelJson = {
    [fieldName: string]: ScheamFieldJson<any>
}

export type SchemaTypeJson = {
    base: string,
    config: {[key: string]: any}
}

export type SchemaJson = {
    type: {[typeName: string]: SchemaTypeJson},
    model: {[modelName: string]: SchemaModelJson},
    view: SchemaLayoutJson[]
}

export type SchemaLayout = SchemaLayoutJson;

export type SchemaField<T> = {
    displayName: string,
    type: InputLayout,
    defaultValue?: T,
    description?: string,
    shown?: string,
    min?: number,
    max?: number
}

export type SchemaModel = {
    [fieldName: string]: SchemaField<any>
}

export type Schema = {
    models: {[modelName: string]: SchemaModel},
    views: SchemaLayout[]
}

export function mergeSchemaJson(original, overrides) {
    return {
        view: [
            ...(original.view || []),
            ...(overrides.view || [])
        ],
        model: {
            ...(original.model || {}),
            ...(overrides.model || {})
        },
        type: {
            ...(original.type || {}),
            ...(overrides.type || {})
        }
    }
}

export function compileSchemaFromJson(schemaObj: SchemaJson) {
    let types: {[typeName: string]: InputLayout} = {};

    if(schemaObj.type) {
        types = mapProperties(schemaObj.type, (_, {base, config}) => {
            return new (TYPE_BASES[base])(config);
        })
    }

    let models = {};

    if(schemaObj.model) {
        let missingTypeNames = [];

        models = mapProperties(schemaObj.model, (_, modelObj) => {
            return mapProperties(modelObj, (_, field) => {
                let { displayName, type: typeName, defaultValue, description, shown, min, max } = field;
                let type = types[typeName];
                if(!type) {
                    missingTypeNames.push(typeName);
                }
                return {
                    displayName,
                    type,
                    shown,
                    defaultValue,
                    description,
                    min,
                    max
                }
            })
        })

        if(missingTypeNames.length > 0) {
            throw new Error("types could not be found for type names " + JSON.stringify(missingTypeNames));
        }
    }

    return {
        views: schemaObj.view,
        models
    }
}
