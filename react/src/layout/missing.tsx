import React from "react";
import { Layout } from "./layout";

export class MissingLayout extends Layout<undefined, {}> {
    getFormDependencies = () => {
        return [];
    }

    component = (props) => {
        return <>Missing layout!</>;
    }
}
