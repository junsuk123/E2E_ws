from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import os
import xacro
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    pkg_share = get_package_share_directory('my_robot_description')

    # 1) 인자 선언
    declare_world_arg = DeclareLaunchArgument(
        'world',
        default_value=os.path.join(pkg_share, 'worlds', 'AI_Center3.world'),
        description='Gazebo world file to load'
    )
    declare_x_arg = DeclareLaunchArgument('x_pose', default_value='0.0',  description='Spawn X')
    declare_y_arg = DeclareLaunchArgument('y_pose', default_value='-1.4', description='Spawn Y')
    declare_z_arg = DeclareLaunchArgument('z_pose', default_value='0.0',  description='Spawn Z')

    # 2) LaunchConfiguration 객체
    world  = LaunchConfiguration('world')
    x_pose = LaunchConfiguration('x_pose')
    y_pose = LaunchConfiguration('y_pose')
    z_pose = LaunchConfiguration('z_pose')

    # 3) xacro → URDF
    xacro_file = os.path.join(pkg_share, 'urdf', 'robot_core.xacro')
    robot_description_config = xacro.process_file(xacro_file).toxml()

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

        # robot_state_publisher (URDF 퍼블리시)
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

        # spawn_entity.py (한 번만)
        Node(
            package='gazebo_ros',
            executable='spawn_entity.py',
            arguments=[
                '-topic',  'robot_description',
                '-entity', 'my_mobile',
                '-x',      x_pose,
                '-y',      y_pose,
                '-z',      z_pose
            ],
            output='screen'
        ),
    ])
