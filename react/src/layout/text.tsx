import React from "react";
import { FunctionComponent, useContext } from "react";
import { Dependency } from "../data/dependency";
import { CModelsWrapper } from "../data/wrapper";
import { useInterpolatedString, ValueSelectors } from "../hook/string";
import { Layout } from "./layout";

export type TextConfig = {
    type: 'body' | 'header',
    text: string
}

export class TextLayout extends Layout<TextConfig, {}> {
    getFormDependencies(): Dependency[] {
        return [];
    }

    component: FunctionComponent<{ [key: string]: any; }> = (props) => {
        let modelsWrapper = useContext(CModelsWrapper);
        
        let interpText = useInterpolatedString(modelsWrapper, this.config.text, ValueSelectors.Models);

        switch(this.config.type) {
            case "header":
                return <h3>{interpText}</h3>;
            case "body":
                return <p>{interpText}</p>
            
        }
    };
}
