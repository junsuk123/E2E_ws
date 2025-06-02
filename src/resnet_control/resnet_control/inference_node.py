#!/usr/bin/env python3
import os
import rclpy
import torch
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import Twist
from cv_bridge import CvBridge
from torchvision.transforms import Compose, ToPILImage, Resize, ToTensor
from torchvision.models import resnet50, ResNet50_Weights
from ament_index_python.packages import get_package_share_directory

class InferenceNode(Node):
    def __init__(self):
        super().__init__('resnet_inference')

        # CV bridge
        self.bridge = CvBridge()

        # 1) 모델 파일 검색 (절대 경로 → ~/erp_ws/src/resnet_control/models)
        #    자신의 워크스페이스 이름(예: e2e_ws, erp_ws)에 맞춰 수정하세요.
        model_dir = os.path.join(
            os.path.expanduser('~/e2e_ws'),
            'src',
            'resnet_control',
            'models'
        )
        # pkg_root   = os.path.dirname(os.path.dirname(__file__))
        # model_dir = os.path.join(pkg_root, 'models')
        # share_dir = get_package_share_directory('resnet_control')
        # model_dir = os.path.join(share_dir, 'model')
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
        # 클래스 수를 실제 모델에 맞게 설정하세요 (예: 2)
        num_classes = 2
        self.model = resnet50(weights=None, num_classes=num_classes).to(self.device)
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.eval()
        self.get_logger().info(f"Loaded model: {model_path}")

        # 4) Transform 정의
        #    ToPILImage 으로 numpy.ndarray → PIL.Image 로 변환
        self.tf = Compose([
            ToPILImage(),            # numpy → PIL
            Resize((240, 320)),      # height, width
            ToTensor(),              # PIL → tensor, [0,1]
        ])

        # 5) 구독 (320×320 융합 이미지)
        self.create_subscription(
            Image,
            '/fused_image',
            self.cb_image,
            10
        )
        # 6) 발행 (/cmd_vel)
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)

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
    # 모델 로드 실패 시 node 존재 여부로 체크
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
