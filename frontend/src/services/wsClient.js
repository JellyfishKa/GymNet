export class LiveWsClient {
    constructor(url, onMessage) {
        this.socket = new WebSocket(url);
        this.socket.onmessage = (event) => {
            onMessage(JSON.parse(event.data));
        };
    }
    send(payload) {
        if (this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(payload));
        }
    }
}
