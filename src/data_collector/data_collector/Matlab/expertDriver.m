%% ========================================================================
%  sequentialLaunchAndPurePursuit_Repeated_LaunchAndKill_AllWaypoints.m
%
% 설명:
%  - waypoints 디렉토리에 있는 모든 waypoint 파일에 대해,
%    각 파일마다 20회 반복(trial)하며,
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

%% 2. waypoints 디렉토리에서 모든 파일 목록 불러오기
folderName    = "waypoints/release";
filePattern   = fullfile(folderName, "waypoints_*.mat");
allFiles      = dir(filePattern);
if isempty(allFiles)
    error("waypoints 폴더에 'waypoints_*.mat' 파일이 없습니다.");
end

%% 3. 각 waypoint 파일별로 20회 반복 수행
numRepeats = 20;

for fileIdx = 1:numel(allFiles)
    latestFileName = allFiles(fileIdx).name;
    fullFilePath   = fullfile(folderName, latestFileName);
    fprintf("\n===== 파일 [%s] 처리 시작 =====\n", latestFileName);
    
    data = load(fullFilePath);
    if ~isfield(data, "waypoints")
        error("파일 '%s'에 'waypoints' 변수가 없습니다.", latestFileName);
    end
    waypoints = data.waypoints;  % Nx2 array [x y]
    
    % ----------------- 이 안에서 20회 반복 -----------------
    for trial = 1:numRepeats
        fprintf("\n--- Trial %d / %d (파일: %s) 시작 ---\n", trial, numRepeats, latestFileName);
        
        %% 3-1. 랜덤 Pure Pursuit 파라미터 생성
        rng("shuffle");
        randLinVel    = 0.1 + (0.3 - 0.1)*rand();   % [0.2, 0.5]
        randAngVel    = 0.3 + (0.5 - 0.1)*rand();   % [0.2, 0.7]
        randLookahead = 0.15 + (0.25 - 0.1)*rand();   % [0.2, 0.4]
        fprintf(" → [랜덤 파라미터] LinVel=%.3f, AngVel=%.3f, Lookahead=%.3f\n", ...
                randLinVel, randAngVel, randLookahead);

        %% 3-2. ① Gazebo 시뮬레이션 띄우기 (7초 대기)
        disp("1) TurtleBot3 Gazebo 시뮬레이션 런치...");
        cmd1 = sprintf( ...
          'bash -i -c "%s && ros2 launch turtlebot3_gazebo turtlebot3_AICenter.launch.py &"', ...
          ros2Env);
        [st1, out1] = system(cmd1);
        if st1 ~= 0
            error("Gazebo 런치 실패:\n%s", out1);
        end
        pause(7);

        %% 3-3. ② YOLOv11n_seg 노드 띄우기 (5초 대기)
        disp("2) YOLOv11n_seg 노드 런치...");
        cmd2 = sprintf( ...
          'bash -i -c "%s && ros2 launch yolo_ros yolov11n_seg.launch.py &"', ...
          ros2Env);
        [st2, out2] = system(cmd2);
        if st2 ~= 0
            error("YOLOv11n_seg 런치 실패:\n%s", out2);
        end
        pause(5);

        %% 3-4. ③ Image Fusion 노드 띄우기 (5초 대기)
        disp("3) Image Fusion 노드 런치...");
        cmd3 = sprintf( ...
          'bash -i -c "%s && ros2 launch image_fusion image_fusion.launch.py &"', ...
          ros2Env);
        [st3, out3] = system(cmd3);
        if st3 ~= 0
            error("Image Fusion 런치 실패:\n%s", out3);
        end
        pause(5);
        %% 2. Rviz 시뮬레이션 런치 (20초 대기)
        disp("1) Rviz...");
        cmd7 = sprintf( ...
            'bash -i -c "%s && rviz2 &"', ...
            ros2Env);
        [status7, out7] = system(cmd7);
        if status7 ~= 0
            error("Rviz 런치 실패:\n%s", out7);
        end
        pause(5);  % Gazebo가 spawn_entity 서비스를 올릴 시간 확보

        %% 3-5. ④ Data Collector 노드 런치 (5초 대기)
        disp("4) Data Collector 노드 런치...");
        cmd4 = sprintf( ...
            'bash -i -c "%s && ros2 launch data_collector data_collector.launch.py &"', ...
            ros2Env);
        [status4, out4] = system(cmd4);
        if status4 ~= 0
            error("Data Collector 런치 실패:\n%s", out4);
        end
        pause(5);

        %% 3-6. Pure Pursuit 수행
        if exist("node", "var"), clear node; end
        node    = ros2node("expert_driver_node");
        odomSub = ros2subscriber(node, "/odom",    "nav_msgs/Odometry");
        cmdPub  = ros2publisher(node,  "/cmd_vel", "geometry_msgs/Twist");

        pp = controllerPurePursuit;
        pp.Waypoints             = waypoints;
        pp.DesiredLinearVelocity = randLinVel;
        pp.MaxAngularVelocity    = randAngVel;
        pp.LookaheadDistance     = randLookahead;

        goal          = waypoints(end, :);
        goalThreshold = 0.1;

        fig = figure("Name", sprintf("Pure Pursuit Trial %d (%s)", trial, latestFileName), ...
                     "NumberTitle", "off");
        ax  = axes(fig);
        hold(ax, "on"); grid(ax, "on");
        xlabel(ax, "X [m]"); ylabel(ax, "Y [m]");
        title(ax, sprintf("File: %s | Trial %d 수행", latestFileName, trial));

        plot(ax, waypoints(:,1), waypoints(:,2), "b-", "LineWidth", 1);
        hCurrent = plot(ax, NaN, NaN, "ro", "MarkerSize", 6, "MarkerFaceColor", "r");
        margin = 0.2;
        xmin   = min(waypoints(:,1)) - margin;
        xmax   = max(waypoints(:,1)) + margin;
        ymin   = min(waypoints(:,2)) - margin;
        ymax   = max(waypoints(:,2)) + margin;
        axis(ax, [xmin, xmax, ymin, ymax]);

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

        pause(1);
        if isvalid(fig), close(fig); end

        %% 3-7. 후처리: 구독/퍼블리셔 해제 및 노드 종료
        clear odomSub cmdPub node pp;
        disp(sprintf("Trial %d 종료: expert_driver 노드 해제 완료", trial));

        %% 3-8. 백그라운드 노드 & 프로세스 강제 종료
        disp("백그라운드 노드 정리 시작...");
        killCmds = { ...
            'pkill -9 -f yolo', ...
            'pkill -9 -f tracking_node', ...
            'pkill -9 -f image_fusion', ...
            'pkill -9 -f data_collector', ...    % inference_node(ResNet) 강제 종료
            'pkill -9 -f robot_state_pub', ...
            'killall -9 gzserver gzclient gazebo', ...            
            'killall -9 rviz2', ...
            'ros2 daemon stop', ...
            'ros2 daemon start', ...
        };

        for k = 1:numel(killCmds)
            cmd_k = sprintf('bash -lc "set +e; %s; %s"', ros2Env, killCmds{k});
            [st_k, out_k] = system(cmd_k);
            if st_k ~= 0
                fprintf("[경고] 명령 실패 [%s]:\n%s\n", killCmds{k}, out_k);
            end
        end
        disp("백그라운드 노드 정리 완료.");

        pause(2);  % 다음 trial 전 여유
    end
    
    fprintf("===== 파일 [%s]의 모든 Trial (%d회) 완료 =====\n", latestFileName, numRepeats);
end

disp("==== 모든 waypoint 파일에 대한 반복 수행이 완료되었습니다! ====");
