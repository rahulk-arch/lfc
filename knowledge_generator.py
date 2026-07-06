import os
import time
import json
from google import genai
from google.genai import types

try:
    import streamlit as st
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except (ImportError, KeyError, FileNotFoundError):
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Load Workbook
def generate_knowledge(category, location):
    # Gemini Client
    client = genai.Client(api_key=GEMINI_API_KEY)

    NUM_KEYWORDS = 40
    NUM_ORGANIZATION_TYPES = 25
    NUM_ACTIVITIES = 30
    NUM_BENEFICIARIES = 25
    NUM_SYNONYMS = 20
    NUM_LOCATION_ALIASES = 15


    # Gemini Prompt
    prompt = f"""
    You are an expert researcher.

    Category: {category}
    Location: {location}

    You are building a knowledge graph for search query generation.

    The output will later be combined by Python to create hundreds of Google search queries.

    Therefore every list must contain ONLY its own type of information.

    Rules:

    keywords
    - Only topics, concepts, domains and subjects.
    - Never include organization types.
    - Never include locations.
    - Never include activities.

    organization_types
    - Only legal or commonly used organization names.
    - Never include keywords.
    - Never include activities.
    - Never include locations.

    activities
    - Only programs, services or actions.
    - Never include organization names.
    - Never include keywords.

    beneficiaries
    - Only people or communities being served.

    synonyms
    - Only alternate names or phrases people use for the CATEGORY.
    - Do not include organization types.

    location_aliases
    - Only names or aliases of the given location.
    
    Rules:

    Generate at least

    {NUM_KEYWORDS} keywords

    {NUM_ORGANIZATION_TYPES} organization types

    {NUM_ACTIVITIES} activities

    {NUM_BENEFICIARIES} beneficiaries

    {NUM_SYNONYMS} synonyms

    {NUM_LOCATION_ALIASES} location aliases

    Do not generate Google search queries.

    Every item must be unique.

    Do not repeat the same idea using different wording.

    Prefer terms that people actually search on Google.

    Think of at least 5 different perspectives:
    - donor
    - parent
    - volunteer
    - government
    - CSR company

    
    IMPORTANT:

    Imagine you are trying to discover as many real organizations as possible using Google.

    Include words and phrases that people naturally type into Google.

    Mix:

    - formal terminology
    - everyday terminology
    - NGO terminology
    - government terminology
    - website terminology
    - CSR terminology

    Prefer search-friendly vocabulary over academic vocabulary.

    Think about how donors, parents, volunteers, journalists and CSR managers search online.

    Return ONLY valid JSON:
    {{
        "keywords": [],
        "organization_types": [],
        "activities": [],
        "beneficiaries": [],
        "synonyms": [],
        "location_aliases": []
    }}
    """



    # ----------------------------
    # Ask Gemini
    # ----------------------------
    for attempt in range(5):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.4,
                    top_p=0.9,
                    response_mime_type = "application/json"
            )
        )
            text = response.text

            if not text:
                raise Exception("Empty response from Gemini")

            data = json.loads(text)
            return data

        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")

            if attempt == 4:
                raise

            time.sleep(10)
