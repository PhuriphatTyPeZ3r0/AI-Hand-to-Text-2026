import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from tf_keras.models import load_model
import numpy as np
import time

# --- ตั้งค่า MediaPipe Hand Landmarker (Tasks API ใหม่) ---
base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    num_hands=1,
    running_mode=vision.RunningMode.VIDEO
)
landmarker = vision.HandLandmarker.create_from_options(options)

cap = cv2.VideoCapture(0)
classes = ['Hello', 'Good Luck', 'I Love You', 'Yes', 'No']

model = load_model('converted_keras/keras_model.h5')
data = np.ndarray(shape=(1, 224, 224, 3), dtype=np.float32)

frame_timestamp_ms = 0

while True:
    success, img = cap.read()
    if not success:
        continue

    h, w, _ = img.shape
    frameRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frameRGB)

    # ใช้ timestamp ที่เพิ่มขึ้นเรื่อยๆ สำหรับ VIDEO mode
    frame_timestamp_ms += 33  # ~30 FPS
    results = landmarker.detect_for_video(mp_image, frame_timestamp_ms)

    if results.hand_landmarks:
        for hand_landmarks in results.hand_landmarks:
            x_max = 0
            y_max = 0
            x_min = w
            y_min = h

            # --- ส่วนที่ 1: หาจุดขอบเขตของมือ (Bounding Box) ---
            for lm in hand_landmarks:
                x, y = int(lm.x * w), int(lm.y * h)
                if x > x_max: x_max = x
                if x < x_min: x_min = x
                if y > y_max: y_max = y
                if y < y_min: y_min = y

            # เผื่อพื้นที่กรอบ (Padding) เพื่อไม่ให้ตัดภาพชิดมือเกินไป
            y_min = max(0, y_min - 20)
            y_max = min(h, y_max + 20)
            x_min = max(0, x_min - 20)
            x_max = min(w, x_max + 20)

            try:
                # --- ส่วนที่ 2: ตัดภาพและเตรียมข้อมูลเข้า Model ---
                imgCrop = img[y_min:y_max, x_min:x_max]
                imgResize = cv2.resize(imgCrop, (224, 224))

                # แปลงค่าสีภาพให้อยู่ในช่วง -1 ถึง 1 (มาตรฐานของ Teachable Machine)
                image_array = np.asarray(imgResize)
                normalized_image_array = (image_array.astype(np.float32) / 127.0) - 1
                data[0] = normalized_image_array

                # --- ส่วนที่ 3: ทำนายผลลัพธ์ ---
                prediction = model.predict(data, verbose=0)
                index = np.argmax(prediction)
                className = classes[index]
                confidenceScore = prediction[0][index]

                # --- ส่วนที่ 4: วาดผลลัพธ์ลงบนภาพ ---
                cv2.rectangle(img, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)
                cv2.putText(img, f'{className} ({int(confidenceScore * 100)}%)',
                            (x_min, y_min - 10), cv2.FONT_HERSHEY_SIMPLEX,
                            0.8, (255, 0, 255), 2)

            except Exception as e:
                # ป้องกัน error กรณีที่มืออยู่ขอบจอเกินไปจนคำนวณ Crop ล้มเหลว
                pass

    # แสดงผลภาพ
    cv2.imshow("Hand Sign Detection", img)

    # กดปุ่ม 'q' เพื่อออกจากโปรแกรม
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# คืนค่าทรัพยากรทั้งหมด
landmarker.close()
cap.release()
cv2.destroyAllWindows()