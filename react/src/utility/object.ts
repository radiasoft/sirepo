export function mapProperties<I, O>(obj: {[key: string]: I}, mapFunc: (name: string, value: I) => O): {[key: string]: O} {
    return Object.fromEntries(
        Object.entries(obj).map(([propName, propValue]) => {
            return [propName, mapFunc(propName, propValue)]
        })
    )
}
