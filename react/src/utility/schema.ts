import { globalTypes, partialTypes, rsAbstrType } from "../types";
import { mapProperties } from "./object";

export type SchemaViewJson = {
    layout: string
} & {[propName: string]: any}

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
    settings: {[key: string]: any}
}

export type SchemaJson = {
    type: {[typeName: string]: SchemaTypeJson},
    model: {[modelName: string]: SchemaModelJson},
    view: [SchemaViewJson]
}

export type SchemaView = SchemaViewJson;

export type SchemaField<T> = {
    displayName: string,
    type: rsAbstrType,
    defaultValue?: T,
    shown?: string,
    min?: number,
    max?: number
}

export type SchemaModel = {
    [fieldName: string]: SchemaField<any>
}

export type Schema = {
    models: {[modelName: string]: SchemaModel},
    views: [SchemaView]
}

export function compileSchemaFromJson(schemaObj: SchemaJson) {
    let enumTypes = {};
    let additionalTypes = {};

    if(schemaObj.type) {
        additionalTypes = mapProperties(schemaObj.type, (name, {base, settings}) => {
            let partialTypeFactory = partialTypes[base];
            let partialType = partialTypeFactory(settings);
            return partialType;
        })
    }

    let types = {
        ...globalTypes,
        ...enumTypes,
        ...additionalTypes
    }

    let models = {};

    // TODO merge this from file
    let simulationModel = {
        documentationUrl: {
            displayName: "Documentation URL", 
            type: "OptionalString", 
            defaultValue: ""
        },
        folder: {
            displayName: "Folder", 
            type: "String", 
            defaultValue: ""
        },
        isExample: {
            displayName: "Is Example", 
            type: "Boolean", 
            defaultValue: true
        },
        lastModified: {
            displayName: "Time Last Modified", 
            type: "Integer", 
            defaultValue: 0
        }, // TODO: include this?
        name: {
            displayName: "Name", 
            type: "String", 
            defaultValue: ""
        },
        notes: {
            displayName: "Notes", 
            type: "OptionalString", 
            defaultValue: ""
        },
        simulationId: {
            displayName: "Simulation ID", 
            type: "String", 
            defaultValue: ""
        }, // TODO: include this?
        simulationSerial: {
            displayName: "Simulation Serial", 
            type: "String", 
            defaultValue: ""
        } // TODO: include this?
    }

    if(schemaObj.model) {
        let missingTypeNames = [];

        models = mapProperties({
            ...schemaObj.model,
            simulation: simulationModel
        }, (modelName, modelObj) => {
            return mapProperties(modelObj, (fieldName, field) => {
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
