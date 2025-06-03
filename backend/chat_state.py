import redis, json

r = redis.Redis(host="localhost", decode_responses=True)

def push_msg(sid: str, role: str, content: str):
    """Append a message to the chat history for a session."""
    r.rpush(f"hist:{sid}", json.dumps({"role": role, "content": content}))


def history(sid: str):
    """Return the chat history list for a session (empty list if none)."""
    return [json.loads(x) for x in r.lrange(f"hist:{sid}", 0, -1)]
