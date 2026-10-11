
import streamlit as st
import mysql.connector
from mysql.connector import Error
from pymongo import MongoClient


def get_mysql_connection():
    """Create a connection to the MySQL database."""
    try:
        config = st.secrets["mysql"]

        connection = mysql.connector.connect(
            host=config["host"],
            port=int(config.get("port", 3306)),
            user=config["user"],
            password=config["password"],
            database=config["database"]
        )

        if connection.is_connected():
            return connection

        raise Error("Could not connect to MySQL.")

    except Error:
        raise
    except Exception as exc:
        raise RuntimeError(
            "Check your MySQL settings in .streamlit/secrets.toml."
        ) from exc


def get_mongo_collection():
    """Return the MongoDB activity-log collection, if configured."""
    config = st.secrets.get("mongo", {})
    uri = config.get("uri", "")

    if not uri:
        return None

    client = MongoClient(uri, serverSelectionTimeoutMS=3000)
    client.admin.command("ping")

    return client["food_donation_db"]["activity_logs"]


def log_activity(action, details):
    """Save an activity to MongoDB when it is configured."""
    try:
        collection = get_mongo_collection()

        if collection is not None:
            collection.insert_one({
                "action": str(action),
                "details": str(details)
            })

    except Exception:
        # Logging failure should not crash the main application.
        pass
