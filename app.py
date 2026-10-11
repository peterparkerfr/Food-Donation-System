
import streamlit as st
import pandas as pd
import bcrypt

from datetime import date
from mysql.connector import Error
from database import get_mysql_connection, log_activity

st.set_page_config(
    page_title="Food Donation System",
    page_icon="🍲",
    layout="wide"
)

st.title("🍲 Food Donation and Distribution Management System")
st.caption("Reduce food waste. Connect donors with NGOs.")


# ---------- DATABASE HELPERS ----------

def query_df(sql, params=()):
    conn = get_mysql_connection()
    try:
        return pd.read_sql(sql, conn, params=params)
    finally:
        conn.close()


def execute_sql(sql, params=()):
    conn = get_mysql_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def register_user(name, email, password, role):
    hashed = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    execute_sql(
        """
        INSERT INTO users (name, email, password_hash, role)
        VALUES (%s, %s, %s, %s)
        """,
        (name.strip(), email.strip().lower(), hashed, role)
    )

    log_activity("user_registered", f"{email} registered as {role}")


def login_user(email, password):
    users = query_df(
        """
        SELECT id, name, email, password_hash, role
        FROM users WHERE email = %s
        """,
        (email.strip().lower(),)
    )

    if users.empty:
        return None

    user = users.iloc[0]
    hashed = user["password_hash"]

    if isinstance(hashed, str):
        hashed = hashed.encode("utf-8")

    if bcrypt.checkpw(password.encode("utf-8"), hashed):
        return {
            "id": int(user["id"]),
            "name": user["name"],
            "email": user["email"],
            "role": user["role"]
        }

    return None


# ---------- DONOR ----------

def donor_section(user):
    st.header("Add Food Donation")

    with st.form("donation_form"):
        food = st.text_input("Food name")
        quantity = st.number_input(
            "Quantity", min_value=0.1, value=1.0
        )
        unit = st.selectbox(
            "Unit", ["servings", "kg", "litres", "packs", "boxes"]
        )
        expiry = st.date_input("Expiry date", min_value=date.today())
        submit = st.form_submit_button("Add Donation")

    if submit:
        if not food.strip():
            st.error("Enter a food name.")
        else:
            try:
                execute_sql(
                    """
                    INSERT INTO donations
                    (donor_id, food_name, quantity, unit, expiry_date, status)
                    VALUES (%s, %s, %s, %s, %s, 'Available')
                    """,
                    (user["id"], food.strip(), quantity, unit, expiry)
                )
                log_activity("donation_created", f"{food} added by user {user['id']}")
                st.success("Donation added!")
                st.rerun()
            except Error:
                st.error("Could not save donation. Check the database.")

    st.subheader("My Donations")
    mine = query_df(
        """
        SELECT id, food_name, quantity, unit, expiry_date, status
        FROM donations WHERE donor_id = %s ORDER BY id DESC
        """,
        (user["id"],)
    )
    st.dataframe(mine, use_container_width=True)


# ---------- NGO ----------

