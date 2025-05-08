
import * as msgpack from '@msgpack/msgpack';

//TODO(pjm): logging service
const srlog = console.log;

//SIREPO.app.factory('msgRouter', ($interval, $q, $window, authState, errorService) => {
export const msgRouter = {
    asyncMsgMethods: {},
    toSend: [],
    needReply: {},
    reqSeq: 1,
    socket: null,
    socketRetryBackoff:  0,

    _appendBuffers(wsreq, buffers) {
        buffers.splice(0, 0, wsreq.msg);
        const f = new Uint8Array(buffers.reduce((a, b) => a + b.length, 0));
        let i = 0;
        for (const b of buffers) {
            f.set(b, i);
            i += b.length;
        }
        wsreq.msg = f;
    },

    _protocolError(header, content, wsreq, errorMsg) {
        const e = "sirepo.msgRouter protocolError=" + (errorMsg || "invalid reply from server");
        srlog(
            e,
            header.kind === SIREPO.APP_SCHEMA.websocketMsg.kind.asyncMsg
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
    },

    _reply(blob) {
        let [header, content] = msgpack.decodeMulti(blob);
        const wsreq = this.needReply[header.reqSeq];
        if (header.version !== SIREPO.APP_SCHEMA.websocketMsg.version) {
            this._protocolError(header, content, wsreq, "invalid version");
            return;
        }
        if (header.kind === SIREPO.APP_SCHEMA.websocketMsg.kind.asyncMsg) {
            if (! header.method) {
                this._protocolError(header, content, wsreq, "missing method in content");
            }
            else if (! (header.method in this.asyncMsgMethods) ){
                this._protocolError(header, content, wsreq, `unregistered asyncMsg method=${header.method}`);
            }
            else {
                this.asyncMsgMethods[header.method](content);
            }
            return;
        }
        const _replyError = (reply) => {
            if (SIREPO.traceWS) {
                srlog(`wsreq#${wsreq.header.reqSeq} replyError:`, reply);
            }
            if (wsreq && wsreq.deferred !== null) {
                wsreq.deferred.reject(reply);
            }
        };
        if (! wsreq) {
            this._protocolError(header, content, null, "reqSeq not found");
            return;
        }
        delete this.needReply[header.reqSeq];
        if (header.kind === SIREPO.APP_SCHEMA.websocketMsg.kind.srException) {
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
        if (header.kind !== SIREPO.APP_SCHEMA.websocketMsg.kind.httpReply) {
            this._protocolError(header, content, wsreq, "invalid websocketMsg.kind");
            return;
        }
        const b = wsreq.responseType === "blob";
        if (content instanceof Uint8Array) {
            if (! b) {
                this._protocolError(header, content, wsreq, "unexpected blob content");
                return;
            }
            content = new Blob([content]);
        }
        else if (b) {
            if (content.error) {
                _replyError({data: content});
                return;
            }
            this._protocolError(header, content, wsreq, "expected blob content");
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
        if (SIREPO.traceWS) {
            srlog(`wsreq#${wsreq.header.reqSeq} reply:`, content);
        }
        if (wsreq.deferred !== null) {
            wsreq.deferred.resolve({
                data: content,
                status: 200
            });
        }
    },

    _reqData(data, wsreq, done) {
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
        this._reqDataFile(d, f.key, f.file, done);
    },

    _reqDataFile(data, key, file, done) {
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
    },

    _send() {
        //if already req_seq use that so server can know if it is a resend
        if (this.toSend.length <= 0) {
            return;
        }
        if (this.socket === null) {
            this._socket();
            return;
        }
        if (this.socket.readyState !== 1) {
            return;
        }
        while (this.toSend.length > 0) {
            const wsreq = this.toSend.shift();
            this.needReply[wsreq.header.reqSeq] = wsreq;
            this.socket.send(wsreq.msg);
        }
    },

    _socket() {
        if (this.socket !== null) {
            return;
        }
        //TODO(pjm): support cookies
        //if (authState.cookieCheck()) {
        //    return;
        //}
        const s = new WebSocket(
            //new URL($window.location.href).origin.replace(/^http/i, "ws") + "/ws",
            new URL(window.location.href).origin.replace(/^http/i, "ws") + "/ws",
        );
        s.onclose = this._socketError.bind(this);
        s.onerror = this._socketError.bind(this);
        s.onmessage = this._socketOnMessage.bind(this);
        s.onopen = this._socketOnOpen.bind(this);
        this.socket = s;
    },

    _socketError(event) {
        // close: event.code : short, event.reason : str, wasClean : bool
        // error: app specific
        this.socket = null;
        if (this.socketRetryBackoff <= 0) {
            this.socketRetryBackoff = 1;
            srlog("WebSocket failed: event=", event);
            if (! event.wasClean) {
                this.toSend.unshift(...Object.values(this.needReply));
                this.needReply = {};
            }
        }
        //TODO(robnagler) some type of set status to communicate connection lost
        //$interval(_socket, this.socketRetryBackoff * 1000, 1);
        setTimeout(this._socket.bind(this), this.socketRetryBackoff * 1000);

        if (this.socketRetryBackoff < 60) {
            this.socketRetryBackoff *= 2;
        }
    },

    _socketOnMessage(event) {
        event.data.arrayBuffer().then(
            (blob) => {this._reply(blob);},
            (error) => {srlog("WebSocket.onmessage error=", error, " event=", event);}
        );
    },

    _socketOnOpen(event) {
        this.socketRetryBackoff = 0;
        this._send();
    },

    clearModels() {
        while (this.toSend.length > 0) {
            this.toSend.shift().deferred = null;
        }
        for (const v of Object.values(this.needReply)) {
            v.deferred = null;
        }
        this.needReply = {};
    },

    registerAsyncMsg(methodName, callback) {
        if (methodName in this.asyncMsgMethods) {
            throw new Error(`duplicate registerAsyncMsg methodName="${methodName}"`);
        }
        this.asyncMsgMethods[methodName] = callback;
    },

    send(url, data, httpConfig) {
        //TODO(pjm): support cookies
        //if (authState.cookieCheck()) {
        //    // app will reload so return a fake promise
        //    return {then: () => {}};
        //}

        const d = {};
        const p = new Promise((resolve, reject) => {
            Object.assign(d, {resolve, reject });
        });
        const wsreq = {
            //deferred: $q.defer(),
            deferred: d,
            header: {
                kind: SIREPO.APP_SCHEMA.websocketMsg.kind.httpRequest,
                reqSeq: this.reqSeq++,
                uri: decodeURIComponent(url),
                version: SIREPO.APP_SCHEMA.websocketMsg.version,
            },
            ...httpConfig,
        };
        wsreq.msg = msgpack.encode(wsreq.header);
        const c = (buffers) => {
            if (buffers) {
                this._appendBuffers(
                    wsreq,
                    buffers.map((b) => (new msgpack.Encoder()).encodeSharedRef(b)),
                );
            }
            this.toSend.push(wsreq);
            this._send();
        };
        if (SIREPO.traceWS) {
            srlog(`wsreq#${wsreq.header.reqSeq} send:`, wsreq.header.uri, data);
        }
        if (data === null) {
            c();
        }
        else {
            this._reqData(data, wsreq, c);
        }
        //return wsreq.deferred.promise;
        return p;
    },
};
