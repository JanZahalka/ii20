"""
generate_secret_key.py

Author: Jan Zahalka (jan@zahalka.net)

Generates the secret key for the II-20 Django app (for security reasons, it is
not recommended to keep it as a part of the repository)
"""
from django.core.management.utils import get_random_secret_key
import json
import os
import sys

# Ensure the working directory is set to the scripts dir
rel_script_dir = os.path.dirname(sys.argv[0])

if rel_script_dir != "":
    os.chdir(rel_script_dir)

# Establish secret key paths
SECRETS_DIR = "../ii20/secrets"
SECRET_KEY_PATH = os.path.join(SECRETS_DIR, "secret_key.json")

# If the secrets directory does not exist, create it
if not os.path.exists(SECRETS_DIR):
    os.makedirs(SECRETS_DIR)

# If the secret key file exists, ask user for confirmation to overwrite
if os.path.exists(SECRET_KEY_PATH):
    user_confirmation = input(("The secret key file '%s' already exists. "
                              "Do you want to overwrite [y/N]? ")
                              % SECRET_KEY_PATH)
    if user_confirmation.lower() != "y":
        print("Keeping the old secret key file.")
        exit()

# Generate the secret key
key_entry = dict()
key_entry["secret_key"] = get_random_secret_key()

# Store it as JSON
with open(SECRET_KEY_PATH, "w") as f:
    f.write(json.dumps(key_entry))

print("Secret key generated and stored (%s)." % SECRET_KEY_PATH)
