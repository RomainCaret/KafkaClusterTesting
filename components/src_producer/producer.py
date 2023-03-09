import os
import argparse
import time
import mlflow
import datetime, warnings, scipy
from pathlib import Path
import psutil
import platform
from datetime import datetime
import cpuinfo
import socket
import uuid
import re
from kafka import KafkaProducer
from kafka import KafkaConsumer
import json
import time
import random
import threading

# Create random data of characters
amount_of_ko = 10
load_message = ''.join(random.choice('0123456789ABCDEF') for i in range(amount_of_ko*1024))

# Create the data of the producer proc
def create_producer_proc_data():
    proc = {}
    uname = platform.uname()
    proc['system'] = uname.system
    proc['processor'] = uname.processor
    proc['cpu_brand'] = cpuinfo.get_cpu_info()['brand_raw']
    proc['cpu_hz'] = cpuinfo.get_cpu_info()['hz_actual_friendly']
    proc['cpu_cores'] = psutil.cpu_count(logical=False)
    proc['cpu_cores_total'] = psutil.cpu_count(logical=True)
    svmem = psutil.virtual_memory()
    proc['ram_total'] = svmem.total
    return proc

# Create the data to send
def create_data_json(proc_data,machineKafka, flow, batch_size):
    data = {}
    # put 5 ko of data
    data['data'] = load_message
    data['proc_prod'] = proc_data
    data['machine_kafka'] = machineKafka
    data['batch_size'] = batch_size
    data['timestamp'] = time.time()
    return data

def print_debug(message, brokerAddress):
    producer = KafkaProducer(
			bootstrap_servers=brokerAddress,
			api_version=(0, 10, 1),
			acks=1,)
    data = {"message": message}
    data_encode = json.dumps(data).encode('utf-8')
    producer.send("debug", data_encode)
    producer.flush()
    producer.close()

# Send data
def send_data(brokerAddress, num_messages, topic, proc_data, machineKafka, batch_size):
    
    
    producer = KafkaProducer(
            bootstrap_servers=brokerAddress,
            api_version=(0, 10, 1),
            acks=1,)
    data = create_data_json(proc_data, machineKafka, num_messages, batch_size)
    data_encode = json.dumps(data).encode('utf-8')
    
    for _ in range(num_messages):
        producer.send(topic, data_encode)

    

    # Flush and close the producer to ensure all messages are sent
    producer.flush()
    producer.close()

# Send data secured
def send_data_secured(brokerAddress, num_messages, topic):

    producer = KafkaProducer(
            bootstrap_servers=brokerAddress,
            api_version=(0, 10, 1),
            acks=1,)
    data = {}
    data_encode = json.dumps(data).encode('utf-8')

    for _ in range(num_messages):
        producer.send(topic, data_encode)
    
    print_debug("end topic: " + topic, brokerAddress)
    # Flush and close the producer to ensure all messages are sent
    producer.flush()
    producer.close()

def main():
    """Main function of the script."""

    # input and output arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--num_producer", type=str, help="numero du producer")
    parser.add_argument("--num_machine", type=str, help="numero de la machine")
    parser.add_argument("--brokerAddress", type=str, help="Broker address")
    parser.add_argument("--machineKafka", type=str, help="Machine Kafka")
    
    args = parser.parse_args()

    name = args.num_machine + "-" + args.num_producer
    print("name: ", name)
    
    # Set the data of the producer
    proc_data = create_producer_proc_data()

    brokerAddress = args.brokerAddress.split(" ")
    for i in range(len(brokerAddress)):
        brokerAddress[i] = brokerAddress[i] + ":9094"

    consumer = KafkaConsumer(
            bootstrap_servers=brokerAddress,
            api_version=(0, 10),)

    consumer.subscribe(["manager-producer"])
    
    # Initialize the variables
    stop = False
    flow = 0
    batch_size = 0
    amount_of_time = 0

    while True:
        for message in consumer:
            if json.loads(message.value.decode("utf-8"))["stop"] == True:
                stop = True
                break
            diff = time.time() - json.loads(message.value.decode("utf-8"))["timestamp"]
            # If the message is older than 10 minutes, we ignore it
            if diff < 600:
                print_debug("Let s produce: " + str(json.loads(message.value.decode("utf-8"))), brokerAddress)
                flow = json.loads(message.value.decode("utf-8"))["flow"]
                batch_size = json.loads(message.value.decode("utf-8"))["batch_size"]
                amount_of_time = json.loads(message.value.decode("utf-8"))["amount_of_time"]
                break
        
        # Start the producer with the flow and the batch size given by the manager for the next amount of time
        if stop:
            break
        time_start = time.time()
        while time.time() - time_start < amount_of_time:
            threading.Thread(target=send_data, args=(brokerAddress, int(flow/2), "topic-aiops"+name, proc_data, args.machineKafka, batch_size)).start()
            # sleep for 0.5 seconds
            time.sleep(0.5)
        # Send the end of the flow
        time.sleep(1)
        send_data_secured(brokerAddress, 1, "consumer-write"+name)
        time.sleep(10)

    send_data_secured(brokerAddress, 1, "consumer-end"+name)
    time.sleep(20)

if __name__ == "__main__":
    main()
