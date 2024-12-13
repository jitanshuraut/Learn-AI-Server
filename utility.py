import re
import asyncio
import aiohttp
from promts import Genrate_Outline
import msgpack


async def call_api(session, endpoint, data):
    packed_data = msgpack.packb(data)
    async with session.post(endpoint, data=packed_data, headers={'Content-Type': 'application/x-msgpack'}) as response:
        packed_response = await response.read()
        unpacked_response = msgpack.unpackb(packed_response, raw=False)
        return unpacked_response


def Model_caller(model, input_text, dominant_topic, subtopics):
    subtopics_text = ", ".join(subtopics)
    out_line = model.generate_content(Genrate_Outline(
        input_text, subtopics_text, dominant_topic))
    return out_line


def LLama_Generate_Cover(model, query_prompt, sys_prompt="You are a helpful assistant."):
    resp = model.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": sys_prompt,
            },
            {
                "role": "user",
                "content": query_prompt,
            }
        ],
        model="llama-3.1-70b-versatile",
    )
    return resp.choices[0].message.content


def segment_text(text, tag):
    segments = re.split(rf'(<{tag}.*?>.*?</{tag}>)', text, flags=re.DOTALL)
    result = []
    current_segment = ""

    for segment in segments:
        if re.match(rf'<{tag}.*?>.*?</{tag}>', segment, flags=re.DOTALL):
            if current_segment:
                result.append(current_segment)
                current_segment = ""
        current_segment += segment

    if current_segment:
        result.append(current_segment)

    return result


def content_segmentation(content):
    segments_h1 = segment_text(content, 'h1')
    segments_h2 = []
    segments_h3 = []

    for segment_h1 in segments_h1:
        segments_h2.extend(segment_text(segment_h1, 'h2'))

    for segment_h2 in segments_h2:
        segments_h3.extend(segment_text(segment_h2, 'h3'))

    if len(segments_h3) > len(segments_h2) and len(segments_h3) > len(segments_h1):
        result = segments_h3
    elif len(segments_h2) > len(segments_h1):
        result = segments_h2
    else:
        result = segments_h1
    return result
