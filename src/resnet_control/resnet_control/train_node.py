# mobilenet2_ros2_train.py
#!/usr/bin/env python3
#===============================================================================
# mobilenet2_ros2_train.py
#===============================================================================

import os
import csv
from datetime import datetime
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from torchvision.models import mobilenet_v2
from PIL import Image
from tqdm import tqdm

class RecursiveDriveDataset(Dataset):
    """
    root_dir 아래를 재귀적으로 탐색(os.walk)하여,
    'data.csv'를 발견한 모든 파일 경로를 모은 뒤, tqdm progress bar를 띄우며 샘플을 로드합니다.
    """
    def __init__(self, root_dir: str, transform=None):
        self.transform = transform
        self.samples = []

        if not os.path.isdir(root_dir):
            raise RuntimeError(f"Provided root_dir is not a directory: {root_dir}")

        # 1) 먼저 모든 data.csv 파일 경로를 수집
        csv_paths = []
        for dirpath, _, filenames in os.walk(root_dir):
            if 'data.csv' in filenames:
                csv_paths.append(os.path.join(dirpath, 'data.csv'))

        if len(csv_paths) == 0:
            raise RuntimeError(f"No data.csv files found under root_dir={root_dir}")

        # 2) tqdm progress bar를 사용해 CSV 파일별로 샘플을 읽어들임
        for csv_path in tqdm(csv_paths, desc="Loading dataset", unit="file"):
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    img_file = row.get('image_file', '').strip()
                    if img_file == '':
                        continue
                    img_path = os.path.join(os.path.dirname(csv_path), img_file)
                    if not os.path.isfile(img_path):
                        continue
                    try:
                        steer = float(row.get('angular_z', '0.0'))
                        vel   = float(row.get('linear_x', '0.0'))
                    except ValueError:
                        continue
                    self.samples.append((img_path,
                                         torch.tensor([steer, vel], dtype=torch.float32)))
        if len(self.samples) == 0:
            raise RuntimeError(f"No valid samples found under root_dir={root_dir} "
                               "(data.csv은 발견됐으나 유효한 이미지-레이블 쌍이 없습니다.)")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, label = self.samples[idx]
        image = Image.open(img_path).convert('RGB')
        if self.transform is not None:
            image = self.transform(image)
        return image, label


