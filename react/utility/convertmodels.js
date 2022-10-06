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
                name,
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

//convertModels("myapp.json");
