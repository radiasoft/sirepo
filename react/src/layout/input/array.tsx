import { InputConfigBase, InputLayout } from "./input";

export type ArrayModelElement<T> = {
    item: T,
    model: string
}

export type ArrayField<F> = ArrayModelElement<F>[]

export type ArrayInputConfig = {
    
} & InputConfigBase

// TODO: garsuga, implement
export class ArrayInputLayout extends InputLayout<ArrayInputConfig, any[], any[]> {
    toModelValue: (value: any[]) => any[] = (value) => {
        return value;
    }

    fromModelValue: (value: any[]) => any[] = (value) => {
        return value;
    };

    validate: (value: any[]) => boolean = (value) => {
        return true;
    };
}
