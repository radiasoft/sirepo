
import * as msgpack from '@msgpack/msgpack';
import { authState } from '@/services/authstate.js';
import { schema } from '@/services/schema.js';

//TODO(pjm): logging service
const srlog = console.log;
globalThis.sirepoTraceWS = false;

class CookieManager {
    #cookie = null;
    #cookiesVerbatim = null;

    #cookieSave() {
        // Keep two versions for faster checking in cookieCheck
        this.#cookiesVerbatim = document.cookie;
        // save complete value: easier and better for debugging
        const p = authState.cookieName + '=';
        this.#cookie = this.#cookiesVerbatim.split(/\s*;\s*/).find(e => e.startsWith(p)) || null;
    }

    cookieCheck() {
        if (this.#cookiesVerbatim === document.cookie) {
            return false;
        }
        const p = this.#cookie;
        this.#cookieSave();
        // first time is null; server always sends a cookie
        if (! p || p === this.#cookie) {
            return false;
        }
        srlog('authState cookie changed via another browser tab, reloading application');
        //TODO(pjm): implement this
        //uri.globalRedirectRoot();
        //return true;
        throw new Error('unhandled uri.globalRedirectRoot()');
    };

    updateCookies(changeOp) {
        if (this.cookieCheck()) {
            return false;
        }
        changeOp();
        this.#cookieSave();
        return true;
    }
}

class MsgRouter {
    #asyncMsgMethods = {};
    #needReply = {};
    #reqSeq = 1;
    #socket = null;
    #socketRetryBackoff = 0;
    #timeout = null;
    #toSend = [];

    constructor(cookieManager) {
        this.cookieManager = cookieManager;
    }

