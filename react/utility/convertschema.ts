let fs = require("fs");
let { Command } = require("commander");

class Dependency {
    modelName: string;
    fieldName: string;

    constructor(dependencyString: string) {
        let { modelName, fieldName } = this.mapDependencyNameToParts(dependencyString);
        this.modelName = modelName;
        this.fieldName = fieldName;
    }

    mapDependencyNameToParts: (dep: string) => { modelName: string, fieldName: string } = (dep) => {
        let [modelName, fieldName] = dep.split('.').filter((s: string) => s && s.length > 0);
        return {
            modelName,
            fieldName
        }
    }

    getDependencyString: () => string = () => {
        return this.modelName + "." + this.fieldName;
    }
}

function mapProperties<I, O>(obj: {[key: string]: I}, mapFunc: (name: string, value: I) => O): {[key: string]: O} {
    return Object.fromEntries(
        Object.entries(obj).map(([propName, propValue]) => {
            return [propName, mapFunc(propName, propValue)]
        })
    )
}

type OldSchemaEnum = [
    value: string,
    displayName: string
][]

type SchemaLayoutJson = {
    layout: string,
    config: any
} 

type ScheamFieldJson<T> = {
    displayName: string,
    type: string,
    defaultValue?: T,
    description?: string,
    shown?: string,
    min?: number,
    max?: number
}

type SchemaModelJson = {
    [fieldName: string]: ScheamFieldJson<any>
}

type SchemaModelsJson = {[modelName: string]: SchemaModelJson};

type SchemaTypeJson = {
    base: string,
    config: {[key: string]: any}
}

type SchemaRoutesJson = {
    [key: string]: string
}

type SchemaJson = {
    constants: {[key: string]: any},
    type: {[typeName: string]: SchemaTypeJson},
    model: SchemaModelsJson,
    view: SchemaLayoutJson[],
    route: SchemaRoutesJson,
    reactRoute: SchemaRoutesJson
}

type OldSchemaModel = {
    [fieldName: string]: [
        displayName: string,
        typeName: string,
        defaultValue: any,
        description?: string,
        min?: number,
        max?: number
    ]
}

type OldSchemaModels = {[modelName: string]: OldSchemaModel};
type OldSchemaView = {[key: string]: any};
type OldSchemaViews = {[viewName: string]: OldSchemaView};

type OldSchema = {
    enum: {[enumName: string]: OldSchemaEnum},
    model: OldSchemaModels
    view: OldSchemaViews
}



function readSchema(fileName: string): OldSchema {
    let fileString = fs.readFileSync(fileName, { encoding: "utf-8" });
    let fileJson = JSON.parse(fileString) as OldSchema;
    return fileJson;
}

function mergeObjects(child: {[key: string]: any}, parents: {[key: string]: any}[]): {[key: string]: any} {
    let no = {};
    (parents || []).forEach(o => Object.assign(no, o));
    Object.assign(no, child);
    return no;
}

function mergeArrays(child: any[], parents: any[][]): any[] {
    let na = [];
    (parents || []).forEach(a => na.push(...a));
    na.push(...child);
    return na;
}

function performInheritances<T extends object>(objects: {[key: string]: T}, mergeFunc: (original: T, inh: T[]) => T): {[key: string]: T} {
    return Object.fromEntries(
        Object.entries(objects).map(([key, value]) => {
            if(key.startsWith("_")) {
                return undefined;
            }
            let sup: string[] = value["_super"];
            if(sup) {
                value["_super"] = undefined;
                let inh: T[] = sup.filter(v => v !== "model" && v !== "view" && v !== "_").map(n => objects[n]);
                return [
                    key,
                    mergeFunc(value, inh)
                ]
            }
            return [
                key,
                value
            ]
        }).filter(e => e !== undefined)
    )
}

function modelInheritances(models: OldSchemaModels): OldSchemaModels {
    return performInheritances(models, (o, i) => mergeObjects(o, i));
}

function viewInheritances(views: OldSchemaViews): OldSchemaViews {
    return performInheritances(views, (o, i) => {
        let mergeField = (fieldName: string) => {
            o[fieldName] = o[fieldName] || [];
            o[fieldName] = mergeArrays(o[fieldName], i.map(v => v[fieldName] || {}))
            if(Object.keys(o[fieldName]).length == 0) {
                o[fieldName] = undefined;
            }
        }
        mergeField("basic");
        mergeField("advanced");
        return o;
    })
}

function convertSchema(schema: OldSchema) {
    let oModels = modelInheritances(schema.model);
    //saveSchema("omodels.json", oModels);
    let models = mapProperties(oModels, (modelName, model) => convertModel(model));
    let types = mapProperties(schema.enum, (enumName, e) => convertEnum(e));

    let views = [];
    let uViews = [];

    let oViews = viewInheritances(schema.view);
    //saveSchema("oviews.json", oViews)
    mapProperties(oViews, (viewName, view) => {
        let [converted, cv] = convertView(viewName, view, models);
        if(converted) {
            views.push(cv);
        } else {
            uViews.push(cv);
        }
    })

    return {
        model: models,
        type: types,
        view: views,
        unhandled: uViews
    }
}

function convertModel(model: OldSchemaModel): SchemaModelJson {
    let newModel = {};
    for(let [fieldName, field] of Object.entries(model)) {
        if(field === undefined) {
            continue;
        }
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
    return newModel;
}

function convertEnum(old: OldSchemaEnum): SchemaTypeJson {
    return {
        base: "Enum",
        config: {
            allowedValues: old
        }
    }
}

function convertView(viewName: string, view: {[key: string]: any}, models: SchemaModelsJson): [converted: boolean, view: {[key: string]: any}] {
    let keys = Object.keys(view);

    let withMeta = (viewName, view) => {
        view["_NAME"] = viewName;
        return view;
    }

    if(keys.includes("basic") || keys.includes("advanced")) {
        // is panel
        return [true, withMeta(viewName, convertPanel(viewName, view, models))]
    } else {
        return [false, withMeta(viewName, view)];
    }
}

function fullFieldName(fieldName: string, modelName: string) {
    let r = /\./
    if(r.test(fieldName)) {
        return fieldName;
    }
    return `${modelName}.${fieldName}`;
}


function convertPanel(
    viewName: string, 
    view: {[key: string]: any}, 
    models: SchemaModelsJson
): {[key: string]: any} {
    let modelName = viewName;
    if(view.model) {
        modelName = view.model;
    }

    let convertPanelContents = (children: any[]): SchemaLayoutJson[] => {
        let tabs: [name: string, views: any[]][] = [];
        let convertArrayChild = (ac: any) => {
            /**
             * ac could be either 
             * [string, ...] as a tab or 
             * [[string, ...], ...] as a table
             */
            if(Array.isArray(ac[0])) {
                // is table
                return fieldTableLayout(ac, modelName, models);
            } else {
                tabs.push([ac[0], convertPanelContents(ac[1])])
                return undefined;
            }
        }

        let newChildren = [];
        let fieldNames = [];
        let popFields = () => {
            if(fieldNames.length > 0) {
                newChildren.push(fieldListLayout(fieldNames));
                fieldNames = [];
            }
        }
        for(let child of children) {
            if(typeof child === "string") {
                fieldNames.push(fullFieldName(child, modelName));
            } else {
                popFields();
                if(Array.isArray(child)) {
                    let c = convertArrayChild(child);
                    if(c !== undefined) {
                        newChildren.push(c);
                    }
                } else {
                    throw new Error(`unknown child=${JSON.stringify(child)}`);
                }
            }
        }
        popFields();

        if(tabs.length > 0) {
            newChildren.push(tabsLayout(tabs))
        }

        return newChildren;
    }

    let config: {[key: string]: any} = {};

    if(view.basic) {
        config['basic'] = convertPanelContents(view.basic);
    }

    if(view.advanced) {
        config['advanced'] = convertPanelContents(view.advanced);
    }

    config['title'] = view.title;

    return {
        layout: "panel",
        config
    }
}

function layout(
    type: string,
    config: {[key: string]: any}
) {
    return {
        layout: type,
        config
    }
}

function tabsLayout(
    tabs: [name: string, views: any[]][],

): SchemaLayoutJson {
    let tab = (name: string, views: any[]) => {
        return {
            name,
            items: views
        }
    }

    return layout(
        "tabs",
        {
            tabs: tabs.map(([name, views]) => tab(name, views))   
        }
    )
}

function fieldListLayout(fieldNames: string[]) {
    return layout("fieldList", {
        fields: fieldNames
    })
}

function fieldTableLayout(
    columns: [name: string, fieldNames: string[]][],
    modelName: string,
    models: SchemaModelsJson
) {
    let columnNames = columns.map(([name,]) => name);
    let rows: {
        label: string,
        description: string,
        fields: string[]
    }[] = [];
    let lens = [...new Set(columns.map(([, fields]) => fields.length))];
    if(lens.length > 1) {
        //throw new Error(`unequal table columns=${JSON.stringify(columns)} field lengths=${lens}`)
        // return these broken into columns manually instead of as a table
        return layout("hStack", {
            items: columns.map(([name, fieldNames]) => {
                return layout("vStack", {
                    items: [
                        layout("text", {
                            type: "header",
                            align: "left",
                            text: name
                        }),
                        fieldListLayout(fieldNames.map(fn => fullFieldName(fn, modelName)))
                    ]
                })
            })
        })
    }
    if(lens.length > 0) {
        let len = lens[0];
        for(let i = 0; i < len; i++) {
            let fields = columns.map(([, fields]) => fullFieldName(fields[i], modelName));
            let dep = new Dependency(fields[0]);
            let firstModelField = models[dep.modelName][dep.fieldName]
            rows.push({
                label: firstModelField.displayName,
                description: firstModelField.description,
                fields
            })
        }
    }
    return layout(
        "fieldTable",
        {
            columns: columnNames,
            rows
        }
    )
}

function saveSchema(fileName: string, schema): void {
    fs.writeFileSync(fileName, JSON.stringify(schema));
}

let program = new Command();
program
.arguments("<fileName>")
.option("-o, --output <fileName>", "output filename")
.action((inFile: string, options: {output?: string}) => {
    let defaultOutfile = () => {
        let sep =inFile.indexOf(".");
        if(sep < 0) {
            return inFile + "-conv";
        }

        return inFile.substring(0, sep) + "-conv" + inFile.substring(sep);
    }
    let outFile = options.output || defaultOutfile();
    saveSchema(outFile, convertSchema(readSchema(inFile)));
})
program.parse();
