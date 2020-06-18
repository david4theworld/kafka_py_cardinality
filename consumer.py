import time
import json
from kafka import KafkaConsumer
from datetime import datetime
from pdsa.cardinality.linear_counter import LinearCounter

def calculate_thoughput(timing, n_messages=1000000, msg_size=1500):
    print("Processed {0} messsages in {1:.2f} seconds".format(n_messages, timing))
    print("{0:.2f} MB/s".format((msg_size * n_messages) / timing / (1024*1024)))
    print("{0:.2f} Msgs/s".format(n_messages / timing))

def print_minute_stats(prev_window, unique_users):
    l_datetime = datetime.utcfromtimestamp(prev_window*60).strftime('%Y-%m-%d %H:%M:%S')
    print('Date: {}  Unique Users: {}'.format(l_datetime, unique_users))

def utf8len(s):
    return len(str(s).encode('utf-8'))

if __name__ == "__main__":
    consumer = KafkaConsumer(
        'sunday',
        bootstrap_servers=['localhost:9092'],
        auto_offset_reset='earliest',
        value_deserializer=lambda x: json.loads(x.decode('utf-8')))

    total_bytes = 0
    consumer_start = time.time()
    msg_consumed_max = 1000000
    msg_consumed_count = 0
    # one minute window
    previous_window = 0 
    users_bitmap = LinearCounter(60000) 

    for message in consumer:
        json_msg = message.value
        total_bytes = total_bytes + utf8len(json_msg)
        ts = json_msg['ts']
        uid = json_msg['uid']
        # convert ts(seconds) to minutes - using it as the 'minute window'
        current_window = int(ts / 60)

        if previous_window != current_window:
            # current minute window changed
            # print for the previous window the unique users count
            if previous_window > 0:
                print_minute_stats(previous_window, users_bitmap.count())
                
            previous_window = current_window
            users_bitmap = LinearCounter(60000)  
        users_bitmap.add(uid)

        # stop parser after 1000000 mesages
        msg_consumed_count = msg_consumed_count + 1
        if msg_consumed_count + 1 > msg_consumed_max:
            break 

    print_minute_stats(previous_window, users_bitmap.count())
    consumer_timing = time.time() - consumer_start
    consumer.close()
    print('Consumer timing (1000000 messages): {0:.2f}'.format(consumer_timing))
    print('Average message size: {0:.2f}'.format(total_bytes / msg_consumed_max))
    calculate_thoughput(consumer_timing)