%% ========================================================================
%  sequentialLaunchAndPurePursuit.m
%
% 1) 환경 변수(GAZEBO_PLUGIN_PATH, TURTLEBOT3_MODEL) 설정
% 2) TurtleBot3 Gazebo 시뮬레이션 런치 (20초 대기)
% 3) YOLOv11n_seg 노드 런치 (10초 대기)
% 4) Image Fusion 노드 런치 (3초 대기)
% 5) Data Collector 노드 런치 (5초 대기)
% 6) 최신 waypoints로 Pure Pursuit 추종 (실시간 Plot)
%% ========================================================================
clc;clear;close all;
%% 1. 환경 변수 설정 & ROS 2 환경 소스
ros2Env = [ ...
    "unset LD_LIBRARY_PATH; " + ...
    "export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu; " + ...
    "unset ROS_DOMAIN_ID; " + ...
    "export GAZEBO_PLUGIN_PATH=$GAZEBO_PLUGIN_PATH:/opt/ros/humble/lib; " + ...
    "export TURTLEBOT3_MODEL=burger_cam; " + ...
    "source /opt/ros/humble/setup.bash; " + ...
    "source ~/e2e_ws/install/setup.bash" ...
];

%% 2. TurtleBot3 Gazebo 시뮬레이션 런치 (20초 대기)
disp("1) TurtleBot3 Gazebo 시뮬레이션 런치...");
cmd1 = sprintf( ...
  'bash -i -c "%s && ros2 launch turtlebot3_gazebo turtlebot3_AICenter.launch.py &"', ...
  ros2Env);
[status1, out1] = system(cmd1);
if status1 ~= 0
    error("TurtleBot3 Gazebo 런치 실패:\n%s", out1);
end
pause(5);  % Gazebo가 spawn_entity 서비스를 올릴 시간 확보

%% 3. YOLOv11n_seg 노드 런치 (10초 대기)
disp("2) YOLOv11n_seg 노드 런치...");
% 실제 패키지 이름 `yolo_ros`, launch 파일명 `yolov11n_seg.launch.py` (터미널 확인 필수)
cmd2 = sprintf( ...
  'bash -i -c "%s && ros2 launch yolo_ros yolov11n_seg.launch.py &"', ...
  ros2Env);
[status2, out2] = system(cmd2);
if status2 ~= 0
    error("YOLOv11n_seg 런치 실패:\n%s", out2);
end
pause(5);

%% 4. Image Fusion 노드 런치 (3초 대기)
disp("3) Image Fusion 노드 런치...");
% 실제 패키지/launch 파일명을 터미널에서 확인한 뒤 그대로 사용
cmd3 = sprintf( ...
  'bash -i -c "%s && ros2 launch image_fusion image_fusion.launch.py &"', ...
  ros2Env);
[status3, out3] = system(cmd3);
if status3 ~= 0
    error("Image Fusion 런치 실패:\n%s", out3);
end
pause(3);

%% 5. Data Collector 노드 런치 (5초 대기)
disp("4) Data Collector 노드 런치...");
% 실제 패키지/launch 파일명: collect_data.launch.py (터미널 확인 필수)
cmd4 = sprintf( ...
  'bash -i -c "%s && ros2 launch data_collector data_collector.launch.py &"', ...
  ros2Env);
[status4, out4] = system(cmd4);
if status4 ~= 0
    error("Data Collector 런치 실패:\n%s", out4);
end
pause(5);

%% 5) Pure Pursuit 추종 (expertDriver 로직)
% 5-1. waypoints 폴더에서 최신 파일 자동 선택
folderName  = "waypoints";
filePattern = fullfile(folderName, "waypoints_*.mat");
files       = dir(filePattern);
if isempty(files)
    error("waypoints 폴더에 'waypoints_*.mat' 파일이 없습니다.");
end
[~, idxLatest]   = max([files.datenum]);
latestFileName   = files(idxLatest).name;
fullFilePath     = fullfile(folderName, latestFileName);
fprintf("가장 최신 waypoints 파일: %s\n", latestFileName);

data = load(fullFilePath);
if ~isfield(data, "waypoints")
    error("선택된 파일에 'waypoints' 변수가 없습니다.");
end
waypoints = data.waypoints;  % N×2 배열 [x  y]

% 5-2. ROS 2 노드/퍼블리셔/서브스크라이버 생성
if exist("node","var"), clear node; end
node    = ros2node("expert_driver_node");
odomSub = ros2subscriber(node, "/odom",    "nav_msgs/Odometry");
cmdPub  = ros2publisher(node,  "/cmd_vel", "geometry_msgs/Twist");

% 5-3. Pure Pursuit Controller 설정
pp = controllerPurePursuit;
pp.Waypoints             = waypoints;
pp.DesiredLinearVelocity = 0.4;
pp.MaxAngularVelocity    = 0.5;
pp.LookaheadDistance     = 0.2;

% 5-4. 마지막 waypoint 및 도달 임계값 설정
goal          = waypoints(end, :);
goalThreshold = 0.1;

