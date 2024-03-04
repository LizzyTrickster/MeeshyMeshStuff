#!/usr/bin/env python3
# Copyright Lizzy Trickster (Lizzy Green)
import os.path
import time
from datetime import datetime as dt

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
except FileNotFoundError:
    pass

async def on_connect(client: AsyncioPahoClient, userdata: Any, flags: dict[str, Any], result: int):
    await client.asyncio_subscribe("MESHY/2/json/#")


async def on_message(client, userdata, msg):
    # data = json.loads(msg.payload)
    # print(msg.payload)
    data = Box.from_json(msg.payload.decode("utf-8"), frozen_box=True)
    if data.type == "sendtext":
        return

    sender = data['from']
    print(data)
    print(data.type, hex(data.get('to', 0)), hex(sender))
    if sender not in NODES:
        NODES[sender] = dict(as_hex=hex(sender))

    NODES[sender]._last_heard = dict(ts=dt.now(), type=data.type)
    NODES[sender]._stats[data.type or "_"].latest = dt.now()
    NODES[sender]._stats[data.type or "_"].count = NODES[sender]._stats[data.type].get("count", 0) + 1

    match data.type:
        case "nodeinfo":
            NODES[sender].hardware = data.payload.hardware
            NODES[sender].shortname = data.payload.shortname
            NODES[sender].longname = data.payload.longname
        case "position":
            NODES[sender].position = dict(
                lat=(data.payload.latitude_i * 1e7) / 100000000000000,
                lon=(data.payload.longitude_i * 1e7) / 100000000000000,
                alt=data.payload.altitude,
                tim=data.payload.time)
        case "telemetry":
            NODES[sender].telemetry = dict(
                tx_util=data.payload.air_util_tx,
                batt=data.payload.battery_level,
                chan_util=data.payload.channel_utilization,
                voltage=data.payload.voltage)

    print(data.get("sender", "Who knows?"), hex(data.get("from")))



    # Update latest entries
    NODES[sender].latest_rssi = data.get("rssi", 0)
    NODES[sender].latest_snr = data.get("snr", 0)

    if data.type == 'text' and data.payload.text == 'can you hear me LiZB?':
        await send_message(client, f"Hello {hex(sender)}!")


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
        NODES._last_write = time.time()
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
