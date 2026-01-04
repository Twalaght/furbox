#!/usr/bin/python3

# from argparse import ArgumentParser
# from e6pd import gen_headers, e6pd, parallel_download
from os import getenv
from pathlib import Path
from requests import get
from time import sleep
import json

# Read the base directory from the environment variable
base_dir = getenv("COMIC_PATH")

# Set the base directory and read in the database file
base_dir = Path(base_dir)
with open(base_dir / "comics.json") as f:
	comics = json.load(f)

# Sort the ongoing entries and return the data
comics["ongoing"].sort(key = lambda x: x["name"])
comics = comics["ongoing"]


import io
import gzip
import csv

db_index = get("https://e621.net/db_export/").text.splitlines()
pools_db_name = [x for x in db_index if "pools" in x][-1].split('"')[1]

data = get(f"https://e621.net/db_export/{pools_db_name}")
data = io.BytesIO(data.content)
# with open("pools-2023-05-18.csv.gz", "rb") as f:
# 	data = io.BytesIO(f.read())

pools = gzip.GzipFile(fileobj = data).read().decode()
data = io.StringIO(pools)
csv_data = list(csv.reader(data, delimiter=","))[1:]

# Search the downloaded set
search = [x["id"] for x in comics]
e6_data = {int(x[0]): x[1:] for x in csv_data if int(x[0]) in search}

for comic in comics:
	local_num = -comic["offset"]
	for page in (base_dir / comic["name"]).iterdir():
		if page.is_file(): local_num += 1

	server_num = len(e6_data[comic["id"]][-1].split(","))

	if local_num < server_num:
		print(f"{comic['name']} is behind e6 by {local_num - server_num} pages")
	elif local_num > server_num:
		print(f"\033[34m{comic['name']} is ahead of e6 by {local_num - server_num} pages\033[0m")
	else:
		print(f"\033[32m{comic['name']} is up to date\033[0m")
