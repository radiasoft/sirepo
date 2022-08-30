import { globalTypes, enumTypeOf } from "./types";
import { mapProperties } from "./helper";

export function compileSchemaFromJson(schemaObj) {
    let enumTypes = {};

    if(schemaObj.enum) {
        enumTypes = mapProperties(schemaObj.enum, (name, value) => enumTypeOf(value))
    }

    let types = {
        ...globalTypes,
        ...enumTypes
    }

    let models = {};

    if(schemaObj.model) {
        models = mapProperties(schemaObj.model, (modelName, modelObj) => {
            return mapProperties(modelObj, (fieldName, field) => {
                let [name, typeName, defaultValue] = field;
                let type = types[typeName];
                return {
                    name,
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
