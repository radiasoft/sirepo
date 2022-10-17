/* eslint eqeqeq: 0 */
/* eslint no-unused-vars: 0 */
import { useEffect, useLayoutEffect, useRef, useState } from 'react';

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

//TODO(pjm): use a library?
export function debounce(fn, ms) {
    let timer
    return _ => {
        clearTimeout(timer)
        timer = setTimeout(_ => {
            timer = null
            fn.apply(this, arguments)
        }, ms)
    };
}

const xAxisSize = 30;
const yAxisSize = 60;
const margin = 25;

function heightAdjustment() {
    return xAxisSize + margin * 2;
}

function widthAdjustment() {
    return yAxisSize + margin * 2;
}

export function graphMetrics(dim) {
    return {
        graphHeight: dim.height - heightAdjustment(),
        graphWidth: dim.width - widthAdjustment(),
        graphX: yAxisSize + margin,
        graphY: margin,
    };
}

export function useRefSize(ref, aspectRatio) {
    const [dim, setDim] = useState({
        width: 1000,
        height: 1000,
    });
    useLayoutEffect(() => {
        if (! ref || ! ref.current) {
            return;
        }
        const handleResize = debounce(() => {
            if (! ref || ! ref.current) {
                return;
            }
            const w = Number.parseInt(ref.current.offsetWidth);
            const h = heightAdjustment() + Number.parseInt((w - widthAdjustment()) * aspectRatio);
            setDim({
                width: w,
                height: h,
            });
        }, 250);
        window.addEventListener('resize', handleResize);
        handleResize();
        return _ => {
            window.removeEventListener('resize', handleResize);
        };
    }, [ref]);
    return dim;
}
