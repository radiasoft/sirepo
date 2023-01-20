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

export type SchemaModelsJson = {[modelName: string]: SchemaModelJson};

export type SchemaTypeJson = {
    base: string,
    config: {[key: string]: any}
}

export type SchemaRoutesJson = {
    [key: string]: string
}

export type SchemaJson = {
    constants: {[key: string]: any},
    type: {[typeName: string]: SchemaTypeJson},
    model: SchemaModelsJson,
    view: SchemaLayoutJson[],
    route: SchemaRoutesJson,
    reactRoute: SchemaRoutesJson
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

export type SchemaModels = {[modelName: string]: SchemaModel}

export type SchemaRoutes = {
    [key: string]: string
}

export type Schema = {
    constants: {[key: string]: any},
    models: SchemaModels,
    views: SchemaLayout[],
    route: SchemaRoutes,
    reactRoute: SchemaRoutes
}

export const getAppCombinedSchema = (appName: string): Promise<Schema> => {
    return new Promise<Schema>((resolve, reject) => {
        Promise.all([
            fetch(`/static/react-json/common-schema.json`),
            fetch(`/static/react-json/${appName}-schema.json`)
        ]).then(([commonResp, appResp]) => {
            Promise.all([
                commonResp.json(), 
                appResp.json()
            ]).then(([commonJson, appJson]) => {
                let schemaJson = mergeSchemaJson(commonJson, appJson)
                resolve(compileSchemaFromJson(schemaJson));
            })
        })
    })
}

export function mergeSchemaJson(original: SchemaJson, overrides: SchemaJson): SchemaJson {
    let model = {...original.model};

    for(let [modelName, schemaModel] of Object.entries(overrides.model)) {
        let original = model[modelName] || {};
        model[modelName] = {
            ...original,
            ...schemaModel
        }
    }

    return {
        constants: {
            ...(original.constants || {}),
            ...(overrides.constants || {})
        },
        view: [
            ...(original.view || []),
            ...(overrides.view || [])
        ],
        model,
        type: {
            ...(original.type || {}),
            ...(overrides.type || {})
        },
        route: {
            ...(original.route || {}),
            ...(overrides.route || {})
        },
        reactRoute: {
            ...(original.reactRoute || {}),
            ...(overrides.reactRoute || {})
        }
    }
}

export function compileSchemaFromJson(schemaObj: SchemaJson): Schema {
    let types: {[typeName: string]: InputLayout} = {};

    if(schemaObj.type) {
        types = mapProperties(schemaObj.type, (_, typeSettings) => {
            let {base, config} = typeSettings;
            let initializer = TYPE_BASES[base];
            if(!initializer) {
                throw new Error(`type base with name ${base} was not found`);
            }
            return new initializer(config);
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
            missingTypeNames = [...new Set(missingTypeNames)];
            throw new Error("types could not be found for type names " + JSON.stringify(missingTypeNames));
        }
    }

    return {
        constants: schemaObj.constants,
        views: schemaObj.view,
        models,
        route: schemaObj.route,
        reactRoute: schemaObj.reactRoute
    }
}
