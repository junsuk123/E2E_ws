# 🧠 AI Robot Programming E2E - ROS2 Humble + Gazebo + YOLO + MobileNetV2

ROS2 Humble 기반 Gazebo 환경에서 TurtleBot3가 YOLO를 활용하여 객체 인식하고, MobileNetV2 기반 End-to-End 모델로 주행 제어 명령을 생성합니다.

---

## 포맷코드 구조

```bash
e2e_ws/
├── src/
├── install/  (ignored)
├── build/    (ignored)
└── README.md
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

### 🐢 1. TurtleBot3 + Gazebo 환경 실행

```bash
ros2 launch turtlebot3_gazebo turtlebot3_AICenter.launch.py
```

Gazebo 시뮬레이터에 커스텀 TurtleBot3 모델이 스폰되며, `/cmd_vel` 토픽 수신 후 주행 제어, `/odom` 토픽 발행 기능이 포함됩니다.

### 🔍 2. YOLOv11n\_seg Segmentation 노드 실행

```bash
ros2 launch yolo_ros yolov11n_seg.launch.py
```

Segmentation mask가 포함된 `/yolo/detections` 정보를 퍼블리시하며, 도로 방향 정보 누락 문제를 해결하기 위해 기존 검출 모델을 확장하였습니다.

### 🖼️ 3. Image Fusion 노드 실행

```bash
ros2 launch image_fusion image_fusion.launch.py
```

`/yolo/tracking` 토픽과 `/odom` 토픽을 구독하여 바운딩 박스, 도로 마스크, 차량 속도·방향을 융합한 `/fused_image` 이미지를 퍼블리시합니다.

### 💾 4. 데이터 수집 노드 실행

1. Fused Image + Command 저장

```bash
ros2 launch data_collector data_collector.launch.py
```

`/fused_image`와 `/cmd_vel` 토픽을 각각 PNG와 CSV 형식으로 저장하며, 기록 날짜·시간 디렉토리에 1\~3분 간격 주행 데이터를 수집합니다.

2. Camera Image 저장

```bash
ros2 launch data_collector image_collector.launch.py
```

`/camera/image_raw` 토픽을 구독하여 YOLO 학습용 PNG 이미지 데이터를 저장합니다.

### 🎯 5. E2E Control - Training

```bash
ros2 launch e2e_control train.launch.py
```

수차례 데이터 수집과 학습을 반복하며, 기존 모델이 있으면 이어서 학습합니다. 완료된 모델은 `.pth`로 저장하고, 인터럽트 발생 시까지의 모델을 백업합니다.

### ⚙️ 6. E2E Control - Inference

```bash
ros2 launch e2e_control inference.launch.py
```

MobileNetV2 기반 모델이 `/fused_image` 입력을 받아 속도·조향 제어 명령을 예측하여 `/cmd_vel`로 발행합니다.

### ⌨️ 7. Teleop Twist Keyboard

```bash
sudo apt install ros-humble-teleop-twist-keyboard -y
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

키보드로 직접 주행 제어하며, 데이터 수집 또는 제어 성능 비교에 활용할 수 있습니다.

---

## Maintainer

* **김준석**
* ✉️ [bob4587@naver.com](mailto:bob4587@naver.com)
* GitHub: [junsuk123](https://github.com/junsuk123)
