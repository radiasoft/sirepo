/**
 * Helper function to create an object of the same shape as the input by mapping property values to a new value
 * @param {{[name: string]: T}} obj
 * @param {(name: string, value: T) => *} mapFunc
 * @returns {T} An object with the same fields having mapFunc applied
 */
 export function mapProperties(obj, mapFunc) {
    return Object.fromEntries(
        Object.entries(obj).map(([propName, propValue]) => {
            return [propName, mapFunc(propName, propValue)]
        })
    )
}
