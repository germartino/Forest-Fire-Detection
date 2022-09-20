#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <LiquidCrystal.h>
#include <ArduinoJson.h>

#define BUZ 21
#define LED 12
const int flameSensor = 5;
// Replace the next variables with your SSID/Password combination
const char* ssid = "*****";
const char* password = "*****";

// Add your MQTT Broker IP address, example:
const char* mqtt_server = "192.168.1.184";
const int mqtt_port = 1883;

WiFiClient espClient;
PubSubClient client(espClient);
LiquidCrystal lcd(19, 23, 18, 17, 16, 15);
StaticJsonDocument<256> forest;

long lastMsg = 0;
char msg[50];
char out[128];

void setup() {

  Serial.begin(115200);
  lcd.begin(16, 2);
  pinMode(LED, OUTPUT);
  pinMode(BUZ, OUTPUT);
  pinMode(flameSensor, INPUT);

  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
}

void setup_wifi() {
  delay(10);
  // We start by connecting to a WiFi network
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
}

void callback(char* topic, byte* message, unsigned int length) {
  Serial.print("Message arrived on topic: ");
  Serial.print(topic);
  Serial.print(". Message: ");
  String messageTemp;

  for (int i = 0; i < length; i++) {
    Serial.print((char)message[i]);
    messageTemp += (char)message[i];
  }
  Serial.println();

  if (String(topic) == "forest/iot/alert") {
    deserializeJson(forest, messageTemp);
    String sensor = forest["sensor"];
    if (sensor == "FIRE_OFF") {
      Serial.print("FIRE EXTINGUISHED!");
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("FIRE EXTINGUISHED!");
      digitalWrite(BUZ, LOW);
      digitalWrite(LED, LOW);
    }
  }
  else if (String(topic) == "forest/iot/sensors") {
    deserializeJson(forest, messageTemp);
    String sensor = forest["sensor"];
    if (sensor == "FIRE_ON") {
      Serial.print("FIRE DETECTED!");
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("FIRE DETECTED!");
      digitalWrite(BUZ, HIGH);
      digitalWrite(LED, HIGH);
    }
  }
}

void reconnect() {
  // Loop until we're reconnected
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    // Attempt to connect
    if (client.connect("IoT-Forest-Sensors ")) {
      Serial.println("connected");
      // Subscribe
      client.subscribe("forest/iot/alert");
      client.subscribe("forest/iot/sensors");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      // Wait 5 seconds before retrying
      delay(5000);
    }
  }
}
void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  long now = millis();
  if (now - lastMsg > 5000) {
    lastMsg = now;

    // Read from flame sensor
    int flame = digitalRead(flameSensor);

    if (flame == 1) {
      Serial.print("FIRE DETECTED!");
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("ALERT: ");
      lcd.setCursor(0, 1);
      lcd.print("FIRE DETECTED!");

      digitalWrite(BUZ, HIGH);
      digitalWrite(LED, HIGH);

      //char fireString[8] = "FIRE_ON";
      forest["sensor"] = "FIRE_ON";

      JsonArray data = forest.createNestedArray("position");
      data.add(47.397606);
      data.add(8.543060);
      // Generate the minified JSON and send it to the Serial port.
//      char out[128];
      serializeJson(forest, out);
      client.publish("forest/iot/sensors", out);
    }
    memset(out, 0, sizeof(out));

  }
}
