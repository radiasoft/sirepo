import React from "react";
import { FunctionComponent } from "react";
import { InputComponentProps, InputConfigBase, InputLayout } from "./input";

export type ValueListInputConfig = {

} & InputConfigBase

export class ValueListInputLayout extends InputLayout<ValueListInputConfig, any ,any> {
    toModelValue: (value: any) => any = (v) => v;
    fromModelValue: (value: any) => any = (v) => v;
    validate: (value: any) => boolean = () => true;

    component: FunctionComponent<InputComponentProps<{}>> = (props) => {
        return <select disabled={true}></select>
    }
}
