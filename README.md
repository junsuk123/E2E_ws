# 🧠 AI Robot Programming E2E

## ROS2 Humble + Gazebo + YOLO + MobileNetV2

**설명**
ROS2 Humble 기반 Gazebo 환경에서 `my_robot_description` 패키지를 이용해 커스텀 로봇 모델을 스폰하고, YOLO로 객체 인식한 뒤 MobileNetV2 End-to-End 모델로 주행 제어 명령을 생성합니다.

---

## 디렉터리 구조

```bash
E2E_ws/
├── src/            # ROS2 패키지 소스 코드 (my_robot_description, yolo_ros, image_fusion, data_collector, e2e_control 등)
├── install/        # (ignored)
├── build/          # (ignored)
└── README.md       # 프로젝트 설명
```

---

## 설치 방법 (Ubuntu 22.04 + ROS2 Humble 기준)

```bash
git clone https://github.com/junsuk123/e2e_ws.git
cd e2e_ws
sudo apt update && sudo apt install -y python3-rosdep2
rosdep update
rosdep install --from-paths src --ignore-src -r -y --rosdistro humble
colcon build --symlink-install
source install/setup.bash
```

---

## 실행 순서

아래 7단계로 전체 파이프라인을 구동합니다.

### 1. my\_robot\_description + Gazebo

```bash
ros2 launch my_robot_description core.launch.py
```

* Gazebo에 커스텀 로봇 모델 스폰
* `/cmd_vel`(geometry\_msgs/Twist) 수신 → 로봇 구동
* `/odom`(nav\_msgs/Odometry) 발행

### 2. YOLOv11n\_seg 노드

```bash
ros2 launch yolo_ros yolov11n_seg.launch.py
```

* `/camera/image_raw`(sensor\_msgs/Image) 구독
* `/yolo/detections`, `/yolo/tracking`(DetectionArray) 발행

### 3. Image Fusion 노드

```bash
ros2 launch image_fusion image_fusion.launch.py
```

* `/yolo/tracking`, `/odom` 구독
* `/fused_image`(sensor\_msgs/Image) 발행

### 4. 데이터 수집 (Data Collector)

#### 4.1 Fused Image + Command 저장

```bash
ros2 launch data_collector data_collector.launch.py
```

* `/fused_image`, `/cmd_vel` 구독 → PNG + CSV 저장

#### 4.2 Camera Image 저장

```bash
ros2 launch data_collector image_collector.launch.py
```

* `/camera/image_raw` 구독 → 원본 이미지 저장 (PNG)

### 5. E2E Control - Training

```bash
ros2 launch e2e_control train.launch.py
```

* 수집된 데이터로 MobileNetV2 학습
* 학습된 `.pth` 모델 저장 및 백업

### 6. E2E Control - Inference

```bash
ros2 launch e2e_control inference.launch.py
```

* `/fused_image` 구독 → 속도·조향 예측 → `/cmd_vel` 발행

### 7. Teleop Twist Keyboard

```bash
sudo apt install -y ros-humble-teleop-twist-keyboard
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

* 키보드로 직접 주행 제어 (비교 실험용)

---

## Maintainer

* **김준석**
* ✉️ [bob4587@naver.com](mailto:bob4587@naver.com)
* GitHub: [junsuk123](https://github.com/junsuk123)
