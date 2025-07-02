from flask import Flask
from flask_cors import CORS
import groups.auth
import groups.defaults
import groups.recipes
from pymongo import MongoClient
import json
import os

# ✅ Step 1: Load client secrets
secret_json = os.environ.get("CLIENT_SECRET_JSON")
secrets_data = json.loads(secret_json) if secret_json else {}

# ✅ Step 2: Initialize Flask app
app = Flask("Google Login App")
# Configure Flask session (IMPORTANT for authentication)
app.secret_key = os.environ.get("SECRET_KEY", "fallback-secret-key-for-development")
app.config['SESSION_COOKIE_SECURE'] = True  # Only send cookies over HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent XSS
app.config['SESSION_COOKIE_SAMESITE'] = 'None'  # Allow cross-origin cookies
CORS(app,
     origins=["https://healthymeal-frontend.onrender.com"],
     supports_credentials=True,
     expose_headers=["Authorization"],
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

# ✅ Step 3: Connect to MongoDB
mongoUrl = os.environ.get("MONGODB_URI")
print("🧪 MONGODB_URI loaded:", mongoUrl)  # Debug line
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


