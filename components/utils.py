import re
import json

MAX_SIZE_MB = 25

def extract_xml_content(response):
    xml_pattern = r"<\?xml.*?>.*</.*?>" #r"<\?xml.*?>.*?</.*?>" 
    match = re.search(xml_pattern, response, re.DOTALL)
    
    if match:
        return match.group(0)
    else:
        print("No valid xml in gpt response!")
        return ""
    
def extract_xml_diagram_content(response):
    xml_diagram_pattern = r"(<bpmndi:BPMNDiagram[\s\S]*?</bpmndi:BPMNDiagram>)"
    match = re.search(xml_diagram_pattern, response, re.DOTALL)
    if match:
        return match.group(1)
    else:
        print("No valid BPMN DI part")
        return ""

def extract_json_content(response):
    json_pattern = r"\{.*\}"
    match = re.search(json_pattern, response, re.DOTALL)
    if match:
        json_text = match.group(0)
        return json.loads(json_text)
    else:
        return ""
