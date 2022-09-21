const mqtt = require("mqtt");
const rest = require("restler");
const event_key = "jjNOhqJ1_fgJ9FV3KE_G4W-uB9rBetCStQHoIhkLuhS";
const drone = "forest/iot/alert";
const url = "mqtt://192.168.1.184";

const options = {
    port: 1883,
    host: url,
    clientId: "drone_" + Math.random().toString(16).substr(2, 8),
    username: "guest",
    password: "guest",
};

function sendFeedbackMqtt(q, msg) {
    const client = mqtt.connect(url, options);
    client.on("connect", function() {
        client.publish(q, msg, { qos: 2 }, function() {
            client.end();
        });
    });
}

exports.handler = function(context, event) {
    var obj = JSON.parse(event.body);

    if (obj.sensor == "FIRE_BALL_RELEASED") {
        obj.sensor = "FIRE_OFF";
        droneStr = JSON.stringify(obj);

        sendFeedbackMqtt(drone, droneStr);
        rest
            .post(
                "https://maker.ifttt.com/trigger/fire_notification/with/key/" +
                event_key, {
                    data: {
                        value1: obj.sensor,
                        value2: obj.position[0],
                        value3: obj.position[1],
                    },
                }
            )
            .on("complete", function(data) {
                console.log(
                    "Forest status: " +
                    obj.sensor +
                    "Latitude: " +
                    obj.position[0] +
                    "Longitude: " +
                    obj.position[1]
                );
            });
    }
    context.callback("");
};