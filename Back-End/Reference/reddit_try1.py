from jsonmerge import merge

full_data = []

response_new = requests.get("https://oauth.reddit.com/r/lafc/new",
                            headers=headers,
                            params={"limit": "100"})

if response_new.status_code == 200:
    full_data.append(response_new.json())
    full_json = response_new.json()

params_loop = {"before": response_new.json()["data"]["children"][-1]["data"]['name'],
               "limit": "100"}

while len(full_data) < 10:
    response_new = requests.get("https://oauth.reddit.com/r/lafc/new",
                                headers=headers,
                                params=params_loop
                                )
    if response_new.status_code == 200:
        print(response_new.status_code)

    full_data.append(response_new.json())

    # Create a new JSON to merge with the JSON created in the first loop
    new_json = response_new.json()  # using a list to cross check
    full_json = merge(full_json, new_json)

    # Set a new after paramater to demarcate the start of the next 100 posts
    params_loop = {"before": response_new.json()["data"]["children"][-1]["data"]['name'],
                   "limit": "100"}

full_data[1]["data"]["before"]  # Test to see if there's an entry for 'before'