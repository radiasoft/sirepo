import { InputConfigBase, InputLayout } from "./input";

export type ArrayInputConfig = {
    models: string[]
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
