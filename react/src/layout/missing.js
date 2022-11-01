import React from "react";
import { View } from "./layout";

export class MissingLayout extends View {
    getFormDependencies = (config) => {
        return [];
    }

    component = (props) => {
        return <>Missing layout!</>;
    }
}
