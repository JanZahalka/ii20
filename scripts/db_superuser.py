"""
db_superuser.py

Author: Jan Zahalka (jan@zahalka.net)

Assists in setting up the app "superuser" responsible for automanaging II-20's
DB.
"""
import json
import os
import sys

# Ensure the working directory is set to the scripts dir
rel_script_dir = os.path.dirname(sys.argv[0])

if rel_script_dir != "":
    os.chdir(rel_script_dir)

# Establish DB superuser info location
SECRETS_DIR = "../ii20/secrets"
DB_SUPERUSER_PATH = os.path.join(SECRETS_DIR, "db_superuser.json")

print("Creating the database superuser.")

# If the secrets directory does not exist, create it
if not os.path.exists(SECRETS_DIR):
    os.makedirs(SECRETS_DIR)

# If the DB superuser file exists, ask user for confirmation to overwrite
if os.path.exists(DB_SUPERUSER_PATH):
    user_confirmation = input(("The DB superuser info file '%s' "
                               "already exists. "
                              "Do you want to overwrite [y/N]? ")
                              % DB_SUPERUSER_PATH)
    if user_confirmation.lower() != "y":
        print("Keeping the old DB superuser info file.")
        exit()

# Ask the user for the superuser's name
username = input("Username: ")

# A VERY loose username validity check: only whitespace usernames are rejected,
# everything else accepted. It is assumed no II-20 admin would want to
# break their own system right away...
if username.isspace():
    print("The username must contain non-whitespace characters.")
    exit()

# Ask the user for password and password confirmation
password = input("Password: ")
password_conf = input("Password (again): ")

# Check that the passwords match
if password != password_conf:
    print("The passwords do not match.")
    exit()

# Store the DB superuser info
db_superuser_entry = dict()
db_superuser_entry["username"] = username
db_superuser_entry["password"] = password

with open(DB_SUPERUSER_PATH, "w") as f:
    f.write(json.dumps(db_superuser_entry))


