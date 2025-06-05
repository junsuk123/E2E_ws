# mobilenet2_train_launch.py

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import os

def generate_launch_description():
    home_ws = os.path.expanduser('~/e2e_ws')

    # 1) Launch Arguments: 변경 가능한 파라미터들 선언
    data_dir_arg = DeclareLaunchArgument(
        'data_dir',
        default_value=os.path.join(home_ws, 'src', 'resnet_control', 'dataset'),
        description='Path to the workspace-relative dataset folder'
    )
    pretrained_model_arg = DeclareLaunchArgument(
        'pretrained_model',
        default_value=os.path.join(home_ws, 'src', 'resnet_control', 'models', 'model.pth'),
        description='Path to a pretrained .pth checkpoint (relative to models/ if empty)'
    )
    model_save_dir_arg = DeclareLaunchArgument(
        'model_save_dir',
        default_value=os.path.join(home_ws, 'src', 'resnet_control', 'models'),
        description='Directory where trained MobileNetV2 checkpoints will be saved'
    )
    epochs_arg = DeclareLaunchArgument(
        'epochs',
        default_value='100',
        description='Number of training epochs'
    )
    batch_size_arg = DeclareLaunchArgument(
        'batch_size',
        default_value='32',
        description='Batch size for training'
    )
    learning_rate_arg = DeclareLaunchArgument(
        'learning_rate',
        default_value='0.001',
        description='Initial learning rate'
    )
    tol_arg = DeclareLaunchArgument(
        'tol',
        default_value='0.01745',
        description='Tolerance for accuracy calculation (in radians)'
    )
    num_workers_arg = DeclareLaunchArgument(
        'num_workers',
        default_value='1',
        description='Number of DataLoader workers'
    )

    # 2) LaunchConfiguration으로 각 인자를 읽어옴
    data_dir = LaunchConfiguration('data_dir')
    pretrained_model = LaunchConfiguration('pretrained_model')
    model_save_dir = LaunchConfiguration('model_save_dir')
    epochs = LaunchConfiguration('epochs')
    batch_size = LaunchConfiguration('batch_size')
    learning_rate = LaunchConfiguration('learning_rate')
    tol = LaunchConfiguration('tol')
    num_workers = LaunchConfiguration('num_workers')

    # 3) Train Node 설정
    train_node = Node(
        package='resnet_control',     # 패키지 이름
        executable='train_node',      # train_node로 빌드된 실행파일
        name='train_node',
        output='screen',
        emulate_tty=True,             # tqdm 실시간 출력을 위한 pty 에뮬레이션
        parameters=[
            {'data_dir': data_dir},
            {'pretrained_model': pretrained_model},
            {'model_save_dir': model_save_dir},
            {'epochs': epochs},
            {'batch_size': batch_size},
            {'learning_rate': learning_rate},
            {'tol': tol},
            {'num_workers': num_workers},
        ],
    )

    # 4) rqt_plot 실행 (ros2 run rqt_plot rqt_plot … 형식으로 호출)
    rqt_plot_node = ExecuteProcess(
        cmd=[
            'ros2', 'run', 'rqt_plot', 'rqt_plot',
            '/training/loss',
            '/training/accuracy'
        ],
        output='screen'
    )

    return LaunchDescription([
        # Launch Arguments 리스트
        data_dir_arg,
        pretrained_model_arg,
        model_save_dir_arg,
        epochs_arg,
        batch_size_arg,
        learning_rate_arg,
        tol_arg,
        num_workers_arg,

        # 실제 노드 실행
        train_node,
        rqt_plot_node,
    ])
