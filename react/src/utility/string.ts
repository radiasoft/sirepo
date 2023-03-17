import { ModelsAccessor } from "../data/accessor";
import { Dependency } from "../data/dependency";
import { AbstractModelsWrapper } from "../data/wrapper";
import { FormFieldState } from "../store/formState";

export type ValueSelector<T> = (v: T) => any;

export const ValueSelectors = {
    Models: (v: any) => v,
    Fields: (v: FormFieldState<unknown>) => v.value
}

function getStringReplacementPatterns(str: string): RegExpMatchArray[] {
    return [...str.matchAll(/\$\(([^\%]+?)\)/g)];
}

export class InterpolationBase {
    private matches: RegExpMatchArray[];
    constructor(private str: string) {
        if(!str) {
            throw new Error("interpolation base string undefined");
        }
        this.matches = getStringReplacementPatterns(str);
    }

    withValues(values: {[key: string]: any}): InterpolationResult {
        let mappingsArr = this.matches.map(([originalString, mappedGroup]) => {
            return {
                original: originalString,
                value: values[mappedGroup]
            }
        });

        return new InterpolationResult(
            (serializer) => {
                let interpolatedStr = this.str;

                mappingsArr.forEach(({ original, value }) => {
                    interpolatedStr = interpolatedStr.replace(original, `${serializer(value)}`);
                })

                return interpolatedStr;
            }
        )
    }

    withDependencies<M, F>(modelsWrapper: AbstractModelsWrapper<M, F>, valueSelector: ValueSelector<F>): InterpolationResult {
        let mappingsArr = this.matches.map(([originalString, mappedGroup]) => {
            return {
                original: originalString,
                dependency: new Dependency(mappedGroup)
            }
        });

        let modelAccessor = new ModelsAccessor(modelsWrapper, mappingsArr.map(v => v.dependency));

        let valuesArr = mappingsArr.map(mapping => {
            return {
                ...mapping,
                value: (valueSelector)(modelAccessor.getFieldValue(mapping.dependency))
            }
        })

        return new InterpolationResult(
            (serializer) => {
                let interpolatedStr = this.str;

                valuesArr.forEach(({ original, value }) => {
                    interpolatedStr = interpolatedStr.replace(original, `${serializer(value)}`);
                })

                return interpolatedStr;
            }
        )
    }
}

export class InterpolationResult {
    constructor(private interpString: (serializer: (v: any) => string) => string) {

    }

    raw(): string {
        return this.interpString(v => `${v}`);
    }

    evaluated(): any {
        return eval(this.interpString(v => JSON.stringify(v)));
    }
}

export function interpolate(str: string): InterpolationBase {
    return new InterpolationBase(str);
}

export function titleCaseString(str: string): string {
    return str.split(" ").map(word => {
        return word.substring(0,1).toUpperCase() + (word.length > 1 ? word.substring(1) : "");
    }).join(" ");
}
