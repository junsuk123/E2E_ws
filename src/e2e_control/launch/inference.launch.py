from launch import LaunchDescription
from launch_ros.actions import Node
import os

def generate_launch_description():
    home_ws = os.path.expanduser('~/e2e_ws')
    model_path = os.path.join(home_ws, 'src', 'e2e_control', 'models', 'federated_avg_model (1).pth')

    return LaunchDescription([
        Node(
            package='e2e_control',
            executable='inference_node',
            name='e2e_inference',
            output='screen',
            # model_path 파라미터를 굳이 안 주어도,
            # 기본으로 설치된 패키지 내 최신 .pth 를 자동으로 로드합니다.
            parameters=[
                {'model_path': model_path},
            ],
        ),
    ])
