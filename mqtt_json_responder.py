#!/usr/bin/env python3
# Copyright Lizzy Trickster (Lizzy Green)
import aiofiles
import asyncio
import json
import os.path
import random
import re
import time
from collections import namedtuple
from datetime import datetime as dt
from typing import Any

import paho.mqtt.client as mqtt
from asyncio_paho.client import AsyncioPahoClient
from box import Box

MQTT_ROOT: str = os.environ.get("MQTT_ROOT", "MESHY")
MQTT_HOST: str = os.environ.get("MQTT_HOST", "192.168.0.17")
MQTT_USER: str = os.environ.get("MQTT_USER", "mqtt")
MQTT_PASS: str = os.environ.get("MQTT_PASS", "mqtt")
RESPONSES_TO_LISTEN_FOR = [
    # Add your own ones in here, please don't steal my nodename :)
    "lizb signal check",
    "can you hear me lizb?",
    "lizb are you receiving?",
    "anyone receiving??"
    # Notice double question mark, this is to avoid spamming the channel if someone clueless just wants to see if anyone
    # can hear them.

]
RECEIVING_NODES = {
    # These should match the "sender" field on the JSON MQTT payloads. CASE SENSITIVE. They're used on line 83
    "!75e9a1cc": "LiZT",
    "!035e8236": "LiZB"
}

topic_regex = re.compile(r"(?P<ROOT>[\w/]+)/\d/(?P<TYPE>\w+)/(?P<CHANNEL>\w+)/(?P<NODE>![a-f0-9]+)")
NODES = Box(default_box=True)
# In memory storage of node info, uses a python-box Box instead of dict, so I can use dot-notation to access the content

try:
    if os.path.exists("nodedb.yaml") and os.path.getsize("nodedb.yaml") > 0:
        with open("nodedb.yaml", "r") as f:
            NODES = Box.from_yaml(f.read(), default_box=True)
except FileNotFoundError:
    pass


async def handle_json_mqtt(client, msg: mqtt.MQTTMessage):
    data = Box.from_json(msg.payload.decode("utf-8"), frozen_box=True)  # Frozen box prevents accidental changes
    if data.type == "sendtext":  # Someone sending text, don't process it
        return

    sender = data['from']
    if sender not in NODES:
        NODES[sender] = dict(as_hex=hex(sender))

    NODES[sender].last_message = dict(ts=dt.now(), type=data.type)
    NODES[sender].message_type_stats[data.type or "_"].latest = dt.now()  # _ here if we got a blank type
    NODES[sender].message_type_stats[data.type or "_"].count = NODES[sender].META_stats[data.type].get("count", 0) + 1

    # RSSI/SNR is not included in the JSON if publishing node is also the sender, in that case we just set them to 0
    NODES[sender].latest_rssi = data.get("rssi", 0)
    NODES[sender].latest_snr = data.get("snr", 0)

    NODES[sender].latest_hops = data.get("hops_away", -1)  # -1 to indicate random edgecases or firmware <2.3.0

    match data.type:
        case "nodeinfo":
            NODES[sender].hardware = data.payload.hardware
            NODES[sender].shortname = data.payload.shortname
            NODES[sender].longname = data.payload.longname
        case "position":
            NODES[sender].position = dict(
                lat=(data.payload.latitude_i * 1e7) / 100000000000000,
                lon=(data.payload.longitude_i * 1e7) / 100000000000000,
                alt=data.payload.get("altitude", 0),  # .get() here cause sometimes altitude isn't in the payload...
                tim=data.payload.get("time", 0))
        case "telemetry":
            NODES[sender].telemetry = dict(
                tx_util=data.payload.air_util_tx,
                batt=data.payload.battery_level,
                chan_util=data.payload.channel_utilization,
                voltage=data.payload.voltage)
            # TODO: more telemetry here, need to stick stuff on my nodes for them to report the data
        case "text":
            if data.payload.text.lower() in RESPONSES_TO_LISTEN_FOR:
                receiver = RECEIVING_NODES[data.sender]  # data.sender here is the node that uplinked to MQTT
                sender_name = NODES[sender].get("shortname", f"!{hex(sender).lstrip('0x')} (your nodeinfo is not yet in my DB)")
                distance = f"{data.hops_away} hops away" if data.hops_away else f"direct (RSSI:{data.rssi}|SNR:{data.snr}) (or not 2.3.X)"
                await send_message(client,
                                   f"Hello {sender_name}!\n{receiver} hears you {distance}",
                                   channel=data.get("channel", 0),  # Return to sender (vaguely...)
                                   sender=int(data.sender.lstrip("!"), 16)
                                   # strips the ! from the start, then converts the hex to base-10 int
                                   )


async def on_connect(client: AsyncioPahoClient, userdata: Any, flags: dict[str, Any], result: int):
    await client.asyncio_subscribe(f"{MQTT_ROOT}/2/json/#")


async def on_message(client, userdata, msg):
    try:
        match = topic_regex.match(msg.topic)
        data = match.groupdict()
        print(data)
        match data['TYPE']:
            case "json":
                print("Handling JSON")
                print(msg.payload)
                await handle_json_mqtt(client, msg)
    except Exception as e:
        print(e)


async def send_message(c: AsyncioPahoClient, message: str, channel: int = 0, sender: int = 0):
    to_send = {"payload": message, "channel": channel, "type": "sendtext", "from": sender}
    await asyncio.sleep(random.random())
    await c.asyncio_publish(f"{MQTT_ROOT}/2/json/mqtt", json.dumps(to_send))



subprocess_return = namedtuple("subprocess_return", ['stdout', 'stderr', 'exit_code'])


async def run_shell(command) -> subprocess_return:
    proc = await asyncio.create_subprocess_shell(command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    return subprocess_return(stdout=stdout.decode() if stdout is not None else None,
                             stderr=stderr.decode() if stderr is not None else None,
                             exit_code=proc.returncode)


async def save_node_db():
    # If you wonder why this saves to a different file then mv's it in place:
    # In write mode, Python will open the file, truncate it then write the contents when the file object is flushed
    # (in this case that's when it exits the async with context).
    # I have been burned a few times when I have had a script saving data and the disk has been filled up by some other
    # process. With a straight write to the file, Python ended up losing the contents if it wasn't able to save it
    # fully, then (if not also accounted for) errors out the function and crashes the app, losing the data in memory too
    # NOTE: If you are on windows: firstly, why?, secondly, edit this function so that it saves direct to the file
    while True:
        NODES.META_last_write = time.time()
        async with aiofiles.open("_nodedb.yaml", "w") as f:
            await f.write(NODES.to_yaml(sort_keys=True))
        await run_shell(f"mv _nodedb.yaml nodedb.yaml")
        # print("Donna Noble has left the library, Donna Noble has been saved")
        await asyncio.sleep(5)


async def main():
    # client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    async with AsyncioPahoClient() as client:
        client.asyncio_listeners.add_on_connect(on_connect)
        client.asyncio_listeners.add_on_message(on_message)

        if MQTT_USER is not None or (MQTT_USER is not None and MQTT_PASS is not None):
            client.username_pw_set(MQTT_USER, MQTT_PASS)

        await client.asyncio_connect(MQTT_HOST)
        print("Let's go! >(^.^)<")
        await asyncio.sleep(5)
        await save_node_db()
        # client.loop_forever()

asyncio.run(main())
