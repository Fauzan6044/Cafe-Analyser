import cv2
from ultralytics import YOLO #YOLO automatically picks GPU Hardware acceleration if PyTorch is set.
import pandas as pd
import cvzone
import numpy as np
import time
from filterpy.kalman import KalmanFilter
from collections import OrderedDict

model = YOLO('yolov8x.pt') #v8x -> highest accuracy at the cost of performance -> RTX 3060 = 30ms avg. per frame
#model.iou = 0.6  # Lower = More Captures
#model.conf = 0.4  # Higher = Stronger Detection

cap = cv2.VideoCapture('video_final.mp4') #input video name
with open("coco.txt", "r") as file:
    class_list = file.read().split("\n")
fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
original_fps = cap.get(cv2.CAP_PROP_FPS)
out = cv2.VideoWriter('output.mp4', fourcc, original_fps, (1920, 1080)) #output video name, fps_limit and video resolution -> has to match with OpenCV's Capture (object = frame)

area1 = [(580, 545), (660, 545), (660, 640), (580, 640)] #sets coordinates for Area 1
area2 = [(580, 642), (660, 642), (660, 730), (580, 730)] #sets coordinates for Area 2
cooldown_time1 = 35 #adjusts cooldown of Staff#1
cooldown_time2 = 25 #adjusts cooldown of Staff#2
#cooldown_time = 19 <-- previous Global Cooldown - redundant code
counter1 = 0
counter2 = 0
last_cup_detection1 = None
last_cup_detection2 = None
last_cup_detection = {}

#related to staff and customer count in if'person' in c:
staff_count = 0
customer_count = 0
person_centroids = OrderedDict() # Maintain order of customer entry
person_labels = OrderedDict()
person_counter = {}


while True:
    ret, frame = cap.read()
    if not ret:
        break
    frame=cv2.resize(frame,(1920,1080))
    results = model.predict(frame)
    a = results[0].boxes.data.cpu()
    px = pd.DataFrame(a).astype("float")

    for index, row in px.iterrows():
        x1 = int(row[0])
        y1 = int(row[1])
        x2 = int(row[2])
        y2 = int(row[3])
        d = int(row[5])
    
        c = class_list[d]
        if 'person' in c:
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2

            # Association logic (similar to your code)
            min_distance = float('inf')
            closest_person_id = None
            for person_id, centroid in person_centroids.items():
                distance = np.sqrt((centroid[0] - center_x)**2 + (centroid[1] - center_y)**2)
                if distance < min_distance:
                    min_distance = distance
                    closest_person_id = person_id

            # If close enough, associate with existing person, otherwise create new
            if min_distance < 100: 
                person_centroids[closest_person_id] = (center_x, center_y)
                person_id = closest_person_id
            else:
                person_centroids[len(person_centroids)] = (center_x, center_y)  # Use len for new IDs
                person_id = len(person_centroids) - 1 

                # Label assignment (changed for customers)
                if staff_count < 2:
                    person_labels[len(person_centroids) - 1] = f"staff {staff_count + 1}"
                    staff_count += 1
                else:
                    person_labels[len(person_centroids) - 1] = f"customer {customer_count + 1}"
                    customer_count += 1

            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), 2)
            cv2.putText(frame, person_labels[person_id], (x1, y1), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

            
        if 'cup' in c: # For Detecting cups in the frame + cup counter logic
            current_time = time.time()
            cvzone.putTextRect(frame, "cup", (x1, y1), 1, 1)
            result = cv2.pointPolygonTest(np.array(area1, np.int32), (x2, y2), False)
            if(result==1):
                if last_cup_detection1 is None or (current_time - last_cup_detection1) >= cooldown_time1: #cooldown logic for Staff #1
                    counter1 = counter1 + 1
                    last_cup_detection1 = current_time
            else:
                result2 =  cv2.pointPolygonTest(np.array(area2, np.int32), (x2, y2), False)
                if(result2==1):
                    if last_cup_detection2 is None or (current_time - last_cup_detection2) >= cooldown_time2: #cooldown logic for Staff #2
                        counter2 = counter2 + 1
                        last_cup_detection2 = current_time

            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), 2)    
            cv2.circle(frame,(x2,y2),4,(255,0,255),-1) #Detection point for the cup, visualized.


    #Staff Cup-Counter
    cv2.putText(frame, f"Cups Served by Farhan: {counter1}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(frame, f"Cups Served by Mannan: {counter2}", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

    #Staff Area Detection -> with visuals
    cv2.polylines(frame,[np.array(area1, np.int32)],True,(0,255,0),1) #set to false to hide area of Staff #1
    cv2.polylines(frame,[np.array(area2, np.int32)],True,(0,0,255),1) #set to false to hide area of Staff #2
    cv2.imshow("Cafe Analyzer", frame)

    if cv2.waitKey(1)&0xFF==27:
        break

    out.write(frame)

cap.release()
out.release()
cv2.destroyAllWindows()