import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import os
import pathlib
import json
import requests
from pprint import pprint
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# Load ingredients and recipes
ingredients_file = os.path.join(
    pathlib.Path(__file__).parent.parent, "data/ingredients.csv"
)
ingredients = pd.read_csv(ingredients_file)
vectorizer = CountVectorizer(stop_words="english")
ingredients_vectors = vectorizer.fit_transform(ingredients["ingredients"])

recipes_file = os.path.join(pathlib.Path(__file__).parent.parent, "data/recipes.csv")
recipes = pd.read_csv(recipes_file)

# Helper to load YouTube API key lazily
def get_yt_api_key():
    secret_file = os.path.join(pathlib.Path(__file__).parent.parent, "client_secret.json")
    try:
        with open(secret_file, "r") as f:
            return json.load(f)["data"]["youtube"]
    except Exception as e:
        print(f"[ERROR] Failed to load YouTube API Key: {e}")
        return None


def suggest_recipes_index(input_ingredients, num_suggestions):
    input_str = ", ".join(input_ingredients)
    input_vector = vectorizer.transform([input_str])
    similarity_scores = cosine_similarity(input_vector, ingredients_vectors)
    top_indices = similarity_scores.argsort()[0][-num_suggestions:]
    return list(top_indices)


def getDietString(diet):
    try:
        return ", ".join([item for item in diet if item != "Vegetarian"])
    except:
        return "General"


def getRecipes(ingredients, diet):
    res = requests.post(
        "https://realfood.tesco.com/api/ingredientsearch/getrecipes",
        json={
            "ingredients": ingredients,
            "dietaryRequirements": diet,
            "mandatoryIngredients": [],
        },
    )
    resData = res.json()

    suggested_recipes_dict = [
        {
            "name": i["recipeName"],
            "ingredients": i["ingredientsList"],
            "time": i["duration"],
            "serves": i["serves"],
            "instructions": [],
            "url": i["recipeUrl"].split("/")[-1][:-5],
            "image": i["recipeImage"],
            "diet": getDietString(i["dietary"]),
        }
        for i in resData["results"]
    ]

    return suggested_recipes_dict[:3] if len(suggested_recipes_dict) >= 3 else suggested_recipes_dict


def ptTimeToMins(time):
    try:
        t = datetime.strptime(time, "PT%MM")
        td = timedelta(minutes=t.minute)
    except:
        t = datetime.strptime(time, "PT%HH%MM")
        td = timedelta(hours=t.hour, minutes=t.minute)
    return td.total_seconds() // 60


def getRecipeDetails(slug):
    parser = "html.parser"
    req = requests.get("https://realfood.tesco.com/recipes/" + slug + ".html")
    soup = BeautifulSoup(req.text, parser)
    data = json.loads(
        "".join(soup.find("script", {"type": "application/ld+json"}).contents)
    )

    return {
        "name": data["name"],
        "ingredients": data["recipeIngredient"],
        "time": ptTimeToMins(data["totalTime"]),
        "cuisine": data["recipeCuisine"],
        "instructions": "\n".join([i["text"] for i in data["recipeInstructions"]]),
        "url": data["url"],
        "image": data["image"][0]["url"],
        "id": slug,
        "nutrition": {
            "calories": data["nutrition"]["calories"],
            "fats": data["nutrition"]["fatContent"],
            "protein": data["nutrition"]["proteinContent"],
        },
        "feeds": data["recipeYield"],
    }


def getRecipeByIndex(index):
    yt_api_key = get_yt_api_key()
    if yt_api_key is None:
        return {"error": "YouTube API key not found"}

    recipe = getRecipeDetails(index)

    res = requests.get(
        "https://www.googleapis.com/youtube/v3/search",
        params={
            "q": f"{recipe['name']} recipe",
            "videoEmbeddable": "true",
            "type": "video",
            "key": yt_api_key,
            "maxResults": 1,
            "part": "snippet",
        },
    )
    resData = res.json()
    recipe["youtube"] = (
        "https://www.youtube.com/embed/" + resData["items"][0]["id"]["videoId"]
    )
    return recipe

