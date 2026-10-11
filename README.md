# Food Donation and Distribution Management System

## 1. Project Overview
The Food Donation and Distribution Management System is a web application designed to connect food donors with NGOs. It helps reduce food waste by making available food donations easier to track and request.

## 2. Technologies Used
- Python
- Streamlit
- MySQL
- MongoDB Atlas
- Pandas
- Pytest
- Bcrypt

## 3. Main Features
- User registration and login
- Password hashing using bcrypt
- Donor food donation management
- NGO donation request functionality
- Admin reporting interface
- MySQL relational database
- MongoDB activity logging
- Automated validation tests

## 4. Database Design
### MySQL
- `users`: stores user details and roles
- `donations`: stores food donation information
- `requests`: stores NGO requests
- `distributions`: records distribution details

### MongoDB
- `activity_logs`: stores application activity events

## 5. Installation
1. Install Python and MySQL.
2. Install project dependencies:

   `pip install -r requirements.txt`

3. Create the MySQL database by running `schema.sql` in MySQL Workbench.
4. Configure database credentials in `.streamlit/secrets.toml`.
5. Configure the MongoDB Atlas URI in the same secrets file.

## 6. Run the Application
Run this command in the project terminal:

`python -m streamlit run app.py`

## 7. Run Automated Tests
Run:

`python -m pytest -v`

The initial validation test suite passed all five tests.

## 8. Future Improvements
- More comprehensive integration tests
- Improved donation request approval and distribution workflows
- Stronger role-based access controls
- Better reporting and activity-log monitoring

## 9. Security Notes
Database credentials must remain private. Passwords should be stored as hashes, and database access should use appropriate permissions.
