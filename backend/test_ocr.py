import os
import sys
from PIL import Image
import cv2
import numpy as np

print("Python executable:", sys.executable)

img_paths = [
    r"D:\CareAI\backend\media\prescriptions\ChatGPT_Image_Sep_22_2026_02_46_51_PM.png",
    r"D:\CareAI\backend\media\prescriptions\WhatsApp_Image_2026-09-22_at_3.31.57_PM.jpeg"
]

for p in img_paths:
    if not os.path.exists(p):
        print(f"File not found: {p}")
        continue
    
    print("\n" + "="*50)
    print(f"Testing image: {p}")
    print(f"File size: {os.path.getsize(p)} bytes")
    
    # Step 2: PIL & OpenCV inspection
    try:
        pil_img = Image.open(p)
        print(f"[PIL] Size: {pil_img.size} (width={pil_img.width}, height={pil_img.height}), Mode: {pil_img.mode}")
    except Exception as e:
        print(f"[PIL] Failed to open: {e}")
        
    try:
        cv_img = cv2.imread(p)
        print(f"[OpenCV] Shape: {cv_img.shape if cv_img is not None else 'None'}")
    except Exception as e:
        print(f"[OpenCV] Failed to open: {e}")

    # Step 3: Run EasyOCR
    print("[EasyOCR] Initializing reader...")
    try:
        import easyocr
        reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        results = reader.readtext(p)
        print(f"[EasyOCR] Results count: {len(results)}")
        for bbox, text, conf in results:
            print(f"  - Conf: {conf:.2f} | Text: {text}")
    except Exception as e:
        print(f"[EasyOCR] Error: {e}")
