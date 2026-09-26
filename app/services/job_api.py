import os

import requests


def fetch_jobs(role, location):
	api_key = os.getenv("JSEARCH_API_KEY")
	if not api_key or api_key == "your_key_here":
		return []

	response = requests.get(
		"https://jsearch.p.rapidapi.com/search",
		headers={
			"X-RapidAPI-Key": api_key,
			"X-RapidAPI-Host": "jsearch.p.rapidapi.com",
		},
		params={"query": f"{role} in {location}", "page": "1", "num_pages": "1"},
		timeout=15,
	)
	if response.ok:
		return response.json().get("data", [])
	return []
