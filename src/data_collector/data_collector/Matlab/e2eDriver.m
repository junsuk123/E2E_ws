%% inferenceAndPlot_withBatchTests.m
% 20회 랜덤 스폰 테스트 자동화, 결과 시각화 및 경로 플로팅
% Ubuntu 22.04 + ROS2 Humble 환경 기준
clc;close all; clear;
%% 0. 백그라운드 노드 강제 종료
ros2Env = [ ...
    "unset LD_LIBRARY_PATH; " + ...
    "export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu; " + ...
    "unset ROS_DOMAIN_ID; " + ...
    "export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp;"+ ...
    "export GAZEBO_PLUGIN_PATH=$GAZEBO_PLUGIN_PATH:/opt/ros/humble/lib; " + ...
    "source /opt/ros/humble/setup.bash; " + ...
    "source ~/e2e_ws/install/setup.bash" ...
];

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

%% 설정
numTests     = 20;        % 총 테스트 횟수
timeLimit    = 150;       % 각 시나리오별 시간 제한 (sec)
successFlags = false(1, numTests);
elapsedTimes = nan(1, numTests);
paths        = cell(1, numTests);  % 각 테스트별 주행 경로 저장
modelName = "MobileNetV2_20250616_013019_doing.pth";  % 또는 원하는 모델 파일명(0617 기준 가장 성능 좋음.)
% modelName = "MobileNetV2_20250615_121253_doing.pth";  % 또는 원하는 모델 파일명 
% modelName = "MobileNetV2_20250616_012232_bob.pth";  % 또는 원하는 모델 파일명
% modelName = "MobileNetV2_20250615_014247_junsuk.pth";  % 또는 원하는 모델 파일명
% modelName = "MobileNetV2_student_distilled.pth";  % 또는 원하는 모델 파일명

%% 2. Waypoints 로드 (테스트 전 공통)
waypointFolder = "waypoints";
pattern        = fullfile(waypointFolder, "waypoints_*.mat");
files          = dir(pattern);
if isempty(files)
    error("Waypoints 파일을 찾을 수 없습니다: %s", pattern);
end
[~, idxLatest] = max([files.datenum]);
data           = load(fullfile(waypointFolder, files(idxLatest).name));
if ~isfield(data, "waypoints")
    error("파일에 waypoints 변수가 없습니다: %s", files(idxLatest).name);
end
waypoints     = data.waypoints;          % N×2 [x y]
goal          = [10.08, -0.099032];       % 목표 위치
obs1          = [4.394416, 0.100351];       % 장애물1 위치
obs2          = [7.241572, -1.188195];       % 장애물2 위치
wall_left_start          = [0.0, 1.012151];       % 시작점 왼쪽벽  위치
wall_right_start          = [0.0, -2.361800];       % 시작점 오른쪽벽  위치
wall_left_end          = [21.179338, 1.012151];       % 시작점 왼쪽벽  위치
wall_right_end          = [21.179338, -2.361800];       % 시작점 오른쪽벽  위치
% 보간할 점 개수
n = 100;

