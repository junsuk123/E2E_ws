# 🧠 AI Robot Programming Simulation - ROS2 Humble + Gazebo + YOLO + ResNet18 E2E

ROS2 Humble 
Gazebo 환경에서 TurtleBot3가 YOLO를 활용하여 객체 인식.
 ResNet18 기반 End-to-End 모델.

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

**설명**: Gazebo 시뮬레이터에서 TurtleBot3가 등장하며, `Insert` 탭을 톸더 적절한 객체(hydrant, ball 등 YOLO 학습된 대상)를 추가하세요.

---

### 🔍 2. YOLOv8 객체 인식 (Segmentation) 노드 실행

```bash
ros2 launch yolo_bringup yolov11n_seg.launch.py
```

**설명**: 'YOLOv11n_seg` 모델을 사용해 객체 검증과 함께 **segmentation mask** 정보를 출력합니다.  
카메라 이미지로부터 인식된 객체 정보를 `/yolo/detections` 통크로 퍼블리시합니다.

**결과 확인**:

```bash
ros2 topic echo /yolo/detections
```

---

### 🖼️ 3. 이미지 변환 노드 실행 

```bash
ros2 launch image_fusion image_fusion_launch.py
```

**설명**: YOLO 결과와 실제 이미지를 fusion. `/fused_image` topic 시각화된 이미지를 퍼블리시합니다.

**결과 확인**:

```bash
ros2 topic echo /fused_image
```

---

### 🎯 4. ResNet18 E2E 모델 실행

#### 📦 학습 (Training)

```bash
ros2 launch resnet_control train.launch.py
```

**설명**: YOLO 인식 결과를 바탕으로 ResNet18 모델을 학습해 주회 명령(`cmd_vel`)을 예측하도록 합니다.  
학습된 모델은 `.pth` 형태로 저장되며, 추후 inference에서 자동 로드됩니다.

> 학습은 로컬이 아닌 **Kaggle Cloud GPU 환경**에서 수행하며, 학습 로그 및 결과는 공유 폴더(`models/`)에 저장됩니다.

#### ⚙️ 추론 (Inference)

```bash
ros2 launch resnet_control inference.launch.py
```

**설명**: 가장 최강에 저장된 모델을 보내여, 실시간 입력 이미지에 대해 제어 명령을 생성합니다.

> 📌 현재 추론 결과에서 **좌우 방향 제어가 반대로 나오는 문제**가 있어, 원인 발견 및 수정 중입니다.

---

### ⌨️ 5. 키보드 텔레오퍼리언션 (teleop twist keyboard)

```bash
sudo apt install ros-humble-teleop-twist-keyboard
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

**설명**: 키보드 방향키를 이용해 직접 TurtleBot3를 조작하며, 학습 데이터 수집 또는 제어 비교 시험 등에 활용할 수 있습니다.

---

## 🎥 시연 영상

[📹 시연 영상 보러가기](https://github.com/user-attachments/assets/1cb8c2a7-1c54-4de1-b77a-f901b61126b3)

---

## 📌 참고 사항

- YOLOv8은 GPU에서 최적 성능을 밟지만, CPU 환경에서도 실행 가능
- 학습 모델은 `install/resnet_control/share/resnet_control/model/`가이드에 저장됨
- 추론 시 가장 최신 `.pth` 모델을 자동 선택 로드
- Gazebo의 카메라 센서는 `<sensor type="camera">`형식으로 구성되어야 하며, `/camera_info` 통크 발행이 필요

---

## 🧑‍💻 Maintainer

- **김준석**  
- ✉️ [bob4587@naver.com](mailto:bob4587@naver.com)  
- GitHub: [junsuk123](https://github.com/junsuk123)
