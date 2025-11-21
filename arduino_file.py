#include <ESP8266WiFi.h>
#include <WiFiClient.h>
#include <ESP8266WebServer.h>
#include <DHT.h>
#include <OneWire.h>
#include <DallasTemperature.h>
 
// --- DHT22 setup ---
#define DHTPIN 2
#define DHTTYPE DHT22
DHT dht(DHTPIN, DHTTYPE, 11); // threshold 11 works for ESP8266
 
// --- DS18B20 setup ---
#define ONE_WIRE_BUS 4 // D4
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature ds18b20(&oneWire);
 
// --- WiFi settings ---
const char* ssid     = "DAH-lab";
const char* password = "AbbeyRoadAlbum";
 
ESP8266WebServer server(80);
 
// --- Variables ---
float humidity, temp_f;
float tempDS1 = 0.0, tempDS2 = 0.0;
String webString = "";
unsigned long previousMillis = 0;
const long interval = 2000;
 
// --- Function prototypes ---
void gettemperature();
 
void setup() {
  Serial.begin(115200);
  dht.begin();
  ds18b20.begin();
 
  // Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.print("\nConnecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
 
  // --- Web server routes ---
  server.on("/", [](){
    server.send(200, "text/plain", "Hello from ESP8266 weather server! Read /temp, /humidity, /ds1, /ds2");
  });
 
  // --- Return DHT22 Sensor Temperature Readings ---
  server.on("/temp", [](){
    gettemperature();
    webString = temp_f;
    server.send(200, "text/plain", webString);
  });
 
  // --- Return DHT22 Sensor Humidity Readings ---
  server.on("/humidity", [](){
    gettemperature();
    webString = humidity;
    server.send(200, "text/plain", webString);
  });
 
  // --- Return the First DS18B20 Sensors Temperature Readings ---
  server.on("/ds1", [](){
    ds18b20.requestTemperatures();
    tempDS1 = ds18b20.getTempCByIndex(0);
    webString = tempDS1; 
    server.send(200, "text/plain", webString);
  });
 
  // --- Return the Second DS18B20 Sensors Temperature Readings, making sure it is present ---
  server.on("/ds2", [](){
    ds18b20.requestTemperatures();
    if (ds18b20.getDeviceCount() > 1) {
      tempDS2 = ds18b20.getTempCByIndex(1);
      webString = tempDS2 ;
    } else {
      webString = "DS18B20 #2 not found!";
    }
    server.send(200, "text/plain", webString);
  });
 
  server.begin(); //Start HTTP servr
  Serial.println("HTTP server started");
}
 
 
void loop() {
  server.handleClient();  // Listen for incoming HTTP requests
}
 
// --- Only read the DHT22 if at least 2 seconds have passed. The DHT22 cannot be read too frequently or it returns NaN. ---
void gettemperature() {
  unsigned long currentMillis = millis();
  if(currentMillis - previousMillis >= interval) {
    previousMillis = currentMillis;
 
// --- Read Humidity and Temperature (In Fahrenheit) ---
    humidity = dht.readHumidity();
    temp_f = dht.readTemperature(true);
 
// --- If the DHT22 failed to return valid data, print an error message. ---
    if (isnan(humidity) || isnan(temp_f)) {
      Serial.println("Failed to read from DHT sensor!");
    }
  }
}
