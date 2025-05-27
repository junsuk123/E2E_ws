from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='resnet_control',
            executable='inference_node',
            name='resnet_inference',
            output='screen',
            # model_path 파라미터를 굳이 안 주어도,
            # 기본으로 설치된 패키지 내 최신 .pth 를 자동으로 로드합니다.
            parameters=[
                # {'model_path': '/custom/path/to/resnet_YYYYMMDD_HHMMSS.pth'},
            ],
        ),
    ])
