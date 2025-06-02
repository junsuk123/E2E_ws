%% ========================================================================
%  sequentialLaunchAndPurePursuit_Repeated_LaunchAndKill.m
%
% 설명:
%  - 아래 스크립트는 10회 반복(trial)하며,
%    매 반복마다 백그라운드 ROS2 노드를 전부 새로 띄우고,
%    Pure Pursuit를 수행한 뒤 강제 종료합니다.
%  
% 1) Gazebo 시뮬레이션   → 2) YOLOv11n_seg 노드   → 3) Image Fusion 노드
% → 4) ResNet Inference 노드  → 5) Pure Pursuit 수행  → 6) 백그라운드 노드 종료
% 
% Pure Pursuit 파라미터(랜덤 범위)
%  - DesiredLinearVelocity ∈ [0.2, 0.5]
%  - MaxAngularVelocity    ∈ [0.2, 0.7]
%  - LookaheadDistance      ∈ [0.2, 0.4]
%% ========================================================================
clc; clear; close all;

%% 1. 공통: ROS2 환경 변수 및 setup.bash 경로 문자 벡터로 미리 정의
ros2Env = [ ...
    "unset LD_LIBRARY_PATH; " + ...
    "export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu; " + ...
    "unset ROS_DOMAIN_ID; " + ...
    "export GAZEBO_PLUGIN_PATH=$GAZEBO_PLUGIN_PATH:/opt/ros/humble/lib; " + ...
    "export TURTLEBOT3_MODEL=burger_cam; " + ...
    "source /opt/ros/humble/setup.bash; " + ...
    "source ~/e2e_ws/install/setup.bash" ...
];

%% 2. 반복 횟수 정의
numTrials = 10;

