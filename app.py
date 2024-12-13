from flask import Flask, request, jsonify, Response
import google.generativeai as genai
import msgpack
import os
from dotenv import load_dotenv
from router import Genrate_Topic_SubTopic, Genrate_Topic_SubHeader
from promts import Query_Promt_LLama, Programming_Model_system_instruction, Science_Model_system_instruction, Maths_Model_system_instruction, Miscellaneous_Model_system_instruction
from json_repair import repair_json
import os
from groq import Groq
from utility import content_segmentation, call_api, Model_caller, LLama_Generate_Cover
import asyncio
import aiohttp
import json
import time
import re
load_dotenv()

app = Flask(__name__)

api_Key = os.environ.get("API_KEY")
api_key_groq=os.environ.get("GROQ_API_KEY")
genai.configure(api_key=api_Key)

router_model = genai.GenerativeModel("models/gemini-1.5-flash")
client = Groq(api_key=api_key_groq)

Programing_model = genai.GenerativeModel(
    model_name="gemini-1.5-flash", system_instruction=Programming_Model_system_instruction())
Science_model = genai.GenerativeModel(
    model_name="gemini-1.5-flash", system_instruction=Science_Model_system_instruction())
Maths_model = genai.GenerativeModel(
    model_name="gemini-1.5-flash", system_instruction=Maths_Model_system_instruction())
Miscellaneous_model = genai.GenerativeModel(
    model_name="gemini-1.5-flash", system_instruction=Miscellaneous_Model_system_instruction())

slave_Server = []
i = 1
while True:
    server_url = os.environ.get(f"SERVER_{i}_URL")
    if not server_url:
        break
    slave_Server.append(server_url)
    i += 1
slave_Server_Index = 0
slave_Server_Length = len(slave_Server)



@app.route('/v1/course-genration-outline', methods=['POST'])
def course_genration_outline():
    try:
        input_text = str(request.json.get('input_text'))
        dominant_topic, subtopics = Genrate_Topic_SubTopic(
            router_model, input_text)

        if dominant_topic == "Programming":
            out_line = Model_caller(
                Programing_model, input_text, dominant_topic, subtopics)
        elif dominant_topic == "Science":
            out_line = Model_caller(
                Science_model, input_text, dominant_topic, subtopics)
        elif dominant_topic == "Maths":
            out_line = Model_caller(
                Maths_model, input_text, dominant_topic, subtopics)
        else:
            out_line = Model_caller(
                Miscellaneous_model, input_text, dominant_topic, subtopics)

        clean_response = repair_json(out_line.text.lstrip("```json").rstrip(
            "```").strip())

        # packed_response = msgpack.packb({"response": clean_response})
        # return Response(packed_response, content_type='application/x-msgpack'), 200

        return jsonify(clean_response), 200
    except Exception as e:
        print(e)
        # packed_error_response = msgpack.packb(
        #     {"error": "An error occurred, you may have reached the rate limit"})
        # return Response(packed_error_response, content_type='application/x-msgpack'), 500
        return jsonify({"error": "An error occurred, you may have reached the rate limit"}), 500


def clean_html_content(html_content):
    clean_text = html_content.lstrip("```html").rstrip("```").strip()
    return clean_text


@app.route('/v1/course-genration-module', methods=['POST'])
def course_genration_module():
    async def main():
        module = str(request.json.get('module'))
        course = str(request.json.get('course'))
        topic = str(request.json.get('topic'))
        subtopics = Genrate_Topic_SubHeader(router_model, module, course)
        # print(subtopics)
        tasks = []
        local_slave_Server_Index = slave_Server_Index
        start_time = time.time()
        async with aiohttp.ClientSession() as session:
            for i in range(len(subtopics)):
                data = {"module": module, "course": course,
                        "topic": topic, "subtopic": subtopics[i]}
                tasks.append(call_api(
                    session, slave_Server[local_slave_Server_Index] + "/v1/course-genration-module", data))
                local_slave_Server_Index += 1
                local_slave_Server_Index %= slave_Server_Length

            results = await asyncio.gather(*tasks)
            final_text = " ".join(
                [clean_html_content(result.get('content', ''))
                 for result in results if result and 'content' in result]
            )

        elapsed_time = time.time() - start_time
        print(f"Elapsed time: {elapsed_time} seconds")
        packed_response = msgpack.packb({"content": final_text})
        return Response(packed_response, content_type='application/x-msgpack'), 200
    try:
        return asyncio.run(main())
    except Exception as e:
        print(e)
        packed_error_response = msgpack.packb(
            {"error": "An error occurred, you may have reached the rate limit"})
        return Response(packed_error_response, content_type='application/x-msgpack'), 500


@app.route('/v1/query', methods=['POST'])
def query_llm():
    try:
        query = str(request.json.get('query'))
        query_promt = Query_Promt_LLama(query)
        resp = LLama_Generate_Cover(client, query_promt)
        return jsonify({"content": str(resp)}), 200
    except Exception as e:
        print(e)
        return jsonify({"error": e}), 500


@app.route('/v1/ppt', methods=['POST'])
def ppt_llm():
    async def main():
        content = msgpack.unpackb(request.data, raw=False)
        content = content.get('content', '')
        result = content_segmentation(content)
        final_text = ""
        max_length = 5000
        print(len(result))
        final_compress = []
        i = 0
        while i < len(result):
            temp_text = result[i]
            i += 1
            while i < len(result) and len(result[i]) + len(temp_text) <= max_length:
                temp_text += result[i]
                i += 1
            final_compress.append(temp_text)

        print(len(final_compress))
        tasks = []
        local_slave_Server_Index = slave_Server_Index
        async with aiohttp.ClientSession() as session:
            for segment in final_compress:
                tasks.append(
                    call_api(
                        session, slave_Server[local_slave_Server_Index] + "/v1/ppt-content", {"content": segment})
                )
                local_slave_Server_Index += 1
                local_slave_Server_Index %= slave_Server_Length

            responses = await asyncio.gather(*tasks)
            final_text = {}
            final_rep = {}
            ptr=0
            # Process each response
            for response in responses:
                if response is not None:
                    content = response.get('slides', {})
                    # print("Raw slides:", content)
                    if isinstance(content, str):
                        try:
                            content = json.loads(repair_json(content))
                        except Exception as e:
                            print("Failed to parse slides content:", e)
                            content = {}

           
                    if isinstance(content, dict):
                        # print("Parsed content:", content)
                        for key, value in content.items():
                            final_text[key+f"_{ptr}"] = value

                        final_rep.update(final_text)
                        ptr+=1
                    else:
                        print("Content is not a dictionary:", content)

                    # Update the final_rep dictionary
            # print("Final representation:", final_rep)

            packed_response = msgpack.packb({"slides": final_rep})
            return Response(packed_response, content_type='application/x-msgpack'), 200

    try:
        return asyncio.run(main())
    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
