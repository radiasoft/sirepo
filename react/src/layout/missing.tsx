import React from "react";
import { View } from "./layout";

export class MissingLayout extends View<undefined, {}> {
    getFormDependencies = () => {
        return [];
    }

    component = (props) => {
        return <>Missing layout!</>;
    }
}
