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
    app.secret_key = "healthyHomeMeals"
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    # Load client secrets from env (Render) or file (local)
    if os.environ.get("CLIENT_SECRET_JSON"):
        secrets_data = json.loads(os.environ["CLIENT_SECRET_JSON"])
    else:
        with open(os.path.join(os.path.dirname(__file__), "..", "client_secret.json")) as f:
            secrets_data = json.load(f)

    GOOGLE_CLIENT_ID = secrets_data["web"]["client_id"]

    flow = Flow.from_client_config(
        secrets_data,
        scopes=[
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email",
            "openid",
        ],
        redirect_uri=secrets_data["data"]["redirect_uri"],
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
                redirect_uri=secrets_data["data"]["redirect_uri"],
            )

            flow.fetch_token(authorization_response=request.url)

            if session.get("state") != request.args.get("state"):
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

            return redirect(secrets_data["data"]["home"])

        except Exception as e:
            # You can log this or print to logs for Render debugging
            print("Callback error:", e)
            return "Internal Server Error", 500


    @app.route("/signout")
    def logout():
        session.clear()
        return redirect(secrets_data["data"]["home"])

    @app.route("/status")
    @login_is_required
    def status():
        return {}

