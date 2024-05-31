import redis

class RedisCache:

    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 8):
        """
        Initialize a connection to the Redis server.

        :param host: The host of the Redis server.
        :param port: The port of the Redis server.
        :param db: The database index to use on the Redis server.
        """
        self.redis = redis.Redis(host=host, port=port, db=db)

    def set(self, key: str, value: str, expire: int = 259200):
        """
        Set a value in the Redis cache.

        :param key: The key under which the value is stored.
        :param value: The value to store.
        :param expire: Optional expiration time in seconds.
        """
        print(f"Setting key: {key} with value: {value}")
        self.redis.set(key, value, ex=expire)

    def get(self, key: str) -> str:
        """
        Get a value from the Redis cache.

        :param key: The key of the value to retrieve.
        :return: The value stored under the key, or None if the key does not exist.
        """
        value = self.redis.get(key)
        return value.decode('utf-8') if value else None

    def delete(self, key: str):
        """
        Delete a key-value pair from the Redis cache.

        :param key: The key of the value to delete.
        """
        self.redis.delete(key)

    def exists(self, key: str) -> bool:
        """
        Check if a key exists in the Redis cache.

        :param key: The key to check for existence.
        :return: True if the key exists, False otherwise.
        """
        return self.redis.exists(key) == 1

    def expire(self, key: str, time: int):
        """
        Set an expiration time for a key.

        :param key: The key to set the expiration time for.
        :param time: Expiration time in seconds.
        """
        self.redis.expire(key, time)

    def flushdb(self):
        """
        Remove all data from the current database.
        """
        self.redis.flushdb()