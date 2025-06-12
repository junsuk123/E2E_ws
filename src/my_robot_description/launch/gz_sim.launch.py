from launch import LaunchDescription
from launch.actions import ExecuteProcess, DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
def generate_launch_description():
    # ② world 인자 선언 & LaunchConfiguration 객체 생성
    declare_world_arg = DeclareLaunchArgument(
        'world',
        default_value='',
        description='Path to the Gazebo world file'
    )
    world = LaunchConfiguration('world')
    return LaunchDescription([
        declare_world_arg,
        ExecuteProcess(
            cmd=[
                'gazebo',
                '--verbose',
                '-s', 'libgazebo_ros_factory.so',
                world                                     # <--- world 인자 사용
            ],
            output='screen'
        )
    ])
