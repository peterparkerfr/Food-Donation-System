
import streamlit as st
import mysql.connector
from pymongo import MongoClient


def get_mysql_connection():
    config = st.secrets["mysql"]
    return mysql.connector.connect(
        host=config["host"],
        port=int(config["port"]),
        user=config["user"],
        password=config["password"],
        database=config["database"]
    )


def get_mongo_collection():
    config = st.secrets.get("mongo", {})
    uri = config.get("uri", "")

    if not uri:
        return None

    client = MongoClient(uri, serverSelectionTimeoutMS=3000)
    client.admin.command("ping")
    return client["food_donation_db"]["activity_logs"]


def log_activity(action, details):
    try:
        collection = get_mongo_collection()
        if collection is not None:
            collection.insert_one({
                "action": action,
                "details": details
            })
    except Exception:
        pass