% 5-5. Figure 창 생성 및 전체 경로 Plot 준비
fig = figure("Name","Expert Driver: Pure Pursuit","NumberTitle","off");
ax  = axes(fig);
hold(ax, "on");
grid(ax, "on");
xlabel(ax, "X [m]");
ylabel(ax, "Y [m]");
title(ax, "Pure Pursuit 추종 중: 전체 경로 및 현재 위치");

% 전체 경로(waypoints)를 파란 실선으로 표시
hPathStatic = plot(ax, waypoints(:,1), waypoints(:,2), "b-", "LineWidth", 1);
% 현재 위치를 표시할 빨간 점 핸들 생성 (초기값 NaN)
hCurrent = plot(ax, NaN, NaN, "ro", "MarkerSize", 6, "MarkerFaceColor", "r");

% 축 범위 설정: waypoints 전체 범위 + margin
margin = 0.2;
xmin   = min(waypoints(:,1)) - margin;
xmax   = max(waypoints(:,1)) + margin;
ymin   = min(waypoints(:,2)) - margin;
ymax   = max(waypoints(:,2)) + margin;
axis(ax, [xmin, xmax, ymin, ymax]);

% 5-6. 추종 루프 (10 Hz)
disp("Pure Pursuit 추종 시작...");
rate = robotics.Rate(10);

while true
    odomMsg = odomSub.LatestMessage;
    if isempty(odomMsg)
        waitfor(rate);
        continue;
    end

    posX = odomMsg.pose.pose.position.x;
    posY = odomMsg.pose.pose.position.y;
    qx   = odomMsg.pose.pose.orientation.x;
    qy   = odomMsg.pose.pose.orientation.y;
    qz   = odomMsg.pose.pose.orientation.z;
    qw   = odomMsg.pose.pose.orientation.w;

    rot   = quaternion([qw, qx, qy, qz]);
    eul   = eulerd(rot, "ZYX", "frame");
    theta = deg2rad(eul(1));

    currentPose = [posX, posY, theta];

    % 목표 도달 여부 확인
    distToGoal = norm([posX, posY] - goal);
    if distToGoal < goalThreshold
        % 정지 명령 발행
        stopMsg = ros2message(cmdPub);
        stopMsg.Linear.X  = 0.0;
        stopMsg.Angular.Z = 0.0;
        send(cmdPub, stopMsg);
        disp("목표 지점에 도달했습니다. 정지합니다.");
        break;
    end

    % Pure Pursuit 제어 계산
    [v, omega] = pp(currentPose);

    % 속도 명령 발행
    cmdMsg = ros2message(cmdPub);
    cmdMsg.linear.x  = v;
    cmdMsg.angular.z = omega;
    send(cmdPub, cmdMsg);

    % 현재 위치를 실시간으로 빨간 점으로 업데이트
    set(hCurrent, "XData", posX, "YData", posY);
    drawnow limitrate;

    waitfor(rate);
end

%% 6) 후처리: 구독/퍼블리셔 해제 및 노드 종료
clear odomSub;
clear cmdPub;
clear node;
disp("expertDriver 스크립트가 종료되었습니다.");

%% ===== MATLAB 스크립트의 맨 마지막에 추가 =====
disp("Figure가 닫혔습니다. 백그라운드 노드를 정리합니다…");

% ① ROS2 환경 변수 및 setup 스크립트 (문자열로 미리 만들어 두기)
ros2Env = [ ...
    'unset LD_LIBRARY_PATH; ' ...
    'export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu; ' ...
    'unset ROS_DOMAIN_ID; ' ...
    'export GAZEBO_PLUGIN_PATH=$GAZEBO_PLUGIN_PATH:/opt/ros/humble/lib; ' ...
    'export TURTLEBOT3_MODEL=burger_cam; ' ...
    'source /opt/ros/humble/setup.bash; ' ...
    'source ~/e2e_ws/install/setup.bash' ...
];

% ② 개별 pkill/daemon 명령을 cell 배열로 정의
killCmds = { ...
    'pkill -9 -f yolo', ...
    'pkill -9 -f tracking_node', ...
    'pkill -9 -f image_fusion_no', ...
    'pkill -9 -f robot_state_pub', ...
    'pkill -9 -f inference_node', ...
    'pkill -9 -f collector_node', ...
    'pkill -9 -f gzserver', ...
    'pkill -9 -f gzclient', ...
    'pkill -9 -f turtlebot3_diff_drive', ...
    'pkill -9 -f turtlebot3_imu', ...
    'pkill -9 -f turtlebot3_joint_state', ...
    'pkill -9 -f turtlebot3_laserscan', ...
    'ros2 daemon stop', ...
    'ros2 daemon start' ...
};

% ③ 하나씩 순차 실행 (실패해도 계속 진행)
for i = 1:numel(killCmds)
    cmd = sprintf('bash -lc "set +e; %s; %s"', ros2Env, killCmds{i});
    [st, out] = system(cmd);
    if st ~= 0
        fprintf("명령 실패 [%s]:\n%s\n", killCmds{i}, out);
    end
end

disp("모든 pkill/daemon 명령이 완료되었습니다.");

% ④ MATLAB 변수 정리
clear odomSub cmdSub node
disp("inferenceAndPlot 스크립트가 완전히 종료되었습니다.");
