import "./table.scss";

export function Table(props) {
    let { rows, columnNames, rowNames } = props;

    let hasRowNames = rowNames && rowNames.length > 0;
    let hasColumnNames = columnNames && columnNames.length > 0;

    let rowElements = [];

    if(hasColumnNames) {
        rowElements.push(
            <thead>
                <tr className="sr-table-row-header sr-table-row">
                    {
                        hasRowNames && <td></td>
                    }
                    {
                        columnNames.map(columnName => <td className="sr-table-cell sr-table-cell-header">{columnName}</td>)
                    }
                </tr>
            </thead>
            
        )
    }

    rowElements.push(
        <tbody>
            {
                (rows.map((row, idx) => {
                    return (
                        <tr className="sr-table-row sr-table-row-body">
                            { hasRowNames && <td className="sr-table-cell-header sr-table-cell">{rowNames[idx]}</td> }
                            { row.map(colVal => <td className="sr-table-cell sr-table-cell-body">{`${colVal}`}</td>)}
                        </tr>
                    )
                }))
            }
        </tbody>
    )

    return (
        <table className="sr-table">
            {rowElements}
        </table>
    )
}
