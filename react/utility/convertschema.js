let fs = require("fs")

function convertModels(fileName) {
    let fileString = fs.readFileSync(fileName, { encoding: "utf-8" });
    let fileJson = JSON.parse(fileString);

    let models = fileJson.model;

    let newModels = {};

    for(let [modelName, model] of Object.entries(models)) {
        let newModel = {};
        for(let [fieldName, field] of Object.entries(model)) {
            let [name, typeString, defaultValue, description, min, max] = field;
            newModel[fieldName] = {
                displayName: name,
                type: typeString,
                defaultValue,
                description,
                min,
                max
            }
        }
        newModels[modelName] = newModel;
    }

    fs.writeFileSync('new-' + fileName, JSON.stringify({ model: newModels }));
}

function convertEnums(fileName) {
    let fileString = fs.readFileSync(fileName, { encoding: "utf-8" });
    let fileJson = JSON.parse(fileString);

    let e = fileJson.enum;
    let types = {};

    for(let [enumName, allowedValues] of Object.entries(e)) {
        types[enumName] = {
            base: "Enum",
            settings: {
                allowedValues
            }
        }
    }

    fs.writeFileSync('new-' + fileName, JSON.stringify({ type: types }));
}

function listTypes(fileName) {
    let fileString = fs.readFileSync(fileName, { encoding: "utf-8" });
    let fileJson = JSON.parse(fileString);
    let models = fileJson.model;

    let fieldTypes = new Set();
    for(let [modelName, model] of Object.entries(models)) {
        for(let [fieldName, field] of Object.entries(model)) {
            let [name, typeString, defaultValue, description, min, max] = field;
            fieldTypes.add(typeString);
        }
    }

    fieldTypes.forEach(s => console.log(s));
}

convertEnums("genesis.json");
//convertModels("myapp.json");
