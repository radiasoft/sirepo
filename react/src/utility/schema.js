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

    if(schemaObj.model) {
        let missingTypeNames = [];

        models = mapProperties(schemaObj.model, (modelName, modelObj) => {
            return mapProperties(modelObj, (fieldName, field) => {
                let [displayName, typeName, defaultValue] = field;
                let type = types[typeName];
                if(!type) {
                    missingTypeNames.push(typeName);
                }
                return {
                    displayName,
                    type,
                    defaultValue
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
