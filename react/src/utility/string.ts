import { getValueSelector, StoreType } from "../data/data";
import { Dependency } from "../data/dependency";
import { HandleFactory } from "../data/handle";

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

    withDependencies<M, F>(handleFactory: HandleFactory, type: StoreType<M, F>): InterpolationResult {
        let valueSelector = getValueSelector(type) as (v: F) => any;

        let mappingsArr = this.matches.map(([originalString, mappedGroup]) => {
            return {
                original: originalString,
                dependency: new Dependency(mappedGroup)
            }
        });

        let valuesArr = mappingsArr.map(mapping => {
            return {
                ...mapping,
                value: (valueSelector)(handleFactory.createHandle<M, F>(mapping.dependency, type).hook().value)
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

// https://stackoverflow.com/a/15710692
export function hashCode(s: string): number {
    return s.split("").reduce(function(a, b) {
      a = ((a << 5) - a) + b.charCodeAt(0);
      return a & a;
    }, 0);
  }
