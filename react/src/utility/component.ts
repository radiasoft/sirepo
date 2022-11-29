/* eslint eqeqeq: 0 */
/* eslint no-unused-vars: 0 */
import React, { RefObject, useLayoutEffect, useState } from 'react';
import { debounce } from './debounce';

export function constrainZoom(transformMatrix, size, dimension) {
    if (transformMatrix[`scale${dimension}`] < 1) {
        transformMatrix[`scale${dimension}`] = 1;
        transformMatrix[`translate${dimension}`] = 0;
    }
    else {
        if (transformMatrix[`translate${dimension}`] > 0) {
            transformMatrix[`translate${dimension}`] = 0;
        }
        else if (size * transformMatrix[`scale${dimension}`] + transformMatrix[`translate${dimension}`] < size) {
            transformMatrix[`translate${dimension}`] = size - size * transformMatrix[`scale${dimension}`];
        }
    }
    return transformMatrix;
}

const xAxisSize = 30;
const yAxisSize = 60;
const margin = 25;

function graphContentHeightOffset() {
    return xAxisSize + margin * 2;
}

function graphContentWidthOffset() {
    return yAxisSize + margin * 2;
}

export type Dimension = {
    height: number,
    width: number
}

function useRefSize(ref: RefObject<HTMLElement>): [Dimension, React.Dispatch<React.SetStateAction<Dimension>>] {
    const [dim, setDim] = useState({
        width: 1000,
        height: 1000,
    });
    useLayoutEffect(() => {
        if (! ref || ! ref.current || ! ref.current.offsetWidth) {
            return () => {};
        }
        const handleResize = debounce(() => {
            const w = ref.current.offsetWidth;
            if (dim.width != w) {
                setDim({
                    width: w,
                    height: ref.current.offsetHeight,
                });
            }
        }, 250);
        window.addEventListener('resize', handleResize);
        handleResize();
        return () => {
            window.removeEventListener('resize', handleResize);
        };
    });
    return [dim, setDim];
}

export function useGraphContentBounds(ref, aspectRatio) {
    const [dim, setDim] = useRefSize(ref);
    const h = graphContentHeightOffset() + ((dim.width - graphContentWidthOffset()) * aspectRatio);
    if (h != dim.height) {
        setDim({
            width: dim.width,
            height: h,
        });
    }
    return {
        contentWidth: dim.width,
        contentHeight: dim.height,
        height: dim.height - graphContentHeightOffset(),
        width: dim.width - graphContentWidthOffset(),
        x: yAxisSize + margin,
        y: margin,
    };
}
