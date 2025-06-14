# 🧠 AI Robot Programming E2E

## ROS2 Humble + Gazebo + YOLO + MobileNetV2

**설명**
ROS2 Humble 기반 Gazebo 환경에서 TurtleBot3가 YOLO를 이용해 객체 인식하고, MobileNetV2 기반 End-to-End 모델로 주행 제어 명령을 생성합니다.

---

## 디렉터리 구조

```bash
E2E_ws/
├── src/            # ROS2 패키지 소스 코드
├── install/        # (ignored)
├── build/          # (ignored)
└── README.md       # 프로젝트 설명
```

---

## 설치 방법 (Ubuntu 22.04 + ROS2 Humble 기준)

```bash
git clone https://github.com/junsuk123/e2e_ws.git
cd e2e_ws
sudo apt install python3-rosdep2 -y
rosdep update
rosdep install \
  --from-paths src --ignore-src -r -y \
  --rosdistro humble
colcon build --symlink-install
source install/setup.bash
```

---

## 시작 방법

### 1. TurtleBot3 + Gazebo 실행

```bash
ros2 launch turtlebot3_gazebo turtlebot3_AICenter.launch.py
```

* Gazebo에 커스텀 TurtleBot3 모델 스폰
* `/cmd_vel`(Twist) 수신 → 주행 제어
* `/odom`(Odometry) 발행

### 2. YOLOv11n\_seg 노드 실행

```bash
ros2 launch yolo_ros yolov11n_seg.launch.py
```

* `/camera/image_raw`(Image) 구독
* `/yolo/detections`, `/yolo/tracking`(DetectionArray) 발행

### 3. Image Fusion 실행

```bash
ros2 launch image_fusion image_fusion.launch.py
```

* `/yolo/tracking`, `/odom` 구독
* `/fused_image`(Image) 발행

### 4. 데이터 수집 노드 실행

#### 4.1 Fused Image + Command 저장

```bash
ros2 launch data_collector data_collector.launch.py
```

* `/fused_image`, `/cmd_vel` 구독 → PNG + CSV 저장

#### 4.2 Camera Image 저장

```bash
ros2 launch data_collector image_collector.launch.py
```

* `/camera/image_raw` 구독 → PNG 저장

### 5. E2E Control - Training

```bash
ros2 launch e2e_control train.launch.py
```

* 수집 데이터로 MobileNetV2 학습
* `.pth` 모델 저장 및 백업

### 6. E2E Control - Inference

```bash
ros2 launch e2e_control inference.launch.py
```

* `/fused_image` 구독 → `/cmd_vel` 예측 발행

### 7. Teleop Twist Keyboard

```bash
sudo apt install ros-humble-teleop-twist-keyboard -y
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

* 키보드로 주행 제어

---

## Maintainer

* **김준석**
* ✉️ [bob4587@naver.com](mailto:bob4587@naver.com)
* GitHub: [junsuk123](https://github.com/junsuk123)
