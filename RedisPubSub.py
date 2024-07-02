import redis
import json
import asyncio
from typing import Callable, Coroutine

class RedisPubSubManager:
    _redis = None
    _pubsub = None
    _channels = set()

    @staticmethod
    def initialize(host: str = 'localhost', port: int = 6379, db: int = 10):
        RedisPubSubManager._redis = redis.Redis(host=host, port=port, db=db)
        RedisPubSubManager._pubsub = RedisPubSubManager._redis.pubsub()

    @staticmethod
    def subscribe(channel: str):
        if channel not in RedisPubSubManager._channels:
            RedisPubSubManager._pubsub.subscribe(channel)
            RedisPubSubManager._channels.add(channel)

    @staticmethod
    def unsubscribe(channel: str):
        if channel in RedisPubSubManager._channels:
            RedisPubSubManager._pubsub.unsubscribe(channel)
            RedisPubSubManager._channels.remove(channel)

    @staticmethod
    def publish(channel: str, message: str):
        RedisPubSubManager._redis.publish(channel, message)

    @staticmethod
    async def listen(callback: Callable[[str], Coroutine]):
        while True:
            message = RedisPubSubManager._pubsub.get_message(ignore_subscribe_messages=True)
            if message and 'data' in message:
                channel = message['channel'].decode('utf-8')
                data = message['data'].decode('utf-8')
                await callback(channel, data)
            await asyncio.sleep(0.01)