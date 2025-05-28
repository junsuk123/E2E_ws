#!/usr/bin/env python3
import math
import numpy as np
import cv2
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Image
from yolo_msgs.msg import DetectionArray
from cv_bridge import CvBridge

def quaternion_to_yaw(qx, qy, qz, qw):
    return math.atan2(2.0*(qw*qz + qx*qy),
                      1.0 - 2.0*(qy*qy + qz*qz))

class ImageFusionNode(Node):
    def __init__(self):
        super().__init__('image_fusion_node')
        self.bridge      = CvBridge()
        self.odom        = None
        self.seg_mask    = None
        self.tracking    = None

        # 퍼블리셔
        self.pub = self.create_publisher(Image, 'fused_image', 10)

        # 구독자
        self.create_subscription(Odometry, 'odom', self.odom_cb, 10)
        self.create_subscription(DetectionArray, 'yolo/tracking',
                                 self.tracking_cb, 10)
        self.create_subscription(Image, 'segmentation_mask',
                                 self.segmentation_cb, 10)

        rate = self.declare_parameter('update_rate', 10.0).value
        self.create_timer(1.0 / rate, self.timer_cb)

    def odom_cb(self, msg: Odometry):
        self.odom = msg

    def segmentation_cb(self, msg: Image):
        # Mono8 마스크를 numpy 배열로
        self.seg_mask = self.bridge.imgmsg_to_cv2(msg, 'mono8')

    def tracking_cb(self, msg: DetectionArray):
        self.tracking = msg

    def timer_cb(self):
        # 1) 빈 캔버스
        img = np.zeros((240, 320, 3), dtype=np.uint8)
        # 3) /yolo/tracking 결과 이용한 Bounding Box
        if self.tracking is not None:
            scale_x, scale_y = 0.5, 0.5
            for det in self.tracking.detections:
                if det.score < 0.5:
                    continue
                # road 클래스: det.mask.data 로 폴리곤 채움
                if det.class_name == 'road' and det.mask.data:
                    # Point2D 리스트 → Nx2 numpy int32 배열
                    pts = np.array([
                        [int(pt.x * scale_x), int(pt.y * scale_y)]
                        for pt in det.mask.data
                    ], dtype=np.int32)
                    # 반드시 (N,1,2) 형태로 reshape
                    pts = pts.reshape(-1, 1, 2)
                    cv2.fillPoly(img, [pts], (255, 0, 0))  # BGR 파랑

                # 그 외 클래스: 녹색 테두리 바운딩 박스
                else:
                    cx = int(det.bbox.center.position.x * scale_x)
                    cy = int(det.bbox.center.position.y * scale_y)
                    w  = int(det.bbox.size.x  * scale_x)
                    h  = int(det.bbox.size.y  * scale_y)
                    x0 = max(0, cx - w//2)
                    y0 = max(0, cy - h//2)
                    cv2.rectangle(
                        img,
                        (x0, y0),
                        (x0 + w, y0 + h),
                        (0, 255, 0),  # BGR 초록
                        thickness=2
                    )



        # 4) 자세 화살표 (보라색)
        if self.odom is not None:
            pts = np.array([[0, -30], [-15, 10], [15, 10]], np.float32)
            q   = self.odom.pose.pose.orientation
            yaw = -quaternion_to_yaw(q.x, q.y, q.z, q.w)
            R   = np.array([[math.cos(yaw), -math.sin(yaw)],
                            [math.sin(yaw),  math.cos(yaw)]], np.float32)
            rot = np.dot(pts, R.T).astype(np.int32)
            base = np.array([160, 200], np.int32)
            tri_pts = (rot + base).reshape((-1,1,2))
            cv2.fillPoly(img, [tri_pts], (255, 0, 255))

        # 5) 퍼블리시
        out = self.bridge.cv2_to_imgmsg(img, encoding='bgr8')
        out.header.stamp = self.get_clock().now().to_msg()
        self.pub.publish(out)

def main(args=None):
    rclpy.init(args=args)
    node = ImageFusionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
