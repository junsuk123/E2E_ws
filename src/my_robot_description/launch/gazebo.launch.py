from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory
import os
import xacro
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    pkg_share = get_package_share_directory('my_robot_description')
    xacro_file = os.path.join(pkg_share, 'urdf', 'robot_core.xacro')

    # ① world 인자 선언 & LaunchConfiguration 객체 생성
    declare_world_arg = DeclareLaunchArgument(
        'world',
        default_value=os.path.join(
            pkg_share,
            'worlds', 'AI_Center3.world'),
        description='Gazebo world file to load'
    )
    world = LaunchConfiguration('world')

    # 여기서 xacro 파일을 파싱해서 URDF XML로 변환
    robot_description_config = xacro.process_file(xacro_file).toxml()
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    x_pose = LaunchConfiguration('x_pose', default='0.00')
    y_pose = LaunchConfiguration('y_pose', default='0.75')


    return LaunchDescription([
        declare_world_arg, 
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_share, 'launch', 'gz_sim.launch.py')
            ),
            launch_arguments={'world': world}.items()
        ),
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{
                'use_sim_time': True,
                'robot_description': robot_description_config
            }]
        ),
        ExecuteProcess(
            cmd=[
                'ros2', 'run', 'gazebo_ros', 'spawn_entity.py',
                '-topic', 'robot_description',
                '-entity', 'my_mobile'
            ],
            output='screen'
        )
    ])
