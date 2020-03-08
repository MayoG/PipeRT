import pytest
from pipert.core.message_handlers import RedisHandler
from urllib.parse import urlparse

key = "Test"


@pytest.fixture(scope="function")
def redis_handler():
    redis_handler = RedisHandler(urlparse("redis://127.0.0.1:6379"))
    yield redis_handler
    redis_handler.conn.delete(key)
    redis_handler.close()


def test_redis_send(redis_handler):
    redis_handler.send(key, "A")
    msg = redis_handler.receive(key)
    assert msg.decode() == "A"


def test_receive_does_not_change_last_message_id_stay_none_when_no_msg_received(redis_handler):
    msg = redis_handler.receive(key)
    assert msg is None
    assert redis_handler.last_msg_id is None


# tests if the method read the last message if it didn't read before
def test_redis_read_next_msg_reads_last_message(redis_handler):
    redis_handler.send(key, "AAA")
    redis_handler.send(key, "BBB")
    msg = redis_handler.read_next_msg(key)

    assert msg.decode() == "BBB"


def test_redis_read_next_msg(redis_handler):
    redis_handler.send(key, "AAA")
    assert redis_handler.read_next_msg(key).decode() == "AAA"
    redis_handler.send(key, "BBB")
    redis_handler.send(key, "CCC")
    assert redis_handler.read_next_msg(key).decode() == "BBB"


def test_redis_read_next_msg_cannot_read_the_same_message(redis_handler):
    redis_handler.send(key, "AAA")
    assert redis_handler.read_next_msg(key).decode() == "AAA"

    assert redis_handler.read_next_msg(key) is None


def test_redis_read_most_recent_message(redis_handler):
    redis_handler.send(key, "AAA")
    redis_handler.send(key, "BBB")
    assert redis_handler.read_most_recent_msg(key).decode() == "BBB"


def test_redis_read_most_recent_message_cannot_read_the_same_message(redis_handler):
    redis_handler.send(key, "AAA")
    assert redis_handler.read_most_recent_msg(key).decode() == "AAA"
    assert redis_handler.read_most_recent_msg(key) is None
