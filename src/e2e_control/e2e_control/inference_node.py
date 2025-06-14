#!/usr/bin/env python3
import os
import rclpy
import torch
import torch.nn as nn
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import Twist
from cv_bridge import CvBridge
from torchvision.transforms import Compose, ToPILImage, Resize, ToTensor
from torchvision.models import mobilenet_v2  # MobileNetV2 사용
from ament_index_python.packages import get_package_share_directory

class InferenceNode(Node):
    def __init__(self):
        super().__init__('mobilenet_inference')

        # CV bridge
        self.bridge = CvBridge()

        # 1) 모델 파일 검색 (절대 경로 → ~/e2e_ws/src/e2e_control/models)
        #    자신의 워크스페이스 이름(예: e2e_ws, erp_ws)에 맞춰 수정하세요.
        model_dir = os.path.join(
            os.path.expanduser('~/e2e_ws'),
            'src',
            'e2e_control',
            'models'
        )
        # .pth 파일 리스트
        candidates = sorted(f for f in os.listdir(model_dir) if f.endswith('.pth'))
        if not candidates:
            self.get_logger().error(f"No .pth model files in {model_dir}")
            rclpy.shutdown()
            return
        default_model = os.path.join(model_dir, candidates[-1])

        # 2) 모델 경로 파라미터 (수정 가능)
        model_path = self.declare_parameter('model_path', default_model).get_parameter_value().string_value
        if not os.path.isfile(model_path):
            self.get_logger().error(f"Model not found: {model_path}")
            rclpy.shutdown()
            return

        # 3) 장치 선택 & 모델 로드
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        # MobileNetV2 정의 (output: [steer, vel] → num_classes=2)
        base_model = mobilenet_v2(weights=None)  # pretrained=False와 동일
        # 분류기 부분을 새로 정의
        in_features = base_model.classifier[1].in_features  # 마지막 Linear 입력 채널 수
        base_model.classifier = nn.Sequential(
            nn.Dropout(p=0.2),
            nn.Linear(in_features, 2)  # 출력: [steer, vel]
        )
        self.model = base_model.to(self.device)

        # 학습된 .pth 체크포인트 로드
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.eval()
        self.get_logger().info(f"Loaded MobileNetV2 model: {model_path}")

        # 4) Transform 정의
        #    ToPILImage 으로 numpy.ndarray → PIL.Image 로 변환
        self.tf = Compose([
            ToPILImage(),            # numpy → PIL
            Resize((240, 320)),      # height, width (
            ToTensor(),              # PIL → tensor, [0,1]
        ])

        # 5) 구독 (320×320 융합 이미지)
        self.create_subscription(
            Image,
            '/fused_image',
            self.cb_image,
            30
        )
        # 6) 발행 (/cmd_vel)
        self.pub = self.create_publisher(Twist, '/cmd_vel', 30)

    def cb_image(self, msg: Image):
        # a) ROS Image → OpenCV (numpy.ndarray, BGR)
        cv_img = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

        # b) 전처리 & 배치 차원 추가
        #    transforms.ToPILImage() 덕분에 바로 처리 가능
        x = self.tf(cv_img).unsqueeze(0).to(self.device)

        # c) 추론
        with torch.no_grad():
            out = self.model(x).cpu().numpy()[0]

        # d) Twist 메시지에 매핑
        t = Twist()
        # out[1] → 선속도, out[0] → 조향각
        t.linear.x  = float(out[1])
        t.angular.z = float(out[0])

        # e) 퍼블리시
        self.pub.publish(t)
        self.get_logger().debug(f"Published cmd_vel: linear.x={t.linear.x:.3f}, angular.z={t.angular.z:.3f}")

def main(args=None):
    rclpy.init(args=args)
    node = InferenceNode()
    # 모델 로드 실패 시 node에 model 속성이 없음 → rclpy.shutdown() 호출됨
    if hasattr(node, 'model'):
        try:
            rclpy.spin(node)
        except KeyboardInterrupt:
            pass
        finally:
            node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
