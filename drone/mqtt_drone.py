# from ast import Global
import asyncio
from contextlib import AsyncExitStack, asynccontextmanager
# from email import message
# from http import client
# from random import randrange
# from turtle import clear
from asyncio_mqtt import Client, MqttError
from mavsdk import System
# from mavsdk import mission
from mavsdk.mission import (MissionItem, MissionPlan)
# from mavsdk.offboard import (OffboardError, VelocityBodyYawspeed)
import json

async def run():

    drone = System()
    await drone.connect(system_address="udp://:14540")

    print("Waiting for drone to connect...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            isConnected = "Connected"
            print(f"-- Connected to drone!")
            async with Client(hostname = mqttHostname, port = mqttPort,username = mqttUsername, password = mqttPassword) as client:
                await client.publish("drone/sensors", isConnected, qos=1)
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

        # Messages that doesn't match a filter will get logged here
        messages = await stack.enter_async_context(client.unfiltered_messages())
        task = asyncio.create_task(log_messages(drone, messages, "[unfiltered] {}"))
        tasks.add(task)

        # Subscribe to topic(s)
        # 🤔 Note that we subscribe *after* starting the message
        # loggers. Otherwise, we may miss retained messages.

        await client.subscribe("forest/iot/alert")


        # Publish a random value to each of these topics
        topics = (
            "drone/sensors",
            "forest/iot/alert",
            "forest/drone/release",
            # 👉 Try to add more topics!
        )

        task = asyncio.create_task(post_to_topics(client, topics, drone))
        tasks.add(task)

        # Wait for everything to complete (or fail due to, e.g., network
        # errors)
        await asyncio.gather(*tasks)

async def post_to_topics(client, topics, drone):
    # global isForestOnFire
    # isForestOnFire = False
    droneDict = {}
    while True:        
        for topic in topics:
            if topic == "drone/sensors":
                async for state in drone.core.connection_state():
                    droneDict['drone'] = str(state.is_connected)
                    print(f'[topic = "{topic}" -> drone] Publishing message = {str(state.is_connected)}')
                    break
                async for battery in drone.telemetry.battery():
                    droneDict['battery_info'] = str(battery.remaining_percent)
                    droneDict['battery_id'] = str(battery.id)
                    droneDict['battery_voltage_v'] = str(battery.voltage_v)
                    print(f'[topic = "{topic}" -> battery] Publishing message = {str(battery.remaining_percent)} | {str(battery.id)} | {str(battery.voltage_v)}')
                    break
                async for gps in drone.telemetry.gps_info():
                    droneDict['gps_info'] = str(gps.num_satellites)
                    droneDict['fix_type'] = str(gps.fix_type)
                    print(f'[topic = "{topic}" -> gps] Publishing message = {str(gps.num_satellites)} | {str(gps.fix_type)}')
                    break
                async for inAir in drone.telemetry.in_air():
                    droneDict['inAir'] = str(inAir)
                    print(f'[topic = "{topic}" -> inAir] Publishing message = {inAir}')
                    break
                async for position in drone.telemetry.position():
                    droneDict['position_latitude'] = str(position.latitude_deg)
                    droneDict['position_longitude'] = str(position.longitude_deg)
                    droneDict['position_absolute_alt'] = str(position.absolute_altitude_m)
                    droneDict['position_relative_alt'] = str(position.relative_altitude_m)
                    print(f'[topic = "{topic}" -> position] Publishing message = {str(position.latitude_deg)} | {str(position.longitude_deg)} | {str(position.absolute_altitude_m)} | {str(position.relative_altitude_m)}')
                    break
                async for health in drone.telemetry.health():
                    droneDict['health_gc'] = str(health.is_gyrometer_calibration_ok)
                    droneDict['health_ac'] = str(health.is_accelerometer_calibration_ok)
                    droneDict['health_mc'] = str(health.is_magnetometer_calibration_ok)
                    droneDict['health_lp'] = str(health.is_local_position_ok)
                    droneDict['health_gp'] = str(health.is_global_position_ok)
                    droneDict['health_hp'] = str(health.is_home_position_ok)
                    droneDict['health_ia'] = str(health.is_armable)
                    print(f'[topic = "{topic}" -> health] Publishing message = {str(health.is_gyrometer_calibration_ok)} | {str(health.is_accelerometer_calibration_ok)} | {str(health.is_magnetometer_calibration_ok)} | {str(health.is_local_position_ok)} | {str(health.is_global_position_ok)} | {str(health.is_home_position_ok)} | {str(health.is_armable)}')                    
                    break
                droneJSON= json.dumps(droneDict)
                await client.publish(topic, droneJSON, qos=1)
            # elif (topic == "forest/iot/alert" and isForestOnFire == True) :
            #     isMissionDone = await drone.mission.is_mission_finished()
            #     if isMissionDone:
            #         message = {"sensor": "FIRE_OFF", "position": [47.397606,8.54306]}
            #         messageJson= json.dumps(message)
            #         print(f'[topic = "{topic}"] Publishing message = FIRE_OFF')
            #         await client.publish(topic, messageJson, qos=1)
            #         isForestOnFire = False

            # await asyncio.sleep(1)

async def log_messages(drone, messages, topic_filter):
    async for message in messages:
        print(f'[topic="{topic_filter}"] {message.payload.decode()}')
        try:
            messageJson = json.loads(message.payload.decode())
            if (messageJson["sensor"] == "FIRE_ON" and topic_filter == "forest/iot/alert"):
                print(f'[topic="{topic_filter}"] Publishing message = FIRE_ON')
                latitude = messageJson["position"][0]
                longitude = messageJson["position"][1]
                await goto(drone, latitude, longitude)
        except:
             continue
        # 🤔 Note that we assume that the message paylod is an
        # UTF8-encoded string (hence the `bytes.decode` call).

async def goto(drone, latitude, longitude):

    drone_mission_progress_task = asyncio.ensure_future(drone_mission_progress(drone))

    mission_items = []
    mission_items.append(MissionItem(latitude,
                                     longitude,
                                     25,
                                     10,
                                     True,
                                     float('nan'),
                                     float('nan'),
                                     MissionItem.CameraAction.NONE,
                                     float('nan'),
                                     float('nan'),
                                     float('nan'),
                                     float('nan'),
                                     float('nan')))

    mission_plan = MissionPlan(mission_items)

    await drone.mission.set_return_to_launch_after_mission(True)

    print("-- Uploading mission")
    await drone.mission.upload_mission(mission_plan)

    print("-- Arming")
    await drone.action.arm()

    print("-- Starting mission")
    await drone.mission.start_mission()

    await drone_mission_progress_task


async def drone_mission_progress(drone):
    async for mission_progress in drone.mission.mission_progress():
        if mission_progress.current == 1:
            print(f"[Mission progress: " f"{mission_progress.current}/" f"{mission_progress.total}]")
            message = {"sensor":"FIRE_BALL_RELEASED","position":[47.397606,8.54306]}
            messageJson= json.dumps(message)
            print(f'[topic = "forest/drone/release"] Publishing message = Fire Ball relesed!')
            async with Client(hostname = mqttHostname, port = mqttPort,username = mqttUsername, password = mqttPassword) as client:
                await client.publish("forest/drone/release", messageJson, qos=1)
                break

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

try:
    mqtt_fp = open('mqtt_config.json')
    mqtt_config = json.load(mqtt_fp)
    mqttHostname  = mqtt_config['ip']
    mqttPort = mqtt_config['port']
    mqttUsername = mqtt_config['username']
    mqttPassword = mqtt_config['password']
except FileNotFoundError:
    print("MQTT configuration file not fourd.")

asyncio.run(main())

