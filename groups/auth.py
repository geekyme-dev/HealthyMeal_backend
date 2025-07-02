import os
import json
from flask import session, abort, redirect, request
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
import cachecontrol
import requests
import google.auth.transport.requests
from utils.loginCheck import login_is_required

def init(app, db):
    dbUsers = db.users
    
    # ✅ Remove duplicate secret key - it's already set in main.py
    # ✅ Only allow insecure transport in development
    if app.debug or os.environ.get("FLASK_ENV") == "development":
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    
    # Load client secrets from env (Render) or file (local)
    if os.environ.get("CLIENT_SECRET_JSON"):
        secrets_data = json.loads(os.environ["CLIENT_SECRET_JSON"])
    else:
        with open(os.path.join(os.path.dirname(__file__), "..", "client_secret.json")) as f:
            secrets_data = json.load(f)
    
    GOOGLE_CLIENT_ID = secrets_data["web"]["client_id"]
    
    # ✅ Fixed redirect URI - check your CLIENT_SECRET_JSON structure
    # It should be either secrets_data["web"]["redirect_uris"][0] or a custom field
    redirect_uri = "https://healthymeal-backend.onrender.com/callback"  # Adjust this URL
    
    flow = Flow.from_client_config(
        secrets_data,
        scopes=[
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email",
            "openid",
        ],
        redirect_uri=redirect_uri,
    )
    
    @app.route("/signin")
    def login():
        authorization_url, state = flow.authorization_url()
        session["state"] = state
        return redirect(authorization_url)
    
    @app.route("/callback")
    def callback():
        try:
            # Re-initialize flow inside the route for thread safety
            flow = Flow.from_client_config(
                secrets_data,
                scopes=[
                    "https://www.googleapis.com/auth/userinfo.profile",
                    "https://www.googleapis.com/auth/userinfo.email",
                    "openid",
                ],
                redirect_uri=redirect_uri,
            )
            
            flow.fetch_token(authorization_response=request.url)
            
            if session.get("state") != request.args.get("state"):
                print("State mismatch error")
                abort(400)
            
            credentials = flow.credentials
            token_request = google.auth.transport.requests.Request()
            id_info = id_token.verify_oauth2_token(
                id_token=credentials._id_token,
                request=token_request,
                audience=GOOGLE_CLIENT_ID,
            )
            
            session["google_id"] = id_info.get("sub")
            session["name"] = id_info.get("name")
            session["fname"] = id_info.get("given_name")
            session["email"] = id_info.get("email")
            
            # ✅ Add user to database
            dbUsers.update_one(
                {"email": session["email"]},
                {
                    "$set": {"email": session["email"]},
                    "$setOnInsert": {
                        "data": {
                            "ingredients": [],
                            "allergies": [],
                            "dietaryStyle": []
                        }
                    },
                },
                upsert=True,
            )
            
            # ✅ Fixed redirect - use your frontend URL
            return redirect("https://healthymeal-frontend.onrender.com/")
            
        except Exception as e:
            print("Callback error:", str(e))
            print("Request URL:", request.url)
            print("Session state:", session.get("state"))
            print("Request state:", request.args.get("state"))
            return f"Authentication error: {str(e)}", 500
    
    @app.route("/signout")
    def logout():
        session.clear()
        return redirect("https://healthymeal-frontend.onrender.com/")
    
    @app.route("/status")
    @login_is_required
    def status():
        return {
            "signedIn": True,
            "email": session.get("email"),
            "name": session.get("name")
        }

