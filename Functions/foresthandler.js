const mqtt = require("mqtt");
const rest = require("restler");
const event_key = "jjNOhqJ1_fgJ9FV3KE_G4W-uB9rBetCStQHoIhkLuhS";
const forest = "forest/iot/alert";
const url = "mqtt://192.168.1.184";

const options = {
    port: 1883,
    host: url,
    clientId: "forest_" + Math.random().toString(16).substr(2, 8),
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
    var forestJson = JSON.parse(event.body);

    if (forestJson.sensor == "FIRE_ON") {
        sendFeedbackMqtt(forest, event.body);
        rest
            .post(
                "https://maker.ifttt.com/trigger/fire_notification/with/key/" +
                event_key, {
                    data: {
                        value1: forestJson.sensor,
                        value2: forestJson.position[0],
                        value3: forestJson.position[1],
                    },
                }
            )
            .on("complete", function(data) {
                console.log(
                    "Forest status: " +
                    forestJson.sensor +
                    "Latitude: " +
                    forestJson.position[0] +
                    "Longitude: " +
                    forestJson.position[1]
                );
            });
    } else {
        sendFeedbackMqtt(forest, event.body);
    }
    context.callback("");
};