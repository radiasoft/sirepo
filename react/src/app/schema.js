import { stringType, optionalStringType, floatType, enumTypeOf } from '../types'

const genderType = enumTypeOf([
    {
        value: 'male',
        displayName: 'Male'
    },
    {
        value: 'female',
        displayName: 'Female'
    }
])

const dogDispositionType = enumTypeOf([
    {
        value: 'aggressive',
        displayName: 'Aggressive'
    },
    {
        value: 'friendly',
        displayName: 'Friendly'
    },
    {
        value: 'submissive',
        displayName: 'Submissive'
    }
])

let dogModel = {
    breed: {
        name: 'Breed',
        type: stringType, // TODO these are the first sources of non-serializable information in the schema
    },
    gender: {
        name: 'Gender',
        type: genderType,
        defaultValue: 'male',
    },
    height: {
        name: 'Height [cm]',
        type: floatType,
        defaultValue: 50.0,
        description: 'Distance from front paws to withers'
    },
    weight: {
        name: 'Weight [lbs]',
        type: floatType,
        defaultValue: 60.5
    },
    disposition: {
        name: 'Disposition',
        type: dogDispositionType,
        defaultValue: 'friendly'
    },
    favoriteTreat: {
        name: 'Favorite Treat',
        type: optionalStringType,
        defaultValue: "" // TODO null/undef? / not needed either way?
    }
}

let models = {
    dog: dogModel
}

let dogView = {
    title: 'Dog',
    type: 'editor',
    config: {
        basicFields: [
            "dog.breed",
            "dog.weight",
            "dog.height",
            "dog.disposition",
            "dog.favoriteTreat"
        ],
        advancedFields: [
            "dog.breed",
            "dog.gender",
            "dog.weight",
            "dog.height"
        ]
    }
}

let dogView2 = {
    ...dogView,
    title: 'Dog2'
}

let heightWeightReportView = {
    title: 'Physical Characteristics',
    type: 'graph2d'
}

let views = {
    dog: dogView,
    dog2: dogView2,
    heightWeightReport: heightWeightReportView
}

// TODO this is strange because it must reference the type of the
// model as though it is instantiated even though this happens
// elsewhere. types would be useful here

// TODO a better definition for 'active' is needed, what does this do?
let isActiveFavoriteTreat = (modelChanges) => {
    let dogModelChanges = modelChanges['dog'];
    if(dogModelChanges) {
        if(dogModelChanges['disposition']) { // TODO by reference instead of by name ??
            let { lastValue, currentValue } = dogModelChanges['disposition'];
            let favoriteTreatChanges = dogModelChanges['favoriteTreat'] || {};
            dogModelChanges['favoriteTreat'] = favoriteTreatChanges;
            favoriteTreatChanges.currentValue.active = (currentValue == 'friendly'); // TODO again, reference or value?
        }
    }   
}

let modelListeners = [
    isActiveFavoriteTreat
]

export default {
    modelListeners,
    views,
    models
}
