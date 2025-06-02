%% 1. 초기화 및 ROS 2 연결 설정
% 이전에 생성된 ROS 2 노드가 남아 있으면 종료 (변수가 있으면 clear)
if exist('node', 'var')
    clear node;   % 이전에 생성된 node 객체 삭제
end

% 새 노드 생성 (노드 이름: 'autodrive_node')
node = ros2node("autodrive_node");
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

%% 2. '/cmd_vel' 토픽이 생성될 때까지 대기
% 메시지 타입: geometry_msgs/Twist
cmdSub = ros2subscriber(node, "/cmd_vel", "geometry_msgs/Twist");

disp("cmd_vel 메시지 수신 대기 중...");
while true
    msgCmd = cmdSub.LatestMessage;
    if ~isempty(msgCmd)
        disp("cmd_vel 메시지 수신됨. 이제 /odom를 기록합니다.");
        break;
    end
    pause(0.05);
end

%% 3. '/odom' 토픽을 폴링 방식으로 구독 (메시지 타입: nav_msgs/Odometry)
sub = ros2subscriber(node, "/odom", "nav_msgs/Odometry");

%% 4. Figure 창 생성 및 실시간 Plot 준비
fig = figure("Name", "Real-Time Robot Position", "NumberTitle", "off");
ax = axes(fig);
hold(ax, "on");
grid(ax, "on");
xlabel(ax, "X [m]");
ylabel(ax, "Y [m]");
title(ax, "실시간 로봇 위치");

% 초기 축 범위 설정 (예: ±1m). 이후 데이터가 쌓이면 아래 코드에서 갱신
axis(ax, [-1, 1, -1, 1]);

% waypoints를 빈 배열로 초기화 (N×2 크기: [x, y])
waypoints = zeros(0,2);

% 경로(Line)와 현재 위치(Point) 객체 미리 생성
hPath  = plot(ax, NaN, NaN, "b-", "LineWidth", 1);                       % 경로를 실선으로
hPoint = plot(ax, NaN, NaN, "ro", "MarkerSize", 6, "MarkerFaceColor", "r"); % 현재 위치를 빨간 점으로

%% 5. 폴링 루프: Figure 창이 닫힐 때까지 위치를 가져와서 plot 및 저장
disp("Figure 창이 닫힐 때까지 실시간으로 로봇 위치를 Plot 합니다...");
margin = 0.1;  % 축 범위 주변 여유(m 단위)

while isgraphics(fig)  % Figure 창이 살아있는 동안 반복
    msgOdom = sub.LatestMessage;  % 가장 최근에 수신된 메시지
    if ~isempty(msgOdom)
        % 5-1. Position 정보 추출
        pos = msgOdom.pose.pose.position;  % geometry_msgs/Point
        x = pos.x;
        y = pos.y;
        
        % 5-2. waypoints에 [x, y] 추가
        waypoints(end+1, :) = [x, y];  %#ok<AGROW>
        
        % 5-3. 경로(Line) 업데이트
        set(hPath, "XData", waypoints(:,1), "YData", waypoints(:,2));
        
        % 5-4. 현재 위치 점 업데이트
        set(hPoint, "XData", x, "YData", y);
        
        % 5-5. 축 범위 자동 조정: 현재까지 모든 waypoints 포함
        xmin = min(waypoints(:,1));
        xmax = max(waypoints(:,1));
        ymin = min(waypoints(:,2));
        ymax = max(waypoints(:,2));
        % 여유(margin)를 추가
        xmin = xmin - margin;
        xmax = xmax + margin;
        ymin = ymin - margin;
        ymax = ymax + margin;
        % 초기축 범위 ±1m 유지 체크
        xmin = min(xmin, -1);
        xmax = max(xmax,  1);
        ymin = min(ymin, -1);
        ymax = max(ymax,  1);
        axis(ax, [xmin, xmax, ymin, ymax]);
        
        drawnow limitrate;  % 화면 업데이트
    end
    
    pause(0.05);  % 폴링 주기 (0.05초)
end

%% 6. Figure 창이 닫히면 구독 및 노드 정리
clear sub;    % subscriber 핸들 삭제 (ODOM)
clear cmdSub; % cmd_vel subscriber 핸들 삭제
clear node;   % node 객체 삭제 (ROS 2 노드 종료)

%% 7. 수집된 waypoints 저장
% 7-1. 저장할 폴더 만들기 (없으면 새로 생성)
folderName = "waypoints";
if ~exist(folderName, "dir")
    mkdir(folderName);
end

% 7-2. 현재 날짜_시간으로 파일명 생성 (예: waypoints_20250602_091523.mat)
t = datetime('now');
timeStr = datestr(t, 'yyyymmdd_HHMMSS');  % 예: "20250602_091523"
fileName = sprintf("waypoints_%s.mat", timeStr);

% 7-3. full path 생성 및 저장
fullPath = fullfile(folderName, fileName);
save(fullPath, "waypoints");

fprintf("Waypoints 데이터가 '%s'에 저장되었습니다.\n", fullPath);

% 최종적으로 저장된 waypoints 확인 (선택적으로 출력)
disp("수집된 waypoints:");
disp(waypoints);
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
