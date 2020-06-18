# Apache Kafka - Cardinality Challenge
The goal of the task is to prototype a solution that will process ingested test data and output the number of unique 
users per minute. 


# Table of Contents
1. [Task description](#task-description)
2. [Prerequisites](#prerequisites) 
3. [Thought process](#thought-process)
4. [Environment setup](#environment-setup)
5. [Usage](#usage) 
6. [Key points](#key-points)
7. [Consumer code](#consumer-code)

## Task description
The initial prototype should provide unique user IDs per minute, from the ingested data described bellow:  
* The test data consists of (Log)-Frames of JSON data;
  * `ts` - timestamp (unixtime);
  * `uid` - user id;  
* Display results as soon as possible;
\
\
The following items should be provided: 
* `READme` document explaining the thought process; 
  * instructions to build/run; 
  * reasoning behind the key points;
  * metrics.
## Prerequisites 
The following should be configured before running the code: 
* JDK/JRE 
* Python 3.x 
  * Use `pip install` to install the following: 
    * [`kafka-python`](https://kafka-python.readthedocs.io/en/master/index.html)
    * [`cython`](https://cython.org/)
    * [`pdsa`](https://pypi.org/project/pdsa/)
## Thought process
Upon inspecting the test data, the following can be observed: 
* 1000000 records, averaging ~1500 bytes per line; 
* Just the `uid`, as the point of interest, has 19 characters, ~150 bits; 

Therefore the first issue is memory, and resolving the cardinality question will cost a lot of it, 
so [back to reading](http://highscalability.com/blog/2012/4/5/big-data-counting-how-to-count-a-billion-distinct-objects-us.html);   
Looking at the comparison between `HashSet`, `Linear` and `HyperLogLog`, I decided to use bitmaps and look up a way to 
implement it in Python - hence the [`pdsa`](https://pypi.org/project/pdsa/) and the LinearCounter. \
Having a way to quickly pass the test data to a console producer and test a python consumer, I just decided to leave 
the defaults from the official Kafka documentation, consume and process the messages, doing an stdout in a 
human-readable format for easier testing and debugging.

## Environment setup
Abiding by the prerequisites, proceed to download: 
* [Kafka](https://kafka.apache.org/quickstart) 
* [Test data](https://drive.google.com/uc?export=download&id=1-Xp6acOXJLgRzJDeI2-59UiivyJyQJ7u) \
The folder structure largely depends on the OS used, but the main concept is 
the same. Under Linux or MacOS, the `.sh` commands are run from `bin/*` while under Windows the `.bat` scripts are under 
`bin\windows\*`. 
## Usage
>Note: The following paths might defer depending on the project structure, so always modify your paths accordingly.

Navigate to Kafka root and in the following order, run: 
1. Zookeper server:\
`bin/zookeeper-server-start.sh config/zookeeper.properties` 
2. Kafka server:\
`bin/kafka-server-start.sh config/server.properties`
3. Topic creation:\
`bin/kafka-topics.sh --create --bootstrap-server localhost:9092 --replication-factor 1 --partitions 1 --topic sunday`
    * Optionally confirm the creation by running `bin/kafka-topics.sh --list --bootstrap-server localhost:9092` 
4. The easiest way to pass the the test data to a console producer is:\
`bin\kafka-console-producer.sh --broker-list localhost:9092 --topic sunday < stream.jsonl`
5. For the consumer, run the provided `.py` sript: \
`python consumer.py`  
   * example of an stdout: 
   ```bash
    Date: 2016-07-11 13:39:00  Unique Users: 16118
    Date: 2016-07-11 13:40:00  Unique Users: 41227
    Date: 2016-07-11 13:41:00  Unique Users: 47192
    Date: 2016-07-11 13:42:00  Unique Users: 49596
    Date: 2016-07-11 13:43:00  Unique Users: 47770
    Date: 2016-07-11 13:44:00  Unique Users: 40595
    Date: 2016-07-11 13:45:00  Unique Users: 43070
    Date: 2016-07-11 13:46:00  Unique Users: 47188
    Date: 2016-07-11 13:47:00  Unique Users: 48479
    Date: 2016-07-11 13:48:00  Unique Users: 48104
    Date: 2016-07-11 13:49:00  Unique Users: 42076
    Date: 2016-07-11 13:50:00  Unique Users: 45125
    Date: 2016-07-11 13:51:00  Unique Users: 43385
    Date: 2016-07-11 13:52:00  Unique Users: 48504
    Date: 2016-07-11 13:53:00  Unique Users: 42668
    Date: 2016-07-11 13:54:00  Unique Users: 52021
    Date: 2016-07-11 13:55:00  Unique Users: 45527
    Date: 2016-07-11 13:56:00  Unique Users: 138
    Average message size: 1630.46
    Processed 1000000 messsages in 67.43 seconds
    21.21 MB/s
    14829.10 Msgs/s
    
    Process finished with exit code 0
   ```

## Key points

* Following the task's direction that the results should be delivered ASAP, I simply checked if all the messages for a 
given timestamp were processed and then print the result. Didn't even have time to think about production scenario of 
higher latency, possible bitflips, unordered events, app crashes and other edge cases. 
* For basic benchmarking I followed [this old article](http://activisiongamescience.github.io/2016/06/15/Kafka-Client-Benchmarking/);
* Next steps - forwarding the result set to a new kafka topic, accessing historical data, using Pandas and MongoDB to create a proper robust solution that could be scaled;

## Consumer code


```python
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
        # convert ts(seconds) to minutes - use it as the 'minute window'
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
```


