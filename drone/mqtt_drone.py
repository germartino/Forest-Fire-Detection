from ast import Global
import asyncio
from contextlib import AsyncExitStack, asynccontextmanager
from email import message
from http import client
from random import randrange
from asyncio_mqtt import Client, MqttError
from mavsdk import System
from mavsdk import mission
from mavsdk.mission import (MissionItem, MissionPlan)
import json
import droneGoTo

mqttHostname  = "192.168.1.184"
mqttPort = 1883
mqttUsername = "guest"
mqttPassword = "guest"

async def run():

    drone = System()
    await drone.connect(system_address="udp://:14540")

    print("Waiting for drone to connect...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print(f"-- Connected to drone!")
            async with Client(hostname = mqttHostname, port = mqttPort,username = mqttUsername, password = mqttPassword) as client:
                await client.publish("drone", "Connected", qos=1)
                break

    # We 💛 context managers. Let's create a stack to help
    # us manage them.
    async with AsyncExitStack() as stack:
        # Keep track of the asyncio tasks that we create, so that
        # we can cancel them on exit
        tasks = set()
        stack.push_async_callback(cancel_tasks, tasks)

        # Connect to the MQTT broker
        client = Client(hostname = mqttHostname, port = mqttPort,username = mqttUsername, password = mqttPassword)
        await stack.enter_async_context(client)

        # You can create any number of topic filters
        topic_filters = (
            "forest/iot/alert",
            # 👉 Try to add more filters!
        )
        for topic_filter in topic_filters:
            # Log all messages that matches the filter
            manager = client.filtered_messages(topic_filter)
            messages = await stack.enter_async_context(manager)
            task = asyncio.create_task(log_messages(drone, messages, topic_filter))
            tasks.add(task)

        # # Messages that doesn't match a filter will get logged here
        # messages = await stack.enter_async_context(client.unfiltered_messages())
        # task = asyncio.create_task(log_messages(drone, messages, topic_filter))
        # tasks.add(task)

        # Subscribe to topic(s)
        # 🤔 Note that we subscribe *after* starting the message
        # loggers. Otherwise, we may miss retained messages.

        await client.subscribe("forest/iot/alert")
        # await client.subscribe("forest/iot/sensors")

        # Publish a random value to each of these topics
        topics = (
            "battery",
            "gps",
            "inAir",
            "health",
            "position",
            "forest/iot/alert"
            # 👉 Try to add more topics!
        )

        task = asyncio.create_task(post_to_topics(client, topics, drone))
        tasks.add(task)

        # Wait for everything to complete (or fail due to, e.g., network
        # errors)
        await asyncio.gather(*tasks)

async def post_to_topics(client, topics, drone):
    global isForestOnFire
    isForestOnFire = False
    while True:        
        for topic in topics:
            if topic == "battery":
                async for battery in drone.telemetry.battery():
                    droneBattery= {
                        "battery_info": str(battery.remaining_percent),
                        "battery_id": str(battery.id),
                        "battery_voltage_v": str(battery.voltage_v)
                    }
                    droneBatteryJSON= json.dumps(droneBattery)
                    print(f'[topic="{topic}"] Publishing message={str(battery.remaining_percent)} and {str(battery.id)} and {str(battery.voltage_v)}')
                    break
                await client.publish(topic, droneBatteryJSON, qos=1)
            elif topic == "gps":
                async for gps in drone.telemetry.gps_info():
                    droneGPS= {
                        "gps_info": str(gps.num_satellites),
                        "fix_type": str(gps.fix_type),
                    }
                    droneGPSJSON= json.dumps(droneGPS)
                    print(f'[topic="{topic}"] Publishing message={str(gps.num_satellites)} and {str(gps.fix_type)}')
                    break
                await client.publish(topic, droneGPSJSON, qos=1)
            elif topic == "inAir":
                async for inAir in drone.telemetry.in_air():
                    inAir_info = str(inAir)
                    print(f'[topic="{topic}"] Publishing message={inAir_info}')
                    break
                await client.publish(topic, inAir_info, qos=1)
            elif topic == "position":
                async for position in drone.telemetry.position():
                    dronePosition= {
                        "position_latitude": str(position.latitude_deg),
                        "position_longitude": str(position.longitude_deg),
                        "position_absolute_alt": str(position.absolute_altitude_m),
                        "position_relative_alt": str(position.relative_altitude_m)
                    }
                    dronePositionJSON= json.dumps(dronePosition)
                    print(f'[topic="{topic}"] Publishing message={str(position.latitude_deg)} and {str(position.longitude_deg)} \
                        and {str(position.absolute_altitude_m)} and {str(position.relative_altitude_m)}')
                    break
                await client.publish(topic, dronePositionJSON, qos=1)
            elif topic == "health":
                async for health in drone.telemetry.health():
                    droneHealth= {
                        "health_gc": str(health.is_gyrometer_calibration_ok),
                        "health_ac": str(health.is_accelerometer_calibration_ok),
                        "health_mc": str(health.is_magnetometer_calibration_ok),
                        "health_lp": str(health.is_local_position_ok),
                        "health_gp": str(health.is_global_position_ok),
                        "health_hp": str(health.is_home_position_ok),
                        "health_ia": str(health.is_armable)
                    }
                    droneHealthJSON= json.dumps(droneHealth)
                    print(f'[topic="{topic}"] Publishing message={str(health.is_gyrometer_calibration_ok)} and {str(health.is_accelerometer_calibration_ok)} and {str(health.is_magnetometer_calibration_ok)} and {str(health.is_local_position_ok)} and {str(health.is_global_position_ok)} and {str(health.is_home_position_ok)} and {str(health.is_armable)}')
                    break
                await client.publish(topic, droneHealthJSON, qos=1)
            elif (topic == "forest/iot/alert" and isForestOnFire == True) :
                isMissionDone = await drone.mission.is_mission_finished()
                if isMissionDone:
                    message= {"sensor": "FIRE_OFF", "position": [47.397606,8.54306]}
                    messageJson= json.dumps(message)
                    print(f'[topic="{topic}"] Publishing message= FIRE_OFF')
                    await client.publish(topic, messageJson, qos=1)
                    isForestOnFire = False

            # await asyncio.sleep(1)

async def log_messages(drone, messages, topic_filter):
    async for message in messages:
        try:
            messageJson = json.loads(message.payload.decode())
            if messageJson["sensor"] == "FIRE_ON" and topic_filter == "forest/iot/alert":
                global isForestOnFire
                isForestOnFire = True
                latitude = messageJson["position"][0]
                longitude = messageJson["position"][1]
                await droneGoTo.droneGoTo(drone, latitude, longitude)
            print(f'[topic="{topic_filter}"] Publishing message= FIRE_ON')
        except:
            continue
        # 🤔 Note that we assume that the message paylod is an
        # UTF8-encoded string (hence the `bytes.decode` call).

async def cancel_tasks(tasks):
    for task in tasks:
        if task.done():
            continue
        try:
            task.cancel()
            await task
        except asyncio.CancelledError:
            pass

async def main():
    # Run the main indefinitely. Reconnect automatically
    # if the connection is lost.
    reconnect_interval = 1  # [seconds]
    while True:
        try:
            await run()
        except MqttError as error:
            print(f'Error "{error}". Reconnecting in {reconnect_interval} seconds.')
        finally:
            await asyncio.sleep(reconnect_interval)

asyncio.run(main())

