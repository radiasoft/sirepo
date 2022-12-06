import React from "react";

export type TableConfig = {
    rows: number[][],
    columnNames: string[],
    rowNames: string[]
}

export function Table(props: TableConfig) {
    let { rows, columnNames, rowNames } = props;

    let hasRowNames = rowNames && rowNames.length > 0;
    let hasColumnNames = columnNames && columnNames.length > 0;

    let rowElements = [];

    if(hasColumnNames) {
        rowElements.push(
            <thead key="thead">
                <tr>
                    {
                        hasRowNames && <th></th>
                    }
                    {
                        columnNames.map(columnName => <th key={columnName} className="text-end">{columnName}</th>)
                    }
                </tr>
            </thead>

        )
    }

    rowElements.push(
        <tbody key="tbody">
            {
                (rows.map((row, idx) => {
                    return (
                        <tr key={`row${idx}`}>
                            { hasRowNames && <th key={rowNames[idx]}>{rowNames[idx]}</th> }
                            { row.map((colVal, idx2) => <td key={`${idx2} ${colVal}`} className="text-end">{`${colVal}`}</td>)}
                        </tr>
                    )
                }))
            }
        </tbody>
    )

    return (
        <div className="col-sm-12">
            <table className="table">
                {rowElements}
            </table>
        </div>
    )
}
