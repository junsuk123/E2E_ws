from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
import os

def generate_launch_description():
    home_ws = os.path.expanduser('~/e2e_ws')
    # base directory for 모델 저장 위치
    base_model_dir = os.path.join(home_ws, 'src', 'e2e_control', 'models')
    # ① model_path 인자 선언 (외부에서 override 가능)
    declare_model_arg = DeclareLaunchArgument(
        'model_name',
        default_value='MobileNetV2_20250617_121056.pth',
        description='모델 파일 이름 (*.pth)'
    )
    return LaunchDescription([
        declare_model_arg,
        Node(
            package='e2e_control',
            executable='inference_node',
            name='e2e_inference',
            output='screen',
            # model_path 파라미터를 굳이 안 주어도,
            # 기본으로 설치된 패키지 내 최신 .pth 를 자동으로 로드합니다.
            # ② LaunchConfiguration 으로 인자 읽어오기
            parameters=[{
                # ② base_model_dir + "/" + model_name
                'model_path': PathJoinSubstitution([
                    base_model_dir,
                    LaunchConfiguration('model_name')
                ])
            }],
        ),
    ])
