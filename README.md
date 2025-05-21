# 🧠 AI Robot Programming Simulation - ROS2 Humble + Gazebo + YOLO + ArUco

ROS2 Humble 기반의 AI 로봇 프로젝트 시뮬레이션 환경입니다.  
Gazebo 환경에서 TurtleBot3가 ArUco 마커와 YOLO 객체를 동시에 인식합니다.

---

## 📁 프로젝트 구조

```
e2e_ws/
├── src/
├── install/ (ignored)
├── build/   (ignored)
└── README.md
```

---

## ⚙️ 설치 방법 (Ubuntu 22.04 + ROS2 Humble)

```bash
git clone https://github.com/junsuk123/e2e_ws.git
cd e2e_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

---

## 🚀 시뮬레이션 실행 방법

### 🐢 1. TurtleBot3 + Gazebo 실행

```bash
ros2 launch turtlebot3_gazebo turtlebot3_AICenter.launch.py
```

> Gazebo가 실행되면, `Insert` 탭을 눌러 적절한 물체 (예: 소화전, 공 등 YOLO 학습된 객체)를 삽입하세요.

---

### 🔍 2. YOLOv8 객체 인식 노드 실행

```bash
ros2 launch yolo_bringup yolov8.launch.py
```

#### 결과 확인

```bash
ros2 topic echo /yolo/detections
```

---

### 🎯 3. ArUco 마커 인식 노드 실행

```bash
ros2 launch ros2_aruco aruco_recognition.launch.py
```

#### 결과 확인

```bash
ros2 topic echo /aruco_markers     # ID 및 pose 정보
ros2 topic echo /aruco_poses       # geometry_msgs/PoseArray
```

---

## 🖼️ 시뮬레이션 예시

### ArUco 마커 인식 + YOLO 객체 탐지 (RViz)

![aruco yolo](./스크린샷%202025-05-21%2016-26-00.png)

### Gazebo 환경

![gazebo](./스크린샷%202025-05-21%2016-25-52.png)

---

## 🎥 시연 영상

▶️ [스크린캐스트 보기](./스크린캐스트%2005-21-2025%2004:26:44%20PM.webm)

---

## 📌 참고 사항

- YOLOv8은 기본적으로 GPU 환경에서 최적 동작하지만, CPU 환경에서도 실행은 가능함
- ArUco 마커의 `pose` 인식을 위해선 카메라 센서에서 `/camera_info`가 정확히 발행되어야 함
- Gazebo용 카메라 센서는 `<sensor type="camera">`로 설정되어야 RViz에서 왜곡 없는 시야 확보 가능

---

## 🧑‍💻 Maintainer

- **김준석**
- ✉️ [bob4587@naver.com](mailto:bob4587@naver.com)
- GitHub: [junsuk123](https://github.com/junsuk123)

---
