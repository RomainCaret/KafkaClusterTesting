from kafka import KafkaConsumer
from kafka import KafkaProducer
import argparse
import time
import mlflow
import json
import time
from threading import Thread
import psutil
import platform
import cpuinfo
import numpy as np

def create_consumer_proc_data():
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


def consume_messages(brokerAddress, proc_data, name):
    brokerAddress = brokerAddress.split(" ")
    for i in range(len(brokerAddress)):
        brokerAddress[i] = brokerAddress[i] + ":9094"
    print("brokerAddress : ", brokerAddress)

    consumer = KafkaConsumer(
            bootstrap_servers=brokerAddress,
            api_version=(0, 10),)

    consumer.subscribe(['consumer-write'+name, 'topic-aiops'+name, 'consumer-end'+name])

    producer = KafkaProducer(
        bootstrap_servers=brokerAddress,
        api_version=(0, 10),
    )

    data_saved = False
    listTime = []
    producer.send("manager-consumer", json.dumps({"consumer-start": "start consumer"}).encode("utf-8"))

    for message in consumer:
        # Check the topic of the message
        if message.topic == "topic-aiops"+name:
            if not data_saved:
                data = json.loads(message.value.decode("utf-8"))
                data_saved = True
            diff = time.time() - json.loads(message.value.decode("utf-8"))["timestamp"]
            listTime.append(diff)
        elif message.topic == "consumer-write"+name:
            producer.send("debug", json.dumps({"consumer-write": "write data"}).encode("utf-8"))
            if len(listTime) > 0:
                # Write data in csv with the median of the list
                data_summarized = {}
                data_summarized["machine_kafka"] = data["machine_kafka"]
                data_summarized["batch_size"] = data["batch_size"]
                data_summarized["nb_messages"] = len(listTime)
                data_summarized["time"] = np.median(listTime)
                producer.send("manager-consumer", json.dumps(data_summarized).encode("utf-8"))
                listTime = []
                data_saved = False
            else:
                producer.send("debug", json.dumps({"error in consumer": "no data to write"}).encode("utf-8"))
        elif message.topic == "consumer-end"+name:
            print("End of consumer")
            break
        else :
            producer.send("debug", json.dumps({"error in consumer": "topic not found : " + message.topic}).encode("utf-8"))
    consumer.close()

def main():
    """Main function of the script."""

    # input and output arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--num_consumer", type=str, help="numero du consumer")
    parser.add_argument("--num_machine", type=str, help="numero de la machine")
    parser.add_argument("--brokerAddress", type=str, help="Broker address")

    args = parser.parse_args()
   
    name = args.num_machine + "-" + args.num_consumer

    # Start Logging
    mlflow.start_run()

    args = parser.parse_args()

    # Set the data of the consumer
    proc_data = create_consumer_proc_data()
    
    # create a new thread
    thread = Thread(target=consume_messages, args=(args.brokerAddress, proc_data, name))
    # start the thread
    thread.start()

    thread.join()
    
    # Stop Logging
    mlflow.end_run()

if __name__ == "__main__":
    main()
