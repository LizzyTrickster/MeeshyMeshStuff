#!/usr/bin/env python3
# Copyright Lizzy Trickster (Lizzy Green)
import os.path

import paho.mqtt.client as mqtt
from asyncio_paho.client import AsyncioPahoClient
import asyncio, json, aiofiles
from typing import Any
from box import Box

base_send = {"from": 56525366, "type": "sendtext"}

NODES = Box()

try:
    if os.path.exists("nodedb.yaml"):
        with open("nodedb.yaml", "r") as f:
            NODES = Box.from_yaml(f.read(), default_box=True)
    elif os.path.exists("nodedb.json"):
        with open("nodedb.json", "r") as f:
            NODES = Box.from_json(f.read())
except FileNotFoundError:
    pass

async def on_connect(client: AsyncioPahoClient, userdata: Any, flags: dict[str, Any], result: int):
    await client.asyncio_subscribe("MESHY/2/json/#")


async def on_message(client, userdata, msg):
    data = json.loads(msg.payload)
    # data = Box.from_json(msg.payload, frozen_box=True)
    if data['type'] == "sendtext":
        return

    print(data)
    print(data['type'], hex(data.get('to', 0)), hex(data['from']))
    if data['from'] not in NODES:
        NODES[data['from']] = dict(as_hex=hex(data['from']))
    if data['type'] == "nodeinfo":
        NODES[data['from']]["hardware"] = data['payload']['hardware']
        NODES[data['from']]['shortname'] = data['payload']['shortname']
        NODES[data['from']]['longname'] = data['payload']['longname']
    elif data['type'] == "position":
        NODES[data['from']]['position'] = dict(
            lat=data['payload']['latitude_i'],
            lon=data['payload']['longitude_i'],
            alt=data['payload']['altitude'],
            tim=data['payload']['time'] )

    print(data.get("sender", "Who knows?"), hex(data.get("from")))



    # Update latest entries
    NODES[data['from']]['latest_rssi'] = data.get("rssi", 0)
    NODES[data['from']]['lates_snr'] = data.get("snr", 0)

    if data['type'] == 'text' and data['payload']['text'] == 'can you hear me LiZB?':
        await send_message(client, f"Hello {hex(data['from'])}!")


async def send_message(c:AsyncioPahoClient, message:str):
    to_send = dict(**base_send, payload=message, channel=2)

    await c.asyncio_publish("MESHY/2/json/mqtt", json.dumps(to_send))


async def on_subscribe(client, userdata, mid, reason_code_list, properties):
    # Since we subscribed only for a single channel, reason_code_list contains
    # a single entry
    if reason_code_list[0].is_failure:
        print(f"Broker rejected you subscription: {reason_code_list[0]}")
    else:
        print(f"Broker granted the following QoS: {reason_code_list[0].value}")


async def on_unsubscribe(client, userdata, mid, reason_code_list, properties):
    # Be careful, the reason_code_list is only present in MQTTv5.
    # In MQTTv3 it will always be empty
    if len(reason_code_list) == 0 or not reason_code_list[0].is_failure:
        print("unsubscribe succeeded (if SUBACK is received in MQTTv3 it success)")
    else:
        print(f"Broker replied with failure: {reason_code_list[0]}")


async def save_node_db():
    while True:
        async with aiofiles.open("nodedb.yaml", "w") as f:
            await f.write(NODES.to_yaml())
            # await f.write(json.dumps(NODES, indent=True))
        # print("Donna Noble has left the library, Donna Noble has been saved")
        await asyncio.sleep(5)
    pass


async def main():
    # client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    async with AsyncioPahoClient() as client:
        client.asyncio_listeners.add_on_connect(on_connect)
        client.asyncio_listeners.add_on_message(on_message)
        # client.asyncio_listeners.add_on_subscribe(on_subscribe)
        # client.asyncio_listeners.add_on_unsubscribe(on_unsubscribe)

        client.username_pw_set("mqtt", "mqtt")

        # client.connect("192.168.0.17")
        await client.asyncio_connect("127.0.0.1")
        print("beep?")
        await asyncio.sleep(5)
        await save_node_db()
        # client.loop_forever()

asyncio.run(main())
