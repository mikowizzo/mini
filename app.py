from utils import *
st.set_page_config(layout="wide")

from openai import OpenAI
import streamlit as st
from streamlit import session_state as ss
from atomic_agents.lib.components.agent_memory import AgentMemory

# Initialize OpenAI client
client = OpenAI()

# Initialize memory if it does not exist in session state
if 'memory' not in ss:
    ss.memory = AgentMemory(max_messages=10)
    ss.model = 'gpt-4o-mini'

# Sidebar 
with st.sidebar:
    if st.button('New Chat'):
        ss.memory = AgentMemory(max_messages=ss.max_messages)
    ss.system_prompt = st.selectbox('System Prompt', options=['raw_query','ai','create_micro_summary','improve_writing', 
                                                              'coding_master','explain_code', 'extract_wisdom', 'summarize',
                                                              'create_5_sentence_summary','extract_predictions', 'find_hidden_message'])
    system_prompt =  Utils.get_system_prompt(ss.system_prompt)
    ss.max_messages = st.slider('Max messages', min_value=1, max_value=20, value=10, step=1)
    ss.model = st.radio('LLM Model', ['gpt-4o-mini'])
    ss.improve_prompt = st.toggle('Improve Prompt', value = False)
    ss.search_web = st.toggle('Search Web', value = False)
    if ss.search_web:
        st.radio('Freshness', ['pd', 'pw', 'pm', 'py'],index = 2, horizontal=True, key='freshness')
    ss.memory.max_messages = ss.max_messages
    if st.toggle('Vision', value = False, key='vision'):
        ss.image_file = st.file_uploader('Upload image', ['jpg', 'png', 'webp', 'gif'])
        if ss.image_file is not None:
            encoded_image = Utils.encode_image(ss.image_file)

# Display the message history
with st.expander('System Prompt'):
    st.markdown(system_prompt)
for message in ss.memory.history:
    with st.chat_message(message.role):
        st.markdown(message.content)

# Chat input from the user
if prompt := st.chat_input("What is up?"):
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get chat history and generate assistant's response
    with st.chat_message("assistant"):
        if ss.improve_prompt:
            prompt = Utils.improve_prompt(prompt)
            st.write(f'Improved prompt: {prompt}')

        if ss.search_web:
            ss.memory.add_message("user", Utils.brave_search(prompt))

        if ss.vision:
            if ss.image_file is not None:
                st.image(ss.image_file)
                ss.memory.add_message('user', [{"type": "text","text": prompt},
                                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}}])
                
        ss.memory.add_message("user", prompt)

        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{'role':'system', 'content':system_prompt}]+ss.memory.get_history(),
            stream=True,
        )
        response = st.write_stream(stream)

    # Add assistant's response to memory
    ss.memory.add_message("assistant", response)

