import os

BOT_TOKEN = os.environ.get('QB_BOT_TOKEN', '')

if not BOT_TOKEN:
    raise RuntimeError("Please provide a value for QB_BOT_TOKEN env")