def ngo_section(user):
    st.header("Request Food")

    available = query_df(
        """
        SELECT id, food_name, quantity, unit, expiry_date
        FROM donations
        WHERE status = 'Available' AND expiry_date >= CURDATE()
        ORDER BY expiry_date
        """
    )

    if available.empty:
        st.info("No available donations right now.")
    else:
        choices = {
            f"{r.food_name} | {r.quantity} {r.unit} | ID {r.id}": int(r.id)
            for r in available.itertuples()
        }

        with st.form("request_form"):
            selected = st.selectbox("Select donation", list(choices.keys()))
            donation_id = choices[selected]
            row = available[available["id"] == donation_id].iloc[0]

            quantity = st.number_input(
                "Quantity requested",
                min_value=0.1,
                max_value=float(row["quantity"]),
                value=min(1.0, float(row["quantity"]))
            )
            submit = st.form_submit_button("Submit Request")

        if submit:
            conn = get_mysql_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT quantity, status FROM donations
                    WHERE id = %s FOR UPDATE
                    """,
                    (donation_id,)
                )
                item = cursor.fetchone()

                if (
                    not item
                    or item[1] != "Available"
                    or quantity > float(item[0])
                ):
                    conn.rollback()
                    st.error("Donation is unavailable or quantity is too high.")
                else:
                    cursor.execute(
                        """
                        INSERT INTO requests
                        (donation_id, ngo_id, quantity_requested, status)
                        VALUES (%s, %s, %s, 'Pending')
                        """,
                        (donation_id, user["id"], quantity)
                    )
                    conn.commit()
                    log_activity(
                        "request_created",
                        f"NGO {user['id']} requested donation {donation_id}"
                    )
                    st.success("Request submitted for admin approval!")
                    st.rerun()
            except Error:
                conn.rollback()
                st.error("Request could not be saved.")
            finally:
                conn.close()

    st.subheader("My Requests")
    requests = query_df(
        """
        SELECT r.id, d.food_name, r.quantity_requested,
               d.unit, r.status
        FROM requests r
        JOIN donations d ON d.id = r.donation_id
        WHERE r.ngo_id = %s ORDER BY r.id DESC
        """,
        (user["id"],)
    )
    st.dataframe(requests, use_container_width=True)


# ---------- ADMIN ----------

def admin_section():
    st.header("Admin: Pending Requests")

    pending = query_df(
        """
        SELECT r.id, r.donation_id, r.ngo_id,
               r.quantity_requested, r.status,
               d.food_name, d.quantity AS available_quantity,
               d.unit, u.name AS ngo_name
        FROM requests r
        JOIN donations d ON d.id = r.donation_id
        JOIN users u ON u.id = r.ngo_id
        WHERE r.status = 'Pending'
        ORDER BY r.id
        """
    )

    if pending.empty:
        st.info("No pending requests.")
    else:
        st.dataframe(pending, use_container_width=True)

        options = {
            f"Request {r.id}: {r.food_name} for {r.ngo_name}": int(r.id)
            for r in pending.itertuples()
        }

        with st.form("admin_decision_form"):
            selected = st.selectbox("Select request", list(options.keys()))
            request_id = options[selected]
            decision = st.radio(
                "Decision", ["Approve", "Reject"], horizontal=True
            )
            submit = st.form_submit_button("Save Decision")

        if submit:
            conn = get_mysql_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT r.donation_id, r.quantity_requested,
                           d.quantity, d.status
                    FROM requests r
                    JOIN donations d ON d.id = r.donation_id
                    WHERE r.id = %s AND r.status = 'Pending'
                    FOR UPDATE
                    """,
                    (request_id,)
                )
                item = cursor.fetchone()

                if not item:
                    st.error("Request is no longer pending.")
                    conn.rollback()
                else:
                    donation_id, requested, stock, status = item

                    if decision == "Approve":
                        if status != "Available" or float(requested) > float(stock):
                            st.error("Not enough available food to approve.")
                            conn.rollback()
                            return

                        remaining = float(stock) - float(requested)
                        new_status = "Available" if remaining > 0 else "Requested"

                        cursor.execute(
                            """
                            UPDATE donations SET quantity = %s, status = %s
                            WHERE id = %s
                            """,
                            (remaining, new_status, donation_id)
                        )
                        cursor.execute(
                            "UPDATE requests SET status = 'Approved' WHERE id = %s",
                            (request_id,)
                        )
                    else:
                        cursor.execute(
                            "UPDATE requests SET status = 'Rejected' WHERE id = %s",
                            (request_id,)
                        )

                    conn.commit()
                    log_activity(
                        "request_decision",
                        f"Request {request_id}: {decision}"
                    )
                    st.success(f"Request {decision.lower()}d.")
                    st.rerun()

            except Error:
                conn.rollback()
                st.error("Could not update request.")
            finally:
                conn.close()

    # Record distribution for approved requests.
    st.header("Record Food Distribution")

    approved = query_df(
        """
        SELECT r.id, d.food_name, r.quantity_requested,
               d.unit, u.name AS ngo_name
        FROM requests r
        JOIN donations d ON d.id = r.donation_id
        JOIN users u ON u.id = r.ngo_id
        WHERE r.status = 'Approved'
          AND NOT EXISTS (
              SELECT 1 FROM distributions ds
              WHERE ds.request_id = r.id
          )
        ORDER BY r.id
        """
    )

    if approved.empty:
        st.info("No approved requests waiting for distribution.")
    else:
        options = {
            f"Request {r.id}: {r.food_name} for {r.ngo_name}": int(r.id)
            for r in approved.itertuples()
        }

        with st.form("distribution_form"):
            selected = st.selectbox(
                "Approved request", list(options.keys())
            )
            request_id = options[selected]
            row = approved[approved["id"] == request_id].iloc[0]

            quantity = st.number_input(
                "Quantity distributed",
                min_value=0.1,
                max_value=float(row["quantity_requested"]),
                value=float(row["quantity_requested"])
            )
            submit = st.form_submit_button("Save Distribution")

        if submit:
            conn = get_mysql_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT quantity_requested, status
                    FROM requests
                    WHERE id = %s FOR UPDATE
                    """,
                    (request_id,)
                )
                req = cursor.fetchone()

                if (
                    not req
                    or req[1] != "Approved"
                    or quantity > float(req[0])
                ):
                    conn.rollback()
                    st.error("Request status or quantity is invalid.")
                else:
                    cursor.execute(
                        """
                        INSERT INTO distributions
                        (request_id, distributed_quantity)
                        VALUES (%s, %s)
                        """,
                        (request_id, quantity)
                    )
                    cursor.execute(
                        "UPDATE requests SET status = 'Completed' WHERE id = %s",
                        (request_id,)
                    )
                    conn.commit()
                    log_activity(
                        "distribution_recorded",
                        f"Request {request_id}, quantity {quantity}"
                    )
                    st.success("Distribution recorded!")
                    st.rerun()
            except Error:
                conn.rollback()
                st.error("Distribution could not be saved.")
            finally:
                conn.close()

    st.header("Distribution History")
    history = query_df(
        """
        SELECT ds.id, ds.request_id, ds.distributed_quantity,
               d.food_name, d.unit, u.name AS ngo_name
        FROM distributions ds
        JOIN requests r ON r.id = ds.request_id
        JOIN donations d ON d.id = r.donation_id
        JOIN users u ON u.id = r.ngo_id
        ORDER BY ds.id DESC
        """
    )
    st.dataframe(history, use_container_width=True)

    st.header("Donation Report")
    donations = query_df("SELECT * FROM donations ORDER BY id DESC")
    st.dataframe(donations, use_container_width=True)
    st.download_button(
        "Download Donation CSV",
        data=donations.to_csv(index=False),
        file_name="donation_report.csv",
        mime="text/csv"
    )


# ---------- LOGIN AND REGISTRATION ----------

if "user" not in st.session_state:
    login_tab, register_tab = st.tabs(["Login", "Register"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input(
                "Password", type="password", key="login_password"
            )
            login_clicked = st.form_submit_button("Login")

        if login_clicked:
            try:
                user = login_user(email, password)
                if user:
                    st.session_state["user"] = user
                    log_activity("login", f"User {user['id']} logged in")
                    st.rerun()
                else:
                    st.error("Invalid email or password.")
            except Error:
                st.error("Database connection failed. Check your settings.")

    with register_tab:
        with st.form("register_form"):
            name = st.text_input("Full name")
            email = st.text_input("Email", key="register_email")
            password = st.text_input(
                "Password (minimum 8 characters)",
                type="password", key="register_password"
            )
            role = st.selectbox("Account type", ["donor", "ngo"])
            register_clicked = st.form_submit_button("Register")

        if register_clicked:
            if not name.strip() or not email.strip():
                st.error("Name and email are required.")
            elif len(password) < 8:
                st.error("Password must be at least 8 characters.")
            else:
                try:
                    register_user(name, email, password, role)
                    st.success("Account created! Now sign in.")
                except Error as exc:
                    if getattr(exc, "errno", None) == 1062:
                        st.error("This email is already registered.")
                    else:
                        st.error("Registration failed. Check the database.")

else:
    user = st.session_state["user"]

    with st.sidebar:
        st.write(f"Signed in: {user['name']}")
        st.write(f"Role: {user['role'].title()}")

        if st.button("Logout"):
            st.session_state.pop("user", None)
            st.rerun()

    try:
        totals = query_df(
            """
            SELECT COUNT(*) AS total,
                   COALESCE(SUM(status = 'Available'), 0) AS available
            FROM donations
            """
        ).iloc[0]

        requests_total = query_df(
            "SELECT COUNT(*) AS total FROM requests"
        ).iloc[0]["total"]

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Donations", int(totals["total"]))
        c2.metric("Available Donations", int(totals["available"]))
        c3.metric("Total Requests", int(requests_total))

        st.subheader("Available Food Donations")
        available = query_df(
            """
            SELECT d.id, d.food_name, d.quantity, d.unit,
                   d.expiry_date, u.name AS donor
            FROM donations d
            JOIN users u ON u.id = d.donor_id
            WHERE d.status = 'Available'
              AND d.expiry_date >= CURDATE()
            ORDER BY d.expiry_date
            """
        )
        st.dataframe(available, use_container_width=True)

        if user["role"] == "donor":
            donor_section(user)
        elif user["role"] == "ngo":
            ngo_section(user)
        elif user["role"] == "admin":
            admin_section()
        else:
            st.error("Unknown account role.")

    except Error:
        st.error("Could not load dashboard. Check MySQL connection and tables.")
