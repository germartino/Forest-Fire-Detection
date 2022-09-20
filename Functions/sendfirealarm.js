var mqtt = require("mqtt");
var url = require("url");

var mqtt_url = url.parse(
    process.env.CLOUDAMQP_MQTT_URL || "mqtt://guest:guest@192.168.1.184:1883"
);
var auth = (mqtt_url.auth || ":").split(":");
var url = "mqtt://" + mqtt_url.host;
var options = {
    port: mqtt_url.port,
    clientId: "forest_" + Math.random().toString(16).substr(2, 8),
    username: auth[0],
    password: auth[1],
};

exports.handler = function(context, event) {
    var client = mqtt.connect(url, options);

    client.on("connect", function() {
        var alarm = '{"sensor":"FIRE_ON","position":[47.397606,8.543060]}';

        client.publish("forest/iot/fire", alarm, function() {
            client.end();
            context.callback("Sent: " + alarm);
        });
    });
};