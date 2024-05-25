import redis
import json
import asyncio
from typing import Callable, Coroutine

class RedisPubSubManager:
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 10):
        self.redis = redis.Redis(host=host, port=port, db=db)
        self.pubsub = self.redis.pubsub()

    def subscribe(self, channel: str):
        self.pubsub.subscribe(channel)

    def unsubscribe(self, channel: str):
        self.pubsub.unsubscribe(channel)

    def publish(self, channel: str, message: str):
        self.redis.publish(channel, message)

    async def listen(self, callback: Callable[[str], Coroutine]):
        while True:
            message = self.pubsub.get_message(ignore_subscribe_messages=True)
            if message:
                await callback(message['data'].decode('utf-8'))
            await asyncio.sleep(0.01)
