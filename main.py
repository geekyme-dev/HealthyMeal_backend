from flask import Flask
from flask_cors import CORS
import groups.auth
import groups.defaults
import groups.recipes
from pymongo import MongoClient
import json
import os
import pathlib

# ✅ Step 1: Write client_secret.json from environment variable
secret_json = os.environ.get("CLIENT_SECRET_JSON")
secret_file_path = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")

if secret_json and not os.path.exists(secret_file_path):
    with open(secret_file_path, "w") as f:
        f.write(secret_json)

# ✅ Step 2: Initialize Flask app
app = Flask("Google Login App")
CORS(app, supports_credentials=True, expose_headers="Authorization")

# ✅ Step 3: Connect to MongoDB using environment variable
mongoUrl = os.environ.get("MONGO_URI")
dbClient = MongoClient(mongoUrl)
db = dbClient.healthyHomeMeals

# ✅ Step 4: Initialize route groups
groups.auth.init(app, db)
groups.defaults.init(app, db)
groups.recipes.init(app, db)

# ✅ Step 5: Run server
if __name__ == "__main__":
    from os import environ
    port = int(environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

