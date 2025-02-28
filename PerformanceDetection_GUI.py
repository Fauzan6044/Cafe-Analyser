import cv2
from ultralytics import YOLO #YOLO v11 automatically picks GPU Hardware acceleration if PyTorch is set.
import pandas as pd
import cvzone
import numpy as np
import time
from collections import OrderedDict
import queue
import os
import shutil
import subprocess

# Create a queue to send data to the GUI (declare it globally)
counter1_queue = queue.Queue()
counter2_queue = queue.Queue()
def run_analysis(input_filepath, output_file_name, check_person, check_arcup, check_cup, check_preview, staff1_n, staff2_n):
    model = YOLO('yolov8x_custom1.pt') #v8x -> highest accuracy at the cost of performance -> RTX 3060 = 30ms avg. per frame
    #model.iou = 0.6  # Adjust IoU threshold (higher value merges more aggressively)
    #model.conf = 0.4  # Adjust confidence threshold (lower value keeps more detections)

    cap = cv2.VideoCapture(input_filepath) #input video name
    # with open("new_coco.txt", "r") as file:
    #     class_list = file.read().split("\n")
    class_list = ["Cups", "Customer", "Staff"]
    fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
    original_fps = cap.get(cv2.CAP_PROP_FPS)
    output_file = output_file_name + ".mp4"
    out = cv2.VideoWriter(output_file, fourcc, original_fps, (1920, 1080)) #output video name, fps_limit and video resolution -> has to match with OpenCV's Capture (object = frame)

    area1 = [(580, 545), (660, 545), (660, 640), (580, 640)] #sets coordinates for Area 1
    area2 = [(580, 642), (660, 642), (660, 730), (580, 730)] #sets coordinates for Area 2
    entrance_area1 = [(700, 980), (1250,980), (1250, 1050), (700,1050)] #Entrance Area 1
    entrance_area2 = [(700, 800), (1250,800), (1250, 960), (700, 960)] #Entrance Area 2
    cooldown_time1 = 35 #adjusts cooldown of Staff#1
    cooldown_time2 = 25 #adjusts cooldown of Staff#2
    #cooldown_time = 19 <-- previous Global Cooldown - redundant code
    counter1 = 0
    counter2 = 0
    cd_trigger = False
    last_trigger_time = 0
    a1_active = -1
    cust_count = 0
    cust_cooldown = 4
    customer_detection = None
    last_cup_detection1 = None
    last_cup_detection2 = None
    last_cup_detection = {}

    #related to staff and customer count in if'person' in c:
    staff_count = 0
    customer_count = 0
    person_centroids = OrderedDict() # Maintain order of customer entry
    person_labels = OrderedDict()
    person_counter = {}
    elapsed_time = {}
    timer = 0



    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame=cv2.resize(frame,(1920,1080))
        results = model.predict(frame, half= True, iou=0.5, conf=0.7)
        a = results[0].boxes.data.cpu()
        px = pd.DataFrame(a).astype("float")

        for index, row in px.iterrows():
            x1 = int(row[0])
            y1 = int(row[1])
            x2 = int(row[2])
            y2 = int(row[3])
            d = int(row[5])
        
            c = class_list[d]
            if c in ["Staff", "Customer"]:
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2

                # Association logic (similar to your code)
                min_distance = float('inf')
                closest_person_id = None
                for person_id, centroid in person_centroids.items():
                    #print("person_id", person_id)
                    distance = np.sqrt((centroid[0] - center_x)**2 + (centroid[1] - center_y)**2)
                    if distance < min_distance:
                        min_distance = distance
                        closest_person_id = person_id
                # If close enough, associate with existing person, otherwise create new
                
                if min_distance < 100:
                    person_centroids[closest_person_id] = (center_x, center_y)
                    person_id = closest_person_id
                    #print("person_id", person_id)
                    if person_id not in elapsed_time:
                        elapsed_time[person_id] = 0
                    else:
                        if(c == "Customer"):
                            person_labels[person_id] = f"{c} {elapsed_time[person_id]: .2f}s"
                        elapsed_time[person_id] += 1/original_fps

                else:
                    person_centroids[len(person_centroids)] = (center_x, center_y)  # Use len for new IDs
                    person_id = len(person_centroids) - 1

                    if c == "Staff":
                        staff_count += 1
                        person_labels[person_id] = f"{c} {staff_count}"
                    else:
   
                        person_labels[person_id] = f"{c} Time: s"

                if check_person.get() == 1:

                    if (cv2.pointPolygonTest(np.array(entrance_area1, np.int32), (x2, y2), False) == 1):
                        # Reset timer if the customer enters entrance_area1
                        elapsed_time[person_id] = 0
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), 2)
                    cv2.circle(frame,(x2,y2),4,(255,0,255),-1) #Detection point for the person, visualized.
                cv2.putText(frame, person_labels[person_id], (x1, y1), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                # Check if the customer is in entrance_area1

                
                res_a1 = cv2.pointPolygonTest(np.array(entrance_area1, np.int32), (x2, y2), False)
                res_a2 = cv2.pointPolygonTest(np.array(entrance_area2, np.int32), (x2, y2), False)
                current_time = time.time()
                if(res_a1==1):
                    cd_trigger = True
                    last_trigger_time = time.time()
                if (cd_trigger == True and time.time() - last_trigger_time < 5):
                    a1_active = 1
                else:
                    a1_active = -1
                if customer_detection is None or (current_time - customer_detection) >= cust_cooldown:
                    if (a1_active == 1 and res_a2 == 1):
                        cust_count += 1
                        customer_detection = current_time
                
            if c == "Cups": # For Detecting cups in the frame + cup counter logic
                current_time = time.time()
                
                result = cv2.pointPolygonTest(np.array(area1, np.int32), (x2, y2), False)
                if(result==1):
                    if last_cup_detection1 is None or (current_time - last_cup_detection1) >= cooldown_time1: #cooldown logic for Staff #1
                        counter1 += 1
                        last_cup_detection1 = current_time
                        counter1_queue.put(counter1)
                else:
                    result2 =  cv2.pointPolygonTest(np.array(area2, np.int32), (x2, y2), False)
                    if(result2==1):
                        if last_cup_detection2 is None or (current_time - last_cup_detection2) >= cooldown_time2: #cooldown logic for Staff #2
                            counter2 += 1
                            last_cup_detection2 = current_time
                            counter2_queue.put(counter2)
                if (check_cup.get() == 1):
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), 2)    
                    cvzone.putTextRect(frame, "cup", (x1, y1), 1, 1)
                    cv2.circle(frame,(x2,y2),4,(255,0,255),-1) #Detection point for the cup, visualized.
                    

        #Staff Cup-Counter
        cv2.putText(frame, f"Cups Served by {staff1_n}: {counter2}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, f"Cups Served by {staff2_n}: {counter1}", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, f"Total Customers Visited: {cust_count}", (1440, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

        #Staff Area Detection -> with visuals
        if (check_arcup.get() == 1):
            cv2.polylines(frame,[np.array(area1, np.int32)],True,(0,255,0),1) #set to false to hide area of Staff #1
            cv2.polylines(frame,[np.array(area2, np.int32)],True,(0,0,255),1) #set to false to hide area of Staff #2
            cv2.polylines(frame,[np.array(entrance_area1, np.int32)],True,(225,0,225),1)
            cv2.polylines(frame,[np.array(entrance_area2, np.int32)],True,(225,225,0),1)
        if (check_preview.get() == 1):    
            cv2.imshow("Cafe Analyzer", frame)

        if cv2.waitKey(1)&0xFF==27:
            break

        out.write(frame)

    cap.release()
    out.release()
    move_output_to_folder(output_file_name)
    cv2.destroyAllWindows()
    print("Successfully Processed")

def compress_video_lossless(input_filep, output_filep, crf=18, speed=1.0):
    # """Compresses an MP4 video using FFmpeg with lossless settings.

    # Args:
    #     input_filepath (str): Path to the input video file.
    #     output_filepath (str): Path to save the compressed video.
    #     crf (int, optional): Constant Rate Factor for video quality (lower values are higher quality). Default is 18, which is visually lossless for most videos.
    # """
    try:
        # Detect hardware acceleration capabilities (same as before)
        probe_command = ['ffmpeg', '-hide_banner', '-hwaccels']
        probe_result = subprocess.run(probe_command, capture_output=True, text=True)
        available_hwaccels = probe_result.stdout.splitlines()

        hwaccel = None
        encoder = 'libx265'  # Default to software encoder
        if 'cuda' in available_hwaccels:
            hwaccel = 'cuda'
            encoder = 'hevc_nvenc'  # NVIDIA GPU H.265 encoder
        elif 'qsv' in available_hwaccels:
            hwaccel = 'qsv'
            encoder = 'hevc_qsv'  # Intel GPU H.265 encoder
        elif 'vaapi' in available_hwaccels or 'drm' in available_hwaccels:
            hwaccel = 'vaapi'
            encoder = 'hevc_vaapi'  # AMD or Intel GPU H.265 encoder

        # Construct FFmpeg command with speedup
        command = [
            'ffmpeg', '-hwaccel', hwaccel, '-hwaccel_device', '0',
            '-i', input_filep,
            '-c:v', encoder, '-crf', str(crf),
            '-preset', 'medium',
            '-filter:v', f"setpts={1.0/speed}*PTS",  # Speedup video
            '-an',  # Remove original audio (since it won't match the sped-up video)
            output_filep
        ]
        subprocess.run(command, check=True)
        print(f"Video compressed and sped up successfully! Saved to {output_filep}")
    except subprocess.CalledProcessError as e:
        print(f"Error compressing/speeding up video: {e}")


def move_output_to_folder(output_file_name):
    script_dir = os.path.dirname(os.path.realpath(__file__))
    output_folder = os.path.join(script_dir, "Output")
    output_file_path = os.path.join(script_dir, output_file_name + ".mp4")
    new_output_path = os.path.join(output_folder, output_file_name + ".mp4")
    
    # Check if Output folder exists, if not, create it
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    try:
        compress_video_lossless(output_file_path, new_output_path, crf=18, speed=2.5)
        #shutil.move(output_file_path, new_output_path)
        print(f"Moved output file to: {new_output_path}")
        
    except FileNotFoundError:
        print(f"Output file not found at: {output_file_path}")
    except Exception as e:
        print(f"Error moving file: {e}")