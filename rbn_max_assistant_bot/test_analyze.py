import zipfile
import xml.etree.ElementTree as ET
import os
import re

def extract_text_from_pptx(pptx_path):
    if not os.path.exists(pptx_path):
        print(f"Error: {pptx_path} does not exist.")
        return



    print(f"Extracting text from: {os.path.basename(pptx_path)}")
    
    with zipfile.ZipFile(pptx_path, 'r') as zip_ref:
        # Get slide files list
        slide_files = [name for name in zip_ref.namelist() if re.match(r'ppt/slides/slide\d+\.xml', name)]
        # Sort slides numerically
        slide_files.sort(key=lambda x: int(re.findall(r'\d+', x)[0]))
        
        for slide_file in slide_files:
            slide_num = re.findall(r'\d+', slide_file)[0]
            print(f"\n--- SLIDE {slide_num} ---")
            
            xml_content = zip_ref.read(slide_file)
            root = ET.fromstring(xml_content)
            
            # Find all text elements <a:t>
            texts = []
            for elem in root.iter('{http://schemas.openxmlformats.org/drawingml/2006/main}t'):
                if elem.text:
                    texts.append(elem.text.strip())
            
            # Group or print texts
            if texts:
                print("\n".join(texts))
            else:
                print("[No text found on this slide]")

pptx_file = "/Users/verakoroleva/Desktop/vpn/rbn_max_assistant_bot/Упаковка ГАБ.pptx"
extract_text_from_pptx(pptx_file)
