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
load_dotenv()

app = Flask(__name__)

api_Key = os.environ.get("API_KEY")
genai.configure(api_key=api_Key)

router_model = genai.GenerativeModel("models/gemini-1.5-flash")
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

Programing_model = genai.GenerativeModel(
    model_name="gemini-1.5-flash", system_instruction=Programming_Model_system_instruction())
Science_model = genai.GenerativeModel(
    model_name="gemini-1.5-flash", system_instruction=Science_Model_system_instruction())
Maths_model = genai.GenerativeModel(
    model_name="gemini-1.5-flash", system_instruction=Maths_Model_system_instruction())
Miscellaneous_model = genai.GenerativeModel(
    model_name="gemini-1.5-flash", system_instruction=Miscellaneous_Model_system_instruction())

slave_Server = [os.environ.get("SERVER_1_URL"), os.environ.get(
    "SERVER_2_URL"), os.environ.get("SERVER_3_URL")]
slave_Server_Index = 0


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

        packed_response = msgpack.packb({"response": clean_response})
        return Response(packed_response, content_type='application/x-msgpack'), 200
    except Exception as e:
        print(e)
        packed_error_response = msgpack.packb(
            {"error": "An error occurred, you may have reached the rate limit"})
        return Response(packed_error_response, content_type='application/x-msgpack'), 500


@app.route('/v1/course-genration-module', methods=['POST'])
def course_genration_module():
    async def main():
        module = str(request.json.get('module'))
        course = str(request.json.get('course'))
        topic = str(request.json.get('topic'))
        subtopics = Genrate_Topic_SubHeader(router_model, module, course)

        subtopic_batches = [subtopics[i:i + 2]
                            for i in range(0, len(subtopics), 2)]
        tasks = []

        async with aiohttp.ClientSession() as session:
            for i in range(3):
                if i < len(subtopic_batches):
                    data = {"module": module, "course": course,
                            "topic": topic, "subtopics": subtopic_batches[i]}
                    tasks.append(
                        call_api(session, slave_Server[i]+"/v1/course-genration-module", data))

            results = await asyncio.gather(*tasks)
            final_text = " ".join([json.dumps(result) for result in results if result is not None])

        packed_response = msgpack.packb({"content": final_text})
        return Response(packed_response, content_type='application/x-msgpack'), 200
    try:
        return asyncio.run(main())
    except Exception as e:
        packed_error_response = msgpack.packb(
            {"error": "An error occurred, you may have reached the rate limit"})
        return Response(packed_error_response, content_type='application/x-msgpack'), 500


@app.route('/v1/query', methods=['POST'])
def query_llm():
    try:
        query = str(request.json.get('query'))
        content = str(request.json.get('content'))
        query_promt = Query_Promt_LLama(query, content)
        resp = LLama_Generate_Cover(client, query_promt)
        return jsonify({"content": str(resp)}), 200
    except Exception as e:
        return jsonify({"error": e}), 500


@app.route('/v1/ppt', methods=['POST'])
def ppt_llm():
    async def main():
        content = msgpack.unpackb(request.data)
        content = content.get('content', '')
        result = content_segmentation(content)
        final_text = ""
        max_length = 10000
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
        async with aiohttp.ClientSession() as session:
            for segment in final_compress:
                if slave_Server_Index == 0:
                    slave_Server_Index += 1
                    slave_Server_Index %= 3
                    tasks.append(
                        call_api(session, slave_Server[0]+"/v1/ppt-content", {"content": segment}))
                elif slave_Server_Index == 1:
                    slave_Server_Index += 1
                    slave_Server_Index %= 3
                    tasks.append(
                        call_api(session, slave_Server[1]+"/v1/ppt-content", {"content": segment}))
                else:
                    slave_Server_Index += 1
                    slave_Server_Index %= 3
                    tasks.append(
                        call_api(session, slave_Server[2]+"/v1/ppt-content", {"content": segment}))

            responses = await asyncio.gather(*tasks)
            final_text = " ".join(
                [str(response) for response in responses if response is not None])

        response = repair_json(final_text)
        packed_response = msgpack.packb({"slides": response})
        return Response(packed_response, content_type='application/x-msgpack'), 200

    try:
        return asyncio.run(main())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
