import { globalTypes, partialTypes } from "../types";
import { mapProperties } from "./object";

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

export function compileSchemaFromJson(schemaObj) {
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