class MobileNetTrainNode(Node):
    def __init__(self):
        super().__init__('mobilenet2_train')

        # 1) ROS2 파라미터 선언
        #    package source 디렉토리 찾기 (src/resnet_control)
        pkg_src = os.path.dirname(os.path.dirname(__file__))

        self.declare_parameter('data_dir',
            os.path.join(pkg_src, 'dataset'))
        self.declare_parameter('pretrained_model',
            '')  # 기본값 빈 문자열 → 랜덤 초기화
        self.declare_parameter('model_save_dir',
            os.path.join(pkg_src, 'models'))
        self.declare_parameter('epochs', 36)
        self.declare_parameter('batch_size', 32)
        self.declare_parameter('learning_rate', 0.002)
        self.declare_parameter('tol', 0.01745)
        self.declare_parameter('num_workers', 1)

        # 파라미터 값 가져오기
        self.data_dir = self.get_parameter('data_dir').get_parameter_value().string_value
        self.pretrained_model = self.get_parameter('pretrained_model').get_parameter_value().string_value
        self.model_save_dir = self.get_parameter('model_save_dir').get_parameter_value().string_value
        epochs     = self.get_parameter('epochs').get_parameter_value().integer_value
        batch_size = self.get_parameter('batch_size').get_parameter_value().integer_value
        lr         = self.get_parameter('learning_rate').get_parameter_value().double_value
        tol        = self.get_parameter('tol').get_parameter_value().double_value
        num_workers = self.get_parameter('num_workers').get_parameter_value().integer_value

        # 2) 모델 저장 디렉토리 생성
        os.makedirs(self.model_save_dir, exist_ok=True)
        now_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.model_path = os.path.join(self.model_save_dir, f"MobileNetV2_{now_str}.pth")

        # 3) 디바이스 자동 설정 (외장 GPU가 없으면 CPU 사용)
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.get_logger().info(f'Using device: {self.device}')

        # 4) Dataset & DataLoader
        transform = transforms.Compose([
            transforms.Resize((240, 320)),
            transforms.ToTensor()
        ])
        try:
            dataset = RecursiveDriveDataset(self.data_dir, transform)
        except RuntimeError as e:
            self.get_logger().error(str(e))
            rclpy.shutdown()
            return

        self.get_logger().info(f"[Info] Total samples collected: {len(dataset)}")
        loader = DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=True,
            num_workers=num_workers,
            pin_memory=(self.device.type == 'cuda')
        )

        # 5) MobileNetV2 모델 정의 및 체크포인트 로드
        model = mobilenet_v2(weights=None)
        model.classifier = nn.Sequential(
            nn.Dropout(p=0.2),
            nn.Linear(model.last_channel, 2)
        )
        self.model = model.to(self.device)

        if self.pretrained_model:
            # 만약 pretrained_model 파라미터가 빈 문자열이 아니라면, src/models 폴더에서 찾음
            if not os.path.isabs(self.pretrained_model):
                pm_path = os.path.join(pkg_src, 'models', self.pretrained_model)
            else:
                pm_path = self.pretrained_model

            if os.path.isfile(pm_path):
                self.get_logger().info(f"Loading pretrained model from: {pm_path}")
                state_dict = torch.load(pm_path, map_location=self.device)
                try:
                    self.model.load_state_dict(state_dict)
                except RuntimeError as e:
                    self.get_logger().warning(f"load_state_dict failed: {e}")
                    self.model.load_state_dict(
                        {k: v for k, v in state_dict.items()
                         if k in self.model.state_dict() and self.model.state_dict()[k].size() == v.size()},
                        strict=False
                    )
            else:
                self.get_logger().warning(f"pretrained_model path invalid: {pm_path} (continue with random init)")

        # 6) Loss / Optimizer / Scheduler
        self.criterion = nn.MSELoss()
        self.optimizer = optim.Adam(self.model.parameters(), lr=lr)
        self.scheduler = optim.lr_scheduler.StepLR(self.optimizer, step_size=7, gamma=0.875)

        # 7) ROS2 퍼블리셔 (visualization)
        self.loss_pub = self.create_publisher(Float32, 'training/loss', 10)
        self.acc_pub  = self.create_publisher(Float32, 'training/accuracy', 10)
        self.lr_pub   = self.create_publisher(Float32, 'training/lr', 10)

        # 8) 학습 루프 시작 (인터럽트 시 체크포인트 저장)
        try:
            for epoch in range(1, epochs + 1):
                avg_loss, avg_acc = self.train_one_epoch(loader, tol, epoch)
                lr_now = self.scheduler.get_last_lr()[0]
                self.scheduler.step()

                self.get_logger().info(
                    f"Epoch {epoch}/{epochs} → loss={avg_loss:.4f}, acc={avg_acc:.4f}, lr={lr_now:.6f}"
                )
            # 정상 완료 시 최종 모델 저장
            torch.save(self.model.state_dict(), self.model_path)
            self.get_logger().info(f"Saved final model to: {self.model_path}")
        except KeyboardInterrupt:
            # 중단 시에도 중간 모델 저장
            tmp_path = self.model_path.replace('.pth', '_interrupted.pth')
            torch.save(self.model.state_dict(), tmp_path)
            self.get_logger().info(f"Training interrupted—saved intermediate model: {tmp_path}")
        finally:
            rclpy.shutdown()

    def train_one_epoch(self, loader, tol, epoch=None):
        self.model.train()
        total_loss = 0.0
        total_correct = 0
        total_samples = 0

        if epoch is not None:
            desc_str = f"Epoch {epoch}"
        else:
            desc_str = "Training"

        loop = tqdm(loader, desc=desc_str, unit="batch")

        for imgs, labels in loop:
            imgs, labels = imgs.to(self.device, non_blocking=True), labels.to(self.device, non_blocking=True)
            outputs = self.model(imgs)

            steer_clamped = torch.clamp(outputs[:, 0], min=-3.14159, max=3.14159)
            vel_clamped   = torch.clamp(outputs[:, 1], min=-1.5,    max=1.5)
            outputs_limited = torch.stack([steer_clamped, vel_clamped], dim=1)

            loss = self.criterion(outputs_limited, labels)

            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()

            total_loss += loss.item() * imgs.size(0)
            correct = ((torch.abs(outputs_limited - labels) < tol).all(dim=1)).sum().item()
            total_correct += correct
            total_samples += imgs.size(0)

            loop.set_postfix({
                "batch_loss": f"{loss.item():.4f}",
                "batch_acc":  f"{correct/imgs.size(0):.3f}"
            })

        avg_loss = total_loss / total_samples
        avg_acc  = total_correct / total_samples
        lr_now   = self.scheduler.get_last_lr()[0]

        # ROS2 퍼블리시
        self.loss_pub.publish(Float32(data=avg_loss))
        self.acc_pub.publish(Float32(data=avg_acc))
        self.lr_pub.publish(Float32(data=lr_now))

        return avg_loss, avg_acc


def main(args=None):
    rclpy.init(args=args)
    node = MobileNetTrainNode()
    # __init__ 내에서 학습 완료 또는 중단 시 shutdown 하므로 spin 필요 없음
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            node.destroy_node()
            rclpy.shutdown()


if __name__ == '__main__':
    main()
