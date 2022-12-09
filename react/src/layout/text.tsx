import React from "react";
import { FunctionComponent, useContext } from "react";
import { Dependency } from "../data/dependency";
import { CModelsWrapper } from "../data/wrapper";
import { useInterpolatedString, ValueSelectors } from "../hook/string";
import { Layout } from "./layout";

export type TextAlign = "left" | "right" | "center"
export type TextType = 'body' | 'header'

export type TextConfig = {
    type: TextType,
    align?: TextAlign,
    text: string
}

export class TextLayout extends Layout<TextConfig, {}> {
    getFormDependencies(): Dependency[] {
        return [];
    }

    component: FunctionComponent<{ [key: string]: any; }> = (props) => {
        let modelsWrapper = useContext(CModelsWrapper);
        
        let interpText = useInterpolatedString(modelsWrapper, this.config.text, ValueSelectors.Models);
        let getTextElement = (type: TextType) => {
            switch(type) {
                case "header":
                    return <h3>{interpText}</h3>;
                case "body":
                    return <p>{interpText}</p>
            }
        }

        let getFlexJustify = (align: TextAlign) => {
            switch(align || "left") {
                case "left":
                    return "flex-start";
                case "right":
                    return "flex-end";
                case "center":
                    return "center";
            }
        }

        let style: React.CSSProperties = {
            display: 'flex',
            justifyContent: getFlexJustify(this.config.align)
        }

        return (
            <div style={style}>
                {getTextElement(this.config.type)}
            </div>
        )
    };
}
