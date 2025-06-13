from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    # World file 인자 선언
    declare_world_arg = DeclareLaunchArgument(
        'world',
        default_value='',
        description='Path to the Gazebo world file'
    )
    # 스폰 위치 인자 선언
    declare_x_arg = DeclareLaunchArgument(
        'x_pose',
        default_value='0.0',
        description='Spawn position X'
    )
    declare_y_arg = DeclareLaunchArgument(
        'y_pose',
        default_value='0.75',
        description='Spawn position Y'
    )
    declare_z_arg = DeclareLaunchArgument(
        'z_pose',
        default_value='0.0',
        description='Spawn position Z'
    )

    # LaunchConfiguration 객체 생성
    world  = LaunchConfiguration('world')
    x_pose = LaunchConfiguration('x_pose')
    y_pose = LaunchConfiguration('y_pose')
    z_pose = LaunchConfiguration('z_pose')

    return LaunchDescription([
        # 인자 등록
        declare_world_arg,
        declare_x_arg,
        declare_y_arg,
        declare_z_arg,

        # Gazebo 실행
        ExecuteProcess(
            cmd=[
                'gazebo', '--verbose',
                '-s', 'libgazebo_ros_factory.so',
                world
            ],
            output='screen'
        ),

        # spawn_entity.py를 사용해 로봇 스폰
        Node(
            package='gazebo_ros',
            executable='spawn_entity.py',
            arguments=[
                '-topic',  'robot_description',  # robot_state_publisher가 publish하는 토픽
                '-entity', 'my_mobile',          # Gazebo 내 엔티티 이름
                '-x',      x_pose,               # X 위치
                '-y',      y_pose,               # Y 위치
                '-z',      z_pose                # Z 위치
            ],
            output='screen'
        ),
    ])