for trial = 1:numTrials
    fprintf("\n===== Trial %d / %d 시작 =====\n", trial, numTrials);
    
    %% 2-1. 랜덤 Pure Pursuit 파라미터 생성
    rng("shuffle");
    randLinVel    = 0.2 + (0.5 - 0.2)*rand();   % [0.2, 0.5]
    randAngVel    = 0.2 + (0.7 - 0.2)*rand();   % [0.2, 0.7]
    randLookahead = 0.2 + (0.4 - 0.2)*rand();   % [0.2, 0.4]
    fprintf(" → [랜덤 파라미터] LinVel=%.3f, AngVel=%.3f, Lookahead=%.3f\n", ...
            randLinVel, randAngVel, randLookahead);
    
    %% 2-2. ① Gazebo 시뮬레이션 띄우기 (20초 가량 대기)
    disp("1) TurtleBot3 Gazebo 시뮬레이션 런치...");
    cmd1 = sprintf( ...
      'bash -i -c "%s && ros2 launch turtlebot3_gazebo turtlebot3_AICenter.launch.py &"', ...
      ros2Env);
    [st1, out1] = system(cmd1);
    if st1 ~= 0
        error("Gazebo 런치 실패:\n%s", out1);
    end
    pause(7);  % Gazebo가 충분히 기동될 시간 확보
    
    %% 2-3. ② YOLOv11n_seg 노드 띄우기 (10초 대기)
    disp("2) YOLOv11n_seg 노드 런치...");
    cmd2 = sprintf( ...
      'bash -i -c "%s && ros2 launch yolo_ros yolov11n_seg.launch.py &"', ...
      ros2Env);
    [st2, out2] = system(cmd2);
    if st2 ~= 0
        error("YOLOv11n_seg 런치 실패:\n%s", out2);
    end
    pause(5);
    
    %% 2-4. ③ Image Fusion 노드 띄우기 (3초 대기)
    disp("3) Image Fusion 노드 런치...");
    cmd3 = sprintf( ...
      'bash -i -c "%s && ros2 launch image_fusion image_fusion.launch.py &"', ...
      ros2Env);
    [st3, out3] = system(cmd3);
    if st3 ~= 0
        error("Image Fusion 런치 실패:\n%s", out3);
    end
    pause(5);

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

    %% 3. Pure Pursuit 수행
    % 3-1. 최신 Waypoints 불러오기
    folderName  = "waypoints";
    filePattern = fullfile(folderName, "waypoints_*.mat");
    files       = dir(filePattern);
    if isempty(files)
        error("waypoints 폴더에 'waypoints_*.mat' 파일이 없습니다.");
    end
    [~, idxLatest] = max([files.datenum]);
    latestFileName = files(idxLatest).name;
    fullFilePath   = fullfile(folderName, latestFileName);
    fprintf("가장 최신 waypoints 파일: %s\n", latestFileName);
    
    data = load(fullFilePath);
    if ~isfield(data, "waypoints")
        error("선택된 파일에 'waypoints' 변수가 없습니다.");
    end
    waypoints = data.waypoints;  % Nx2 array [x y]
    
    % 3-2. ROS 2 노드/퍼블리셔/서브스크라이버 생성
    if exist("node", "var"), clear node; end
    node    = ros2node("expert_driver_node");
    odomSub = ros2subscriber(node, "/odom",    "nav_msgs/Odometry");
    cmdPub  = ros2publisher(node,  "/cmd_vel", "geometry_msgs/Twist");
    
    % 3-3. Pure Pursuit Controller 생성 및 랜덤 파라미터 적용
    pp = controllerPurePursuit;
    pp.Waypoints             = waypoints;
    pp.DesiredLinearVelocity = randLinVel;
    pp.MaxAngularVelocity    = randAngVel;
    pp.LookaheadDistance     = randLookahead;
    
    % 3-4. 마지막 waypoint 및 도달 임계값 설정
    goal          = waypoints(end, :);
    goalThreshold = 0.1;
    
    % 3-5. Figure 창 생성 및 전체 경로 Plot 준비
    fig = figure("Name", sprintf("Pure Pursuit Trial %d", trial), ...
                 "NumberTitle", "off");
    ax  = axes(fig);
    hold(ax, "on"); grid(ax, "on");
    xlabel(ax, "X [m]"); ylabel(ax, "Y [m]");
    title(ax, sprintf("Trial %d: Pure Pursuit 진행", trial));
    
    plot(ax, waypoints(:,1), waypoints(:,2), "b-", "LineWidth", 1);
    hCurrent = plot(ax, NaN, NaN, "ro", "MarkerSize", 6, "MarkerFaceColor", "r");
    margin = 0.2;
    xmin   = min(waypoints(:,1)) - margin;
    xmax   = max(waypoints(:,1)) + margin;
    ymin   = min(waypoints(:,2)) - margin;
    ymax   = max(waypoints(:,2)) + margin;
    axis(ax, [xmin, xmax, ymin, ymax]);
    
    % 3-6. Pure Pursuit 제어 루프 (10 Hz)
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
        
        distToGoal = norm([posX, posY] - goal);
        if distToGoal < goalThreshold
            stopMsg = ros2message(cmdPub);
            stopMsg.Linear.X  = 0.0;
            stopMsg.Angular.Z = 0.0;
            send(cmdPub, stopMsg);
            disp("목표 지점에 도달했습니다. 정지합니다.");
            break;
        end
        
        [v, omega] = pp(currentPose);
        cmdMsg = ros2message(cmdPub);
        cmdMsg.linear.x  = v;
        cmdMsg.angular.z = omega;
        send(cmdPub, cmdMsg);
        
        set(hCurrent, "XData", posX, "YData", posY);
        drawnow limitrate;
        waitfor(rate);
    end
    
    pause(1);  % 잠시 대기 후 Figure 닫기
    if isvalid(fig), close(fig); end
    
    %% 4. 후처리: 구독/퍼블리셔 해제 및 노드 종료
    clear odomSub cmdPub node pp;
    disp(sprintf("Trial %d 종료: expert_driver 노드 해제 완료\n", trial));
    
    %% 5. 백그라운드 노드 & 프로세스 강제 종료
    disp("백그라운드 노드 정리 시작...");
    killCmds = { ...
        'pkill -9 -f yolo', ...
        'pkill -9 -f tracking_node', ...
        'pkill -9 -f image_fusion', ...
        'pkill -9 -f data_collector', ...    % inference_node(ResNet) 강제 종료
        'pkill -9 -f robot_state_pub', ...
        'pkill -9 -f gzserver', ...
        'pkill -9 -f gzclient', ...
        'pkill -9 -f turtlebot3_diff_drive', ...
        'pkill -9 -f turtlebot3_imu', ...
        'pkill -9 -f turtlebot3_joint_state', ...
        'pkill -9 -f turtlebot3_laserscan', ...
        'ros2 daemon stop', ...
        'ros2 daemon start' ...
    };
    
    for k = 1:numel(killCmds)
        cmd_k = sprintf('bash -lc "set +e; %s; %s"', ros2Env, killCmds{k});
        [st_k, out_k] = system(cmd_k);
        if st_k ~= 0
            fprintf("[경고] 명령 실패 [%s]:\n%s\n", killCmds{k}, out_k);
        end
    end
    disp("백그라운드 노드 정리 완료.\n");
    
    pause(2);  % 다음 Trial 진입 전 짧은 여유
end

disp("==== 모든 Trial(10회)이 완료되었습니다! ====");
