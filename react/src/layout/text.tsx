import React from "react";
import { FunctionComponent, useContext } from "react";
import { StoreTypes } from "../data/data";
import { CHandleFactory } from "../data/handle";
import { interpolate } from "../utility/string";
import { Layout } from "./layout";

export type TextAlign = "left" | "right" | "center"
export type TextType = 'body' | 'header'

export type TextConfig = {
    type: TextType,
    align?: TextAlign,
    text: string
}

export class TextLayout extends Layout<TextConfig, {}> {
    component: FunctionComponent<{ [key: string]: any; }> = (props) => {
        let handleFactory = useContext(CHandleFactory);
        
        let interpText = interpolate(this.config.text).withDependencies(handleFactory, StoreTypes.Models).raw();
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
