var msgpack = require("msgpackr");
var zmq = require("zeromq");
var sock = new zmq.Subscriber();

sock.connect("tcp://127.0.0.1:5566");
sock.subscribe("datetime");
console.log("Subscribing to datetime of clock");

async function main() {
    for await (const [topic, message] of sock) {
        if (topic.toString() !== "datetime") {
            continue;
        }
        var msg = msgpack.unpack(message);
        console.log(
            `${msg.year}-${msg.month}-${msg.day} ${msg.hour}:${msg.minute}:${msg.second}`
        );
    }
}

main();
