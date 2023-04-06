import React from "react";

export type FlexJustify = "start" | "end" | "center" | "between" | "around";
export type FlexAlign = "start" | "end" | "center" | "baseline" | "stretch";
export type FlexWrap = "nowrap" | "wrap" | "wrap-reverse";

export type BaseStackProps = {
    justifyContent?: FlexJustify,
    alignItems?: FlexAlign,
    wrap?: FlexWrap
} & {[key: string]: any}

function getFlexboxClassName(props: BaseStackProps) {
    let flexboxClassName = "";
    if(props.justifyContent) {
        flexboxClassName += ` justify-content-${props.justifyContent}`
    }
    if(props.alignItems) {
        flexboxClassName += ` align-items-${props.alignItems}`
    }
    if(props.wrap) {
        flexboxClassName += ` flex-${props.wrap}`
    } else {
        flexboxClassName += " flex-nowrap";
    }
    return flexboxClassName.trim();
}

export type HorizontalStackProps = BaseStackProps

export function HorizontalStack(props: HorizontalStackProps) {
    let className = getFlexboxClassName(props) + " d-flex h-100 w-100 flex-row"; // TODO: eval classnames

    return (
        <div className={className}>
            {
                props.children
            }
        </div>
    )
}

export type VerticalStackProps = BaseStackProps

export function VerticalStack(props: VerticalStackProps) {
    let className = getFlexboxClassName(props) + " d-flex w-100 flex-column";

    return (
        <div className={className}>
            {
                props.children
            }
        </div>
    )
}
