let fs = require("fs")

export function convertModels(fileName) {
    let fileString = fs.readFileSync(fileName, { encoding: "utf-8" });
    let fileJson = JSON.parse(fileString);

    let models = fileJson.model;

    let newModels = {};

    for(let [modelName, model] of Object.entries(models)) {
        let newModel = {};
        for(let [fieldName, field] of Object.entries(model)) {
            let [name, typeString, defaultValue, description, min, max] = field;
            
        }
        newModels[modelName] = newModel;
    }
}

