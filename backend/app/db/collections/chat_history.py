from pymongo.asynchronous.collection import AsyncCollection

from ..db import database


# A MongoDB collection is the equivalent of a SQL table. Each document stores
# one complete conversation and is keyed by the client-generated conversation id.
chat_history_collection: AsyncCollection = database["chat_history"]
