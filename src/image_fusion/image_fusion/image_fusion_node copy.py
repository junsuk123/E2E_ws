#!/usr/bin/env python3
import math
import numpy as np
import cv2
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Image
from yolo_msgs.msg import DetectionArray
from geometry_msgs.msg import Point
from cv_bridge import CvBridge

def quaternion_to_yaw(qx, qy, qz, qw):
    return math.atan2(
        2.0 * (qw*qz + qx*qy),
        1.0 - 2.0 * (qy*qy + qz*qz)
    )

class ImageFusionNode(Node):
    def __init__(self):
        super().__init__('image_fusion_node')
        self.bridge     = CvBridge()
        self.odom       = None
        self.detections = []  # 최신 DetectionArray

        # 퍼블리셔
        self.pub = self.create_publisher(Image, '/fused_image', 10)

        # 구독자
        self.create_subscription(Odometry,
                                 '/odom',
                                 self.odom_cb,
                                 10)
        self.create_subscription(DetectionArray,
                                 '/yolo/tracking',
                                 self.detections_cb,
                                 10)

        # 타이머 (10Hz)
        rate = self.declare_parameter('update_rate', 10.0).value
        self.create_timer(1.0 / rate, self.timer_cb)

    def odom_cb(self, msg: Odometry):
        self.odom = msg

    def detections_cb(self, msg: DetectionArray):
        # DetectionArray 메시지 전체 저장
        self.detections = msg.detections

    def timer_cb(self):
        # 1) 빈 캔버스 생성 (H=240, W=320)
        H, W = 240, 320
        img = np.zeros((H, W, 3), dtype=np.uint8)

        # 2) 각 detection 처리
        #    mask는 원본 영상 크기 (width=640, height=480) 기준
        scale_x = W / float(self.detections[0].mask.width) if self.detections else 1.0
        scale_y = H / float(self.detections[0].mask.height) if self.detections else 1.0

        for det in self.detections:
            if det.score < 0.5:
                continue
            cls = det.class_name.lower()

            # --- passageway: mask data polygon 채우기 (파랑) ---
            if cls == 'passageway' and det.mask.data:
                # det.mask.data: List[Point] (x,y) in 원본 이미지 픽셀 좌표
                pts = np.array([
                    [int(pt.x * scale_x), int(pt.y * scale_y)]
                    for pt in det.mask.data
                ], dtype=np.int32).reshape(-1, 1, 2)
                cv2.fillPoly(img, [pts], (255, 0, 0))
                continue

            # bounding box 좌표 계산 (center+size → x0,y0와 x1,y1)
            cx = det.bbox.center.position.x * scale_x
            cy = det.bbox.center.position.y * scale_y
            w  = det.bbox.size.x  * scale_x
            h  = det.bbox.size.y  * scale_y
            x0 = int(max(0, cx - w/2))
            y0 = int(max(0, cy - h/2))
            x1 = int(min(W, cx + w/2))
            y1 = int(min(H, cy + h/2))

            # --- person: 초록 박스 ---
            if cls == 'person':
                cv2.rectangle(img, (x0, y0), (x1, y1),
                              (0, 255, 0), 2)

            # --- red pillar: 빨강 박스 ---
            elif cls == 'red pillar':
                cv2.rectangle(img, (x0, y0), (x1, y1),
                              (0, 0, 255), 2)

            # 그 외 클래스는 무시

        # 3) 차량 자세 화살표 (보라)
        if self.odom:
            # 로컬 삼각형 좌표
            pts = np.array([[0, -30], [-15, 10], [15, 10]], np.float32)
            q   = self.odom.pose.pose.orientation
            yaw = -quaternion_to_yaw(q.x, q.y, q.z, q.w)
            R   = np.array([[ math.cos(yaw), -math.sin(yaw)],
                            [ math.sin(yaw),  math.cos(yaw)]], np.float32)
            rot = (pts @ R.T).astype(np.int32)
            base = np.array([W//2, H-40], np.int32)
            tri = (rot + base).reshape(-1,1,2)
            cv2.fillPoly(img, [tri], (255, 0, 255))

        # 4) 퍼블리시
        out = self.bridge.cv2_to_imgmsg(img, encoding='bgr8')
        out.header.stamp = self.get_clock().now().to_msg()
        self.pub.publish(out)

    def destroy_node(self):
        self.get_logger().info('Shutting down ImageFusionNode')
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = ImageFusionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
