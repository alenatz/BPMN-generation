import streamlit as st
import streamlit.components.v1 as components
import openai
from components.BPMNGenerator import BPMNGenerator
from components.SignavioConnector import SignavioConnector, AuthenticationError, UploadError, ExportError
from io import BytesIO
import xml.etree.ElementTree as ET

st.set_page_config(layout="wide", page_title="BPMN Generator")

st.title("BPMN Generator")

if "final_bpmn" not in st.session_state or "visualization_ready" not in st.session_state:
    st.session_state["final_bpmn"] = None
    st.session_state["visualization_ready"] = False

def clear_session():
    st.session_state["final_bpmn"] = None
    st.session_state["visualization_ready"] = False

col1, col2 = st.columns([0.3,0.7], border=True)

col2.subheader("Output", divider="grey")

col1.subheader("Input", divider="grey")
col1.info("""Privacy notice  
        This application does not store any data persistently. Any input (voice recording, api key, credentials) is solely used for the duration of the session.
        They are not logged, saved, or transmitted to any third party besides the relevant API endpoints: OpenAI, and if selected SAP Signavio.
        Users are responsible for safeguarding their API keys and credentials. We recommend using service accounts or limited-scope keys when possible.
        By using this application, you agree to this handling of your data.
        """)
api_key = col1.text_input("OpenAI API key", type="password", help="You can find your API key by accessing https://platform.openai.com/ and navigating to API keys", on_change=clear_session)
input = col1.radio(
    "Select your input type",
    ["Audio upload", "Recording input", "Text input"],
    horizontal=True
)
audio = None
recording = None
text = ""
if input == "Audio upload":
    audio = col1.file_uploader("Upload your recorded process description", type=["wav", "mp3", "m4a"], on_change=clear_session)
elif input == "Recording input":
    recording = col1.audio_input("Record the process description", on_change=clear_session)
elif input == "Text input":
    text = col1.text_area("Input the description of your process", on_change=clear_session)

viz = col1.radio(
    "Select how the model is visualized",
    ["bpmn.io", "SAP Signavio"],
    captions=["No account needed", "Only possible with SAP Signavio account"],
    horizontal=True,
    on_change=clear_session
)
if viz == "SAP Signavio":
    username = col1.text_input("SAP Signavio username")
    password = col1.text_input("SAP Signavio password", type="password")
    system_instance = col1.selectbox(
        "SAP Signavio instance",
        ("https://academic.signavio.com", 'https://editor.signavio.com'),
        index=None,
        placeholder="Select the type of your SAP Signavio instance"
    )
    workspace_id = col1.text_input("Workspace ID", help="You can find your workspace ID by accessing Help in your Process Manager, select Workspace Information, and copy the Workspace ID")
    target_directory = col1.text_input("Target directory ID", help="You can find your target directory ID by accessing the directory in your Process Manager and copying the 32 character key displayed after directory/ in the URL")


if col1.button("Generate BPMN", type="primary", disabled=((recording is None and audio is None and text == "") or (api_key == "") or (viz == "SAP Signavio" and (username == "" or password == "" or system_instance is None or workspace_id == "" or target_directory == "")))):
    if audio is not None:
        recording = audio
    try:
        bpmn_generator = BPMNGenerator(recording, text, api_key)
        with col2:
            # call speech to text
            if not text:
                with st.spinner("Transforming speech to text"):
                    bpmn_generator.speech_to_text()
            # call twoshot
            with st.spinner("Generating the first BPMN version"):
                bpmn_generator.text_to_model()
            # call improvement
            with st.spinner("Improving the BPMN"):
                bpmn_generator.improve_model()
            # test completion
            with st.spinner("Checking the file for completeness"):
                complete = bpmn_generator.check_xml_completeness()
            # call completion
            if not complete:
                with st.spinner("BPMN needs to be completed"):
                    bpmn_di = bpmn_generator.generate_bpmn_di()
                    bpmn_generator.merge_bpmn_xml_diagram(bpmn_di)
            
            final_bpmn = bpmn_generator.get_bpmn()
            if isinstance(final_bpmn, ET.ElementTree):
                final_bpmn = ET.tostring(final_bpmn.getroot(), encoding="unicode")

            st.session_state["final_bpmn"] = final_bpmn
            st.session_state["visualization_ready"] = True

    except openai.AuthenticationError:
        col2.error("Your OpenAI API key is not valid. Make sure you are using the correct API key!")
        st.stop()
    except Exception as e:
        col2.error(f'An error occurred while processing your request: {e} Please re-run the model generation.')
        st.stop()

