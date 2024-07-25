import streamlit as st
from streamlit import session_state as ss
from openai import OpenAI
import hmac
import json
import os
import requests
import replicate
import base64

client = OpenAI()

class Utils:
    @staticmethod
    def find_extra_snippets(data):
        results = []
        web_results = data.get("web", {}).get("results", [])
        for result in web_results:
            if "extra_snippets" in result:
                results.append({
                    "url": result.get("url"),
                    "age": result.get("age"),
                    "snippets": result.get("extra_snippets")
                })
        return results

    @staticmethod
    def brave_search(query):
        headers = {
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip',
            'X-Subscription-Token': os.getenv('BRAVE_API_KEY')
        }
        params = {
            "q" : query,
            "freshness" : ss.freshness,
            "country" : "au",
            "result_filter" : "web"}
        response = requests.get(f"https://api.search.brave.com/res/v1/web/search", headers=headers, params=params)
        data = response.json()
        snippets = Utils.find_extra_snippets(data)
        return json.dumps(snippets)
    
    @staticmethod
    def transcribe(audio_file, prompt = 'Summarize the contents of the transcript using bullet points'):        
        st.spinner('Transcribing audio file...')
        transcript = replicate.run(
            "vaibhavs10/incredibly-fast-whisper:3ab86df6c8f54c11309d4d1f930ac292bad43ace52d10c80d87eb258b3c9f79c",
            input={
                "task": "transcribe",
                "audio": audio_file,
                "batch_size": 64,
                "return_timestamps": False,
                "language": "english"
            })
        ss.transcript = transcript['text']
        ss.messages.append({'role':'function', 'name':'transcribe', 'content':ss.transcript})
        ss.messages.append({'role':'user', 'content':prompt})
        with st.chat_message("assistant"):
            stream = client.chat.completions.create(
                model=ss["openai_model"],
                messages= ss.messages,
                stream=True)
            response = st.write_stream(stream)
        ss.messages.append({"role": "assistant", "content": response})
        with st.expander('Transcript', expanded = False):
            st.json({'Transcript':ss.transcript})
        return 
    
    @staticmethod    
    def check_password():
        def password_entered():
            password_to_check = os.getenv('ST_PASSWORD', 'asuka')
            if hmac.compare_digest(ss["password"], password_to_check):
                ss["password_correct"] = True
                del ss["password"]  
            else:
                ss["password_correct"] = False
        if ss.get("password_correct", False):
            return True
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        if "password_correct" in ss:
            st.error("😕 Password incorrect")
        return False

    @staticmethod
    def encode_image(image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    @staticmethod
    def get_system_prompt(selected_prompt):
        return requests.get(f'https://raw.githubusercontent.com/danielmiessler/fabric/main/patterns/{selected_prompt}/system.md').text

    @staticmethod
    def improve_prompt(prompt):
        response = client.chat.completions.create( 
                model=ss.model,
                messages = [{
                    "role": "system",
                    "content": Utils.get_system_prompt('improve_prompt')
                }, {"role":"user", "content":prompt}])
        return response.choices[0].message.content
            
    
if not Utils.check_password():
    st.stop()
