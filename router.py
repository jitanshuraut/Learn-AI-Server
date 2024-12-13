import json
from promts import Generate_Content_Headers, Promt_Genrate_topic
from json_repair import repair_json


def Genrate_Topic_SubTopic(model, text):
    response = model.generate_content(Promt_Genrate_topic(text))
    clean_response = response.text.strip()
    clean_response = clean_response.lstrip("```json").rstrip(
        "```").strip()

    try:
        response_dict = json.loads(clean_response)
        dominant_topic = response_dict.get("dominant_subject")
        subtopics = response_dict.get("subtopics", [])
        print(dominant_topic, subtopics)
        return dominant_topic, subtopics
    except json.JSONDecodeError as e:
        print(f"Failed to decode JSON: {e}")
        return None, []

def Genrate_Topic_SubHeader(model, text, course):
    response = model.generate_content(Generate_Content_Headers(text, course))
    clean_response = response.text.strip()
    clean_response = clean_response.lstrip("```json").rstrip("```").strip()
    
    # print("****************************************************************************************************")
    clean_response = repair_json(clean_response)

    try:
        if isinstance(clean_response, str):
            response_data = json.loads(clean_response)
        else:
            response_data = clean_response  

        if isinstance(response_data, list):
            print("Response is a list. Extracting the dictionary from the list.")
            response_dict = response_data[-1]  
        elif isinstance(response_data, dict):
            response_dict = response_data
        else:
            raise ValueError("Unexpected response format: Not a list or dictionary.")
        dominant_topic = response_dict.get("category", "Unknown Category")
        subtopics = response_dict.get("content_headers", [])
        return subtopics
    except (json.JSONDecodeError, AttributeError, IndexError, ValueError) as e:
        print(f"Error processing response: {e}")
        return []
