import cv2
from datetime import datetime, timedelta
import os

# ===== CẤU HÌNH =====
video_path = "lua.mp4"       # đường dẫn video
start_time_str = "2025-11-16_14-28-40"  # mốc thời gian bắt đầu đặt tên ảnh
interval_seconds = 1           # lấy 1 frame mỗi 5 giây
output_ratio = (4, 3)          # tỷ lệ ảnh 4:3
output_folder = "frames"       # thư mục lưu ảnh
# =====================

# Tạo thư mục nếu chưa tồn tại
os.makedirs(output_folder, exist_ok=True)

# Load video
cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
duration = total_frames / fps

print(f"FPS: {fps}, Tổng giây: {duration}")

# Thời gian nền để đặt tên file
base_time = datetime.strptime(start_time_str, "%Y-%m-%d_%H-%M-%S")

current_second = 0
image_count = 0

while current_second <= duration:
    frame_index = int(current_second * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)

    ret, frame = cap.read()
    if not ret:
        break

    # --- Cắt về tỷ lệ 4:3 ---
    h, w = frame.shape[:2]
    target_w, target_h = output_ratio

    desired_h = int(w * (target_h / target_w))
    if desired_h <= h:
        y1 = (h - desired_h) // 2
        frame = frame[y1:y1 + desired_h, :]
    else:
        desired_w = int(h * (target_w / target_h))
        x1 = (w - desired_w) // 2
        frame = frame[:, x1:x1 + desired_w]

    # Tạo tên ảnh theo ngày giờ
    new_time = base_time + timedelta(seconds=current_second)
    filename = new_time.strftime("%Y-%m-%d_%H-%M-%S.jpg")
    save_path = os.path.join(output_folder, filename)

    # Lưu ảnh
    cv2.imwrite(save_path, frame)
    print(f"Đã lưu: {save_path}")

    # Tăng thời gian
    current_second += interval_seconds
    image_count += 1

cap.release()
print(f"✅ Hoàn thành! Đã lưu {image_count} ảnh trong thư mục '{output_folder}'.")
