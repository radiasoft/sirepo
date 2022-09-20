import { globalTypes, partialTypes } from "../types";
import { mapProperties } from "./object";

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
        documentationUrl: ["Documentation URL", "OptionalString", ""],
        folder: ["Folder", "String", ""],
        isExample: ["Is Example", "Boolean", true],
        lastModified: ["Time Last Modified", "Integer", 0], // TODO: include this?
        name: ["Name", "String", ""],
        notes: ["Notes", "OptionalString", ""],
        simulationId: ["Simulation ID", "String", ""], // TODO: include this?
        simulationSerial: ["Simulation Serial", "String", ""] // TODO: include this?
    }

    if(schemaObj.model) {
        let missingTypeNames = [];

        models = mapProperties({
            ...schemaObj.model,
            simulation: simulationModel
        }, (modelName, modelObj) => {
            return mapProperties(modelObj, (fieldName, field) => {
                let [displayName, typeName, defaultValue, description] = field;
                let type = types[typeName];
                if(!type) {
                    missingTypeNames.push(typeName);
                }
                return {
                    displayName,
                    type,
                    defaultValue,
                    description
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