% 선형 보간 (linspace 이용)
wall_left  = [ linspace(wall_left_start(1),  wall_left_end(1),  n).' , ...
               linspace(wall_left_start(2),  wall_left_end(2),  n).' ];

wall_right = [ linspace(wall_right_start(1), wall_right_end(1), n).' , ...
               linspace(wall_right_start(2), wall_right_end(2), n).' ];

goalThreshold = 0.8;                     % 목표 도달 임계 거리 [m]

%% 테스트 루프
for idx = 1:numTests
    fprintf("\n=== Test %d / %d ===\n", idx, numTests);
    
    % 2-1) 랜덤 spawn 위치 생성 (x, z 고정)
    spawnX = 0.0;
    spawnY = -1.5 + (-1.0 + 1.5) * rand();  % uniform in [-1.5, 0.2]
    spawnZ = 0.0;
    fprintf("Spawn 위치: x=%.3f, y=%.3f, z=%.3f\n", spawnX, spawnY, spawnZ);
        
    cmdCDDS = sprintf( ...
        'bash -i -c "%s && export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp &"', ...
        ros2Env);
    if system(cmdCDDS) ~= 0
        error("CDDS 실패 (Test %d)", idx);
    end
    pause(1);
    % 2-2) Gazebo + Robot spawn
    cmdGazebo = sprintf( ...
        'bash -i -c "%s && humble;e2e;cd ~/e2e_ws; colcon build;source ~/.bashrc; ros2 launch my_robot_description core.launch.py x_pose:=%0.3f y_pose:=%0.3f z_pose:=%0.3f &"', ...
        ros2Env, spawnX, spawnY, spawnZ);
    if system(cmdGazebo) ~= 0
        error("Gazebo 런치 실패 (Test %d)", idx);
    end
    pause(1);
    
    % 2-3) YOLOv11n_seg 노드 런치
    cmdYolo = sprintf('bash -i -c "%s && ros2 launch yolo_ros yolov11n_seg.launch.py &"', ros2Env);
    system(cmdYolo); pause(1);
    
    % 2-4) Image Fusion 노드 런치
    cmdFusion = sprintf('bash -i -c "%s && ros2 launch image_fusion image_fusion.launch.py &"', ros2Env);
    system(cmdFusion); pause(1);
    
    % 2-5) Rviz 런치
    cmdRviz = sprintf('bash -i -c "%s && rviz2 &"', ros2Env);
    system(cmdRviz); pause(1);
    
    % 2-6) Inference 노드 런치
    cmdInf = sprintf( ...
        'bash -i -c "%s && ros2 launch e2e_control inference.launch.py model_name:=%s &"', ...
        ros2Env, modelName);
    system(cmdInf); pause(3);
    %%
    % 3) ROS2 Subscriber 생성
    node    = ros2node("inference_plot_node");
    odomSub = ros2subscriber(node, "/odom", "nav_msgs/Odometry");

    % 4) 테스트 시작: 시간 측정 및 경로 기록
    path    = [];     % 이번 테스트 경로 초기화
    tic;
    reached = false;
    while true
        elapsed = toc;
        if elapsed > timeLimit
            fprintf("▶ Time limit 초과 (%.1f s)\n", elapsed);
            break;
        end
        
        msg = odomSub.LatestMessage;
        if ~isempty(msg)
            pos = [ msg.pose.pose.position.x, msg.pose.pose.position.y ];
            path(end+1, :) = pos;  % 경로에 추가
            norm(pos-goal)
            if norm(pos - goal) < goalThreshold
                fprintf("▶ 목표 도달: %.1f s\n", elapsed);
                reached = true;
                break;
            end
        end
        
        pause(0.0333);
    end
    
    % 5) 결과 저장
    elapsedTimes(idx) = min(toc, timeLimit);
    successFlags(idx) = reached;
    paths{idx}        = path;
    
    % 6) 백그라운드 노드 정리
    killCmds = { ...
        'pkill -9 -f ros2', ...
        'pkill -9 -f yolo', ...
        'pkill -9 -f image_fusion', ...
        'killall -9 rviz2', ...
        'pkill -9 -f inference', ...
        'pkill -9 -f gzserver', ...
        'pkill -9 -f gzclient', ...
        'ros2 daemon stop', ...
        'ros2 daemon start' ...
    };
    for k = 1:numel(killCmds)
        system(sprintf('bash -lc "%s; %s"', ros2Env, killCmds{k}));
    end
    
    pause(2);
end

%% 7. 결과 시각화: Bar Chart
figure("Name","Batch Test Results","NumberTitle","off");
b = bar(1:numTests, elapsedTimes, 'FaceColor','flat');
for i = 1:numTests
    if successFlags(i)
        b.CData(i,:) = [0 0.7 0];  % 성공: 녹색
    else
        b.CData(i,:) = [0.8 0 0];  % 실패: 빨강
    end
end
xlabel("Test Index");
ylabel("Elapsed Time [s]");
title(sprintf("20 Tests: %d Success / %d Fail", sum(successFlags), numTests));

fprintf("\n=== 최종 결과 ===\n");
fprintf("성공 횟수      : %d / %d\n", sum(successFlags), numTests);
if any(successFlags)
    fprintf("평균 소요 시간: %.1f s\n", mean(elapsedTimes(successFlags)));
else
    fprintf("모든 테스트 실패\n");
end

%% 8. 전체 경로 시각화
figure("Name","All Trajectories","NumberTitle","off");
hold on; grid on;
colors = lines(numTests);
for i = 1:numTests
    path_i = paths{i};
    if isempty(path_i)
        warning('Test %d: 경로 데이터 없음, 스킵합니다.', i);
        continue;
    end
    plot(path_i(:,1), path_i(:,2), '-', 'Color', colors(i,:), 'LineWidth', 1);
end
% plot(waypoints(:,1), waypoints(:,2), 'k--', 'LineWidth', 1.5);
plot(goal(1), goal(2), 'r*', 'LineWidth', 1.5);
plot(obs1(1), obs1(2), 'g*', 'LineWidth', 1.5);
plot(obs2(1), obs2(2), 'g*', 'LineWidth', 1.5);
plot(wall_left(:,1),  wall_left(:,2),  'b-', 'DisplayName','Left Wall');
plot(wall_right(:,1), wall_right(:,2), 'b-', 'DisplayName','Right Wall');
xlabel("X [m]"); ylabel("Y [m]");
title("All Scenario Trajectories");
legendEntries = arrayfun(@(i) sprintf('Test %d', i), 1:numTests, 'UniformOutput', false);
legend([legendEntries, {'gaol'},{'obs1'},{'obs2'},{'Left Wall'},{'Right Wall'}], 'Location','bestoutside');