    #appendBuffers(wsreq, buffers) {
        buffers.splice(0, 0, wsreq.msg);
        const f = new Uint8Array(buffers.reduce((a, b) => a + b.length, 0));
        let i = 0;
        for (const b of buffers) {
            f.set(b, i);
            i += b.length;
        }
        wsreq.msg = f;
    }

    #protocolError(header, content, wsreq, errorMsg) {
        const e = "sirepo.msgRouter protocolError=" + (errorMsg || "invalid reply from server");
        srlog(
            e,
            header.kind === schema.websocketMsg.kind.asyncMsg
                ? ` asyncMsgMethod={header.method}`
                : wsreq && wsreq.header ? ` wsreq={wsreq.header.reqSeq}`
                : "wsreq=null",
            " header=",
            header,
            " content=",
            content
        );
        if (wsreq && wsreq.deferred !== null) {
            wsreq.deferred.reject({
                data: {state: "error", error: e},
                status: 500,
            });
        }
    }

    #reply(blob) {
        let [header, content] = msgpack.decodeMulti(blob);
        const wsreq = this.#needReply[header.reqSeq];
        if (header.version !== schema.websocketMsg.version) {
            this.#protocolError(header, content, wsreq, "invalid version");
            return;
        }
        if (header.kind === schema.websocketMsg.kind.asyncMsg) {
            if (! header.method) {
                this.#protocolError(header, content, wsreq, "missing method in content");
            }
            else if (! (header.method in this.#asyncMsgMethods) ){
                this.#protocolError(header, content, wsreq, `unregistered asyncMsg method=${header.method}`);
            }
            else {
                this.#asyncMsgMethods[header.method](content);
            }
            return;
        }
        const _replyError = (reply) => {
            if (sirepoTraceWS) {
                srlog(`wsreq#${wsreq.header.reqSeq} replyError:`, reply);
            }
            if (wsreq && wsreq.deferred !== null) {
                wsreq.deferred.reject(reply);
            }
        };
        if (! wsreq) {
            this.#protocolError(header, content, null, "reqSeq not found");
            return;
        }
        delete this.#needReply[header.reqSeq];
        if (header.kind === schema.websocketMsg.kind.srException) {
            const n = content.routeName;
            const r = {data: {}};
            if (n === "httpException") {
                r.status = content.params.code;
            }
            else {
                r.data.state = "srException";
                r.data.srException = content;
            }
            _replyError(r);
            return;
        }
        if (header.kind !== schema.websocketMsg.kind.httpReply) {
            this.#protocolError(header, content, wsreq, "invalid websocketMsg.kind");
            return;
        }
        const b = wsreq.responseType === "blob";
        if (content instanceof Uint8Array) {
            if (! b) {
                this.#protocolError(header, content, wsreq, "unexpected blob content");
                return;
            }
            content = new Blob([content]);
        }
        else if (b) {
            if (content.error) {
                _replyError({data: content});
                return;
            }
            this.#protocolError(header, content, wsreq, "expected blob content");
            return;
        }
        else if (wsreq.responseType === "json") {
            if (angular.isString(content)) {
                content = JSON.parse(content);
            }
            else {
                if (content.error) {
                    _replyError({data: content});
                }
                else {
                    _replyError({
                        data: {
                            error: "unknown reply type, expecting json",
                            content: content
                        }
                    });
                }
                return;
            }
        }
        if (sirepoTraceWS) {
            srlog(`wsreq#${wsreq.header.reqSeq} reply:`, content);
        }
        if (wsreq.deferred !== null) {
            wsreq.deferred.resolve({
                data: content,
                status: 200
            });
        }
    }

    #reqData(data, wsreq, done) {
        if (! (data instanceof FormData)) {
            done([data]);
            return;
        }
        var d = {};
        var f = null;
        for (const [k, v] of data.entries()) {
            if (v instanceof File) {
                if (f) {
                    throw new Error(`too many form fields ${f.file.name} and ${v.name}`);
                }
                f = {key: k, file: v};
            }
            else {
                d[k] = v;
            }
        }
        if (! f) {
            done([data]);
            return;
        }
        // a bit of sanity since we assume this on the server side
        if (f.key !== "file") {
            throw new Error("file form fields must be named 'file' name=" + f.key);
        }
        this.#reqDataFile(d, f.key, f.file, done);
    }

    #reqDataFile(data, key, file, done) {
        var r = new FileReader();
        r.readAsArrayBuffer(file);
        r.onerror = (event) => {
            srlog("failed to read file=" + file.name, event);
            //errorService.alertText('Failed to read file=' + file.name);
            return;
        };
        r.onloadend = () => {
            delete data[key];
            done([
                data,
                {filename: file.name, blob: new Uint8Array(r.result),},
            ]);
        };
    }

    #send() {
        //if already req_seq use that so server can know if it is a resend
        if (this.#toSend.length <= 0) {
            return;
        }
        if (this.#socket === null) {
            this.#socketCreate();
            return;
        }
        if (this.#socket.readyState !== 1) {
            return;
        }
        while (this.#toSend.length > 0) {
            const wsreq = this.#toSend.shift();
            this.#needReply[wsreq.header.reqSeq] = wsreq;
            this.#socket.send(wsreq.msg);
        }
    }

    #socketCreate() {
        if (this.#socket !== null) {
            return;
        }
        if (this.cookieManager.cookieCheck()) {
            return;
        }
        this.#socket = Object.assign(
            new WebSocket(
                //new URL($window.location.href).origin.replace(/^http/i, "ws") + "/ws",
                new URL(window.location.href).origin.replace(/^http/i, "ws") + "/ws",
            ),
            {
                onclose: this.#socketError.bind(this),
                onerror: this.#socketError.bind(this),
                onmessage: this.#socketOnMessage.bind(this),
                onopen: this.#socketOnOpen.bind(this),
            },
        );
    }

    #socketError(event) {
        console.log('socketError:', event);
        // close: event.code : short, event.reason : str, wasClean : bool
        // error: app specific
        const retrySocket = () => {
            this.#timeout = null;
            this.#socketCreate();
        };
        this.#socket = null;
        if (this.#timeout) {
            return;
        }
        if (this.#socketRetryBackoff <= 0) {
            this.#socketRetryBackoff = 1;
            srlog("WebSocket failed: event=", event);
            if (! event.wasClean) {
                this.#toSend.unshift(...Object.values(this.#needReply));
                this.#needReply = {};
            }
        }
        //TODO(robnagler) some type of set status to communicate connection lost
        //$interval(_socket, this.#socketRetryBackoff * 1000, 1);
        this.#timeout = setTimeout(
            retrySocket.bind(this),
            this.#socketRetryBackoff * 1000,
        );
        if (this.#socketRetryBackoff < 60) {
            this.#socketRetryBackoff *= 2;
        }
    }

    #socketOnMessage(event) {
        event.data.arrayBuffer().then(
            (blob) => {this.#reply(blob);},
            (error) => {srlog("WebSocket.onmessage error=", error, " event=", event);}
        );
    }

    #socketOnOpen(event) {
        this.#socketRetryBackoff = 0;
        this.#send();
    }

    clearModels() {
        while (this.#toSend.length > 0) {
            this.#toSend.shift().deferred = null;
        }
        for (const v of Object.values(this.#needReply)) {
            v.deferred = null;
        }
        this.#needReply = {};
    }

    registerAsyncMsg(methodName, callback) {
        if (methodName in this.#asyncMsgMethods) {
            throw new Error(`duplicate registerAsyncMsg methodName="${methodName}"`);
        }
        this.#asyncMsgMethods[methodName] = callback;
    }

    send(url, data, httpConfig) {
        if (this.cookieManager.cookieCheck()) {
            // app will reload so return a fake promise
            return {then: () => {}};
        }

        const d = {};
        const p = new Promise((resolve, reject) => {
            Object.assign(d, {resolve, reject });
        });
        const wsreq = {
            //deferred: $q.defer(),
            deferred: d,
            header: {
                kind: schema.websocketMsg.kind.httpRequest,
                reqSeq: this.#reqSeq++,
                uri: decodeURIComponent(url),
                version: schema.websocketMsg.version,
            },
            ...httpConfig,
        };
        wsreq.msg = msgpack.encode(wsreq.header);
        const c = (buffers) => {
            if (buffers) {
                this.#appendBuffers(
                    wsreq,
                    buffers.map((b) => (new msgpack.Encoder()).encodeSharedRef(b)),
                );
            }
            this.#toSend.push(wsreq);
            this.#send();
        };
        if (sirepoTraceWS) {
            srlog(`wsreq#${wsreq.header.reqSeq} send:`, wsreq.header.uri, data);
        }
        if (data === null) {
            c();
        }
        else {
            this.#reqData(data, wsreq, c);
        }
        //return wsreq.deferred.promise;
        return p;
    }
}

export const msgRouter = new MsgRouter(new CookieManager());

//TODO(pjm): will there be other async messages? Otherwise move cookie handling into MsgRouter
msgRouter.registerAsyncMsg('setCookies', (content) => {
    msgRouter.cookieManager.updateCookies(() => {
        for (let c of content) {
            document.cookie = c;
        }
    });
});
