var msgpack = require("msgpackr");
var zmq = require("zeromq");
var requester = new zmq.Request();

async function main() {
    requester.connect("tcp://127.0.0.1:5567");

    for (var i = 0; i < 3; i++) {
        var req = msgpack.pack({ a: 2 * i, b: 3 });
        await requester.send(req);
        var [msg] = await requester.receive();
        var rep = msgpack.unpack(msg);
        console.log(`product: ${rep.product}`, `quotient: ${rep.quotient}`);
    }

    requester.close();
}

main();
