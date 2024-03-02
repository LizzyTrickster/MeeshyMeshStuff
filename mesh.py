import meshtastic
import meshtastic.serial_interface
import time
import json
from pubsub import pub

def on_connect(interface, topic=pub.AUTO_TOPIC):
  interface.sendText("Hello from python")

def onReceive(packet, interface):
  print(f"Got {packet['decoded']}\n<<>><<>>\n")
  if "neko" in packet['decoded']['text']:
    print("NYA?!")
    interface.sendText("Nyaaaa")

pub.subscribe(onReceive, "meshtastic.receive")

pub.subscribe(on_connect, "meshtastic.connection.established")

interface = meshtastic.serial_interface.SerialInterface(devPath="/dev/ttyACM0")

for i in range(1000):
    time.sleep(1)
