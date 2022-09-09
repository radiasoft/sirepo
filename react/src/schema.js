import { globalTypes, enumTypeOf } from "./types";
import { mapProperties } from "./helper";

export function compileSchemaFromJson(schemaObj) {
    let enumTypes = {};

    if(schemaObj.enum) {
        enumTypes = mapProperties(schemaObj.enum, (name, allowedValues) => {
            allowedValues = allowedValues.map(allowedValue => {
                let [value, displayName] = allowedValue;
                return {
                    value, 
                    displayName
                }
            })
            return enumTypeOf(allowedValues);
        })
    }

    let types = {
        ...globalTypes,
        ...enumTypes
    }

    let models = {};

    if(schemaObj.model) {
        models = mapProperties(schemaObj.model, (modelName, modelObj) => {
            return mapProperties(modelObj, (fieldName, field) => {
                let [displayName, typeName, defaultValue] = field;
                let type = types[typeName];
                return {
                    displayName,
                    type,
                    defaultValue
                }
            })
        })
    }

    return {
        views: schemaObj.view,
        models
    }
}
