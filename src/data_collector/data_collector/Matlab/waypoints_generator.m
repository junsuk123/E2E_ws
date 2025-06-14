%% 1. 초기화 및 ROS 2 연결 설정
% 이전에 생성된 ROS 2 노드가 남아 있으면 삭제
if exist('rosNode', 'var')
    clear rosNode;
end
% 새 노드 생성 (노드 이름: 'autodrive_node')
rosNode = ros2node("autodrive_node");

%% 2. 환경 변수 설정 & ROS 2 환경 소스
ros2Env = [ ...
    "unset LD_LIBRARY_PATH; " + ...
    "export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu; " + ...
    "unset ROS_DOMAIN_ID; " + ...
    "export GAZEBO_PLUGIN_PATH=$GAZEBO_PLUGIN_PATH:/opt/ros/humble/lib; " + ...
    "source /opt/ros/humble/setup.bash; " + ...
    "source ~/e2e_ws/install/setup.bash" ...
];

%% 3. Gazebo 시뮬레이션 런치 (core.launch.py) 및 YOLO 노드 런치
% 3.1 Gazebo 런치
disp("3-1) Gazebo 시뮬레이션 런치...");
launchGazeboCmd = sprintf( ...
    'bash -i -c "%s && source ~/.bashrc; ros2 launch my_robot_description core.launch.py &"', ...
    ros2Env);
[statusGazebo, outGazebo] = system(launchGazeboCmd);
if statusGazebo ~= 0
    error("Gazebo 런치 실패:\n%s", outGazebo);
end
pause(5);  % spawn_entity 서비스 준비 대기

% 3.2 YOLOv11n_seg 노드 런치
disp("3-2) YOLOv11n_seg 노드 런치...");
launchYoloCmd = sprintf( ...
    'bash -i -c "%s && ros2 launch yolo_ros yolov11n_seg.launch.py &"', ...
    ros2Env);
[statusYolo, outYolo] = system(launchYoloCmd);
if statusYolo ~= 0
    error("YOLOv11n_seg 런치 실패:\n%s", outYolo);
end
pause(5);

%% 4. '/cmd_vel' 토픽 대기 및 '/odom' 구독자 생성
% cmd_vel 토픽이 나올 때까지 대기
cmdVelSub = ros2subscriber(rosNode, "/cmd_vel", "geometry_msgs/Twist");
disp("cmd_vel 메시지 수신 대기 중...");
while true
    msgCmd = cmdVelSub.LatestMessage;
    if ~isempty(msgCmd)
        disp("cmd_vel 메시지 수신됨. /odom 데이터를 기록합니다.");
        break;
    end
    pause(0.05);
end

% odom 토픽 폴링 구독자
odomSub = ros2subscriber(rosNode, "/odom", "nav_msgs/Odometry");

%% 5. Figure 생성 및 실시간 Plot 설정
fig = figure("Name", "Real-Time Robot Position", "NumberTitle", "off");
ax = axes(fig);
hold(ax, "on"); grid(ax, "on");
xlabel(ax, "X [m]"); ylabel(ax, "Y [m]");
title(ax, "실시간 로봇 위치");
axis(ax, [-1, 1, -1, 1]);  % 초기 축 범위

% 데이터 저장용 변수 초기화
waypoints = zeros(0,2);
hPath  = plot(ax, NaN, NaN, "b-", "LineWidth", 1);
hPoint = plot(ax, NaN, NaN, "ro", "MarkerSize", 6, "MarkerFaceColor", "r");

%% 6. 폴링 루프: 위치 수신 → Plot 업데이트
disp("Figure 창이 살아있는 동안 실시간으로 위치를 업데이트합니다...");
margin = 0.1;  % 축 여유

while isgraphics(fig)
    msgOdom = odomSub.LatestMessage;
    if ~isempty(msgOdom)
        % 위치 추출
        p = msgOdom.pose.pose.position;
        x = p.x; y = p.y;
        % 경로 저장
        waypoints(end+1, :) = [x, y];  %#ok<AGROW>
        % Plot 업데이트
        set(hPath, "XData", waypoints(:,1), "YData", waypoints(:,2));
        set(hPoint, "XData", x, "YData", y);
        % 축 범위 자동 조정
        xmin = min(min(waypoints(:,1)) - margin, -1);
        xmax = max(max(waypoints(:,1)) + margin,  1);
        ymin = min(min(waypoints(:,2)) - margin, -1);
        ymax = max(max(waypoints(:,2)) + margin,  1);
        axis(ax, [xmin, xmax, ymin, ymax]);
        drawnow limitrate;
    end
    pause(0.05);
end

%% 7. 종료 처리: 구독자 및 노드 삭제
clear odomSub cmdVelSub rosNode;
disp("Figure 창이 닫혔습니다. 구독자 및 노드를 정리합니다.");

%% 8. Waypoints 저장
folderName = "waypoints/release";
if ~exist(folderName, "dir")
    mkdir(folderName);
end
t = datetime('now');
fileName = sprintf("waypoints_%s.mat", datestr(t, 'yyyymmdd_HHMMSS'));
fullPath = fullfile(folderName, fileName);
save(fullPath, "waypoints");
fprintf("Waypoints가 '%s'에 저장되었습니다.\n", fullPath);

%% 9. 백그라운드 노드 강제 종료
disp("백그라운드 노드 정리 시작...");
killCmds = { ...
    'pkill -9 -f ros', ...
    'pkill -9 -f yolo', ...
    'pkill -9 -f tracking_node', ...
    'pkill -9 -f image_fusion', ...
    'pkill -9 -f data_collector', ...
    'pkill -9 -f robot_state_pub', ...
    'killall -9 gz gazebo', ...
    'killall -9 rviz2', ...
    'ros2 daemon stop', ...
    'ros2 daemon start' ...
};
for i = 1:numel(killCmds)
    cmd = sprintf('bash -lc "set +e; %s; %s"', ros2Env, killCmds{i});
    [statusKill, outKill] = system(cmd);
    if statusKill ~= 0
        fprintf("[경고] 명령 실패 [%s]:\n%s\n", killCmds{i}, outKill);
    end
end
disp("백그라운드 노드 정리 완료.");
