export function downloadAs(blob: Blob, fileName: string) {
    const aElement = document.createElement('a');
    aElement.setAttribute('download', fileName);
    const href = URL.createObjectURL(blob);
    aElement.href = href;
    aElement.setAttribute('target', '_blank');
    aElement.click();
    URL.revokeObjectURL(href);
}


export function getAttachmentFileName(response: Response) {
    let pattern = /filename=["]?([\w.\-_]+)["]?/g
    let match = pattern.exec(response.headers.get('content-disposition'));
    return match[1];
}
