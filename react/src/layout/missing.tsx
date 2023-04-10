import React from "react";
import { Layout } from "./layout";

export class MissingLayout extends Layout<undefined, {}> {
    component = (props) => {
        return <>Missing layout!</>;
    }
}