if st.session_state["visualization_ready"]:
    col2.success("BPMN complete")
    if viz == "SAP Signavio":
        with col2:
            final_bpmn = st.session_state["final_bpmn"]
            signavio_connector = SignavioConnector(system_instance, workspace_id, target_directory)
            try:
                with st.spinner("Authenticating SAP Signavio"):
                    signavio_connector.authenticate(username, password)
                with st.spinner("Importing the process model"):
                    signavio_connector.import_model(final_bpmn)
                st.success("Process model imported into SAP Signavio")
                with st.spinner("Displaying the process model"):
                    png = signavio_connector.export_model()
                st.image(BytesIO(png))
            except AuthenticationError as auth_err:
                st.error("An error occured during authentication: " + str(auth_err))
                st.info("Switching to visualisation with bpmn.io")
                viz = "bpmn.io"
            except UploadError as up_err:
                st.error("An error occured during the upload of your model: " + str(up_err))
                st.info("Switching to visualisation with bpmn.io")
                viz = "bpmn.io"
            except ExportError as exp_err:
                st.error("An error occured displaying the process model with SAP Signavio: " + str(exp_err))
                st.info("Switching to visualisation with bpmn.io")
                viz = "bpmn.io"
            st.download_button(label="Download as XML", data=final_bpmn, file_name="process.bpmn", mime="application/xml")

    if viz == "bpmn.io":
        with col2:
            st.write("Click on the diagram canvas to scroll and navigate.")
            final_bpmn = st.session_state["final_bpmn"]
            escaped_bpmn = final_bpmn.replace("`", "\\`")

            components.html(
                f""" 
                <html>
                    <head>
                    <link rel="stylesheet" href="https://unpkg.com/bpmn-js@18.3.1/dist/assets/bpmn-js.css" />
                    <script src="https://unpkg.com/bpmn-js@18.3.1/dist/bpmn-navigated-viewer.development.js"></script>
                    <style>
                        #canvas {{
                            width: 100%;
                            height: 590px;
                            overflow: auto;
                            border-width: 2px;
                        }}
                    </style>
                    </head>
                    <body>
                        <div id="canvas"></div>
                        <script>
                            (async function(){{
                                var viewer = new BpmnJS({{ 
                                    container: '#canvas'
                                }});
                                var bpmn = `{escaped_bpmn}`;
                                try{{
                                    await viewer.importXML(bpmn);
                                    viewer.get('canvas').zoom('fit-viewport');
                                }}catch (err) {{
                                    console.error('something went wrong:', err);
                                }}
                            }})();
                        </script>
                    </body>
                </html
                """, height=600, scrolling=True)
            st.download_button(label="Download as XML", data=final_bpmn, file_name="process.bpmn", mime="application/xml")

footer_html="""
    <style>
    .footer {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background-color: #f0f2f6;
        padding: 10px;
        text-align: center;
        font-size: 0.8em;
        color: #6c757d;
        border-top: 1px solid #dee2e6;
    }
    </style>

    <div class="footer">
        <p>
            Developed 2025 by Alena Wimmer at TU Munich • Contact: <a href="mailto:alena.wimmer@tum.de">Email</a>
        </p>
    </div>
"""

st.markdown(footer_html, unsafe_allow_html=True)