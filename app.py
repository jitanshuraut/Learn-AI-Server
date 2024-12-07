from flask import Flask, request, Response
import google.generativeai as genai
import os
from dotenv import load_dotenv
from promts import  Genrate_Module, Programming_Model_system_instruction, Science_Model_system_instruction, Maths_Model_system_instruction, Miscellaneous_Model_system_instruction, ppt_genration
from json_repair import repair_json
import os
from groq import Groq
from utility import content_Repair
import msgpack

load_dotenv()

app = Flask(__name__)

api_Key = os.environ.get("API_KEY")
genai.configure(api_key=api_Key)

router_model = genai.GenerativeModel("models/gemini-1.5-flash")
Programing_model = genai.GenerativeModel(
    model_name="gemini-1.5-flash", system_instruction=Programming_Model_system_instruction())
Science_model = genai.GenerativeModel(
    model_name="gemini-1.5-flash", system_instruction=Science_Model_system_instruction())
Maths_model = genai.GenerativeModel(
    model_name="gemini-1.5-flash", system_instruction=Maths_Model_system_instruction())
Miscellaneous_model = genai.GenerativeModel(
    model_name="gemini-1.5-flash", system_instruction=Miscellaneous_Model_system_instruction())
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


@app.route('/v1/course-genration-module', methods=['POST'])
def course_genration_module():

    try:
        module = str(request.json.get('module'))
        course = str(request.json.get('course'))
        topic = str(request.json.get('topic'))
        subtopics_arr = (request.json.get('subtopics'))
        subtopics = ", ".join(subtopics_arr)

        if topic == "Programming":
            print("Programming")
            out_line_2 = Programing_model.generate_content(
                Genrate_Module(module, course, subtopics))
        elif topic == "Science":
            print("Science")
            out_line_2 = Science_model.generate_content(
                Genrate_Module(module, course, subtopics))
        elif topic == "Maths":
            print("Maths")
            out_line_2 = Maths_model.generate_content(
                Genrate_Module(module, course, subtopics))
        else:
            print("Miscellaneous_model")
            out_line_2 = Miscellaneous_model.generate_content(
                Genrate_Module(module, course, subtopics))

        final_text = content_Repair(out_line_2.text, client)
        return Response(msgpack.packb({"content": str(final_text)}), content_type='application/x-msgpack'), 200
    except Exception as e:
        return Response(msgpack.packb({"error": "An error occurred, you may have reached the rate limit"}), content_type='application/x-msgpack'), 500
        # return jsonify({"error": e}), 500


@app.route('/v1/ppt-content', methods=['POST'])
def ppt_llm():
    try:
        content = str(request.json.get('content'))
        prompt = ppt_genration(content)
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                            "content": "You are a helpful assistant who specializes in generating concise and informative PowerPoint slides."
                },
                {
                    "role": "user",
                            "content": prompt,
                }
            ],
            model="llama-3.1-70b-versatile",
        )

        print("--------------------------------------------")
        print(chat_completion.choices[0].message.content)
        # print(len(combined_segment))
        print("--------------------------------------------")
        final_text = chat_completion.choices[0].message.content
        print(final_text)
        response = repair_json(final_text)
        return Response(msgpack.packb({"slides": response}), content_type='application/x-msgpack'), 200

    except Exception as e:
        return Response(msgpack.packb({"error": str(e)}), content_type='application/x-msgpack'), 500


if __name__ == '__main__':
    app.run(debug=True)
