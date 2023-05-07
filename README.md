# Precision landing with reinforcement learning
Deep reinforcement learning for drone precision landing, docker container for simulation in Gazebo-ROS2 
dashing with PX4-Autopilot controller. 

Project developed, starting from a problem of [DRAFT PoliTO](https://www.draftpolito.it/), as part of the course 
"AI in Industry" of the University of Bologna.

# Table of contents
1. [Setup](#setup)
2. [Usage](#usage)
   1. [Train](#train)
   2. [Test](#test)
   3. [Code changes](#changes)
   4. [Speed-up](#speed)
3. [Torch to ONNX](#torch2onnx)
4. [Acknowledgments](#acknowledgments)
5. [References](#references)

## Setup <a name="setup"></a>
Install [Docker](https://docs.docker.com/engine/install/).

Modify the absolute paths in "run_docker.sh" to reflect the position of the repository on your computer.

Add your user to the "docker" group
```
sudo groupadd docker
sudo gpasswd -a $USER docker
newgrp docker  # Or log out/in
```

Build and start the docker, it will take same time, from the root of the repository run:
- For ROS2 Dashing:
   ```
   ./run_docker.sh build  # if an error occurs, delete the docker and run again this command with "sudo"
   ```
- For ROS2 Foxy:
   ```
   ./run_docker.sh build_foxy  # if an error occurs, delete the docker and run again this command with "sudo"
   ```

Don't worry if this message appears "bash: /src/shared/ros_packages/install/setup.bash: No such file or directory", 
you just need to follow the rest of the setup and the following times it won't happen again.

Once it has finished, in the docker run the following commands, in order to build the packages:
```
cd /src/shared/ros_packages
colcon build
source install/setup.bash
```

## Usage <a name="usage"></a>
To start the docker run:
- For ROS2 Dashing:
   ```
   ./run_docker.sh run
   ```
- For ROS2 Foxy:
   ```
   ./run_docker.sh run_foxy
   ```

### Train <a name="train"></a>
Open 2 terminals and run the docker in each one of them, as explained above.

In the first one run:
```
cd /src/shared
./launch_train_ddpg.sh
```

In the second one run:
```
ros2 run px4_ros_extended gazebo_runner.py --train
```

#### Parameters
In "shared/ros_packages/px4_ros_extended/src_py/params.yaml" you can set a few parameters, all of them but 
"train_window_reward" and "test_window_reward", that are used by the jupyter notebook, are used by the agent.

Pay particular attention to the model name, the target dimension and the observation and action shape, as the test script 
will need to know these values.

Among these parameters area also those that let you change the way in which the target moves, such as its maximum and 
minimum velocity or the type of movement, i.e. "linear" or "circular", and the area in which the agent can move.

#### Plots and Models
In the folder "shared/logs" are saved the rewards in pickle files, you can have a look at the jupyter notebook 
"shared/Log Analysis.ipynb" to use them and print a few plots.

In the folder "shared/models" are saved the actor and critic models, 
the files with "best" in the name contain the best weights found during evaluation; the number at the start of the name 
represents the unique-id of the session.

### Test <a name="test"></a>
Open 2 terminals and run the docker in each one of them, as explained above.

In the first one run:
```
ros2 run px4_ros_extended gazebo_runner.py --test --headless
```

#### Baseline
In the second one run
```
cd /src/shared
./launch_baseline.sh
```

#### Agent
In the second one run
```
cd /src/shared
./launch_test_ddpg.sh <run_id> <model> <obs_shape> <action_shape> <num_episodes>
```
Where 'model' is the name of the model to be used, 'paper' or 'small'.

#### Results
The position and velocities for each episode of test are saved in the folder "shared/test_logs".

You can retrieve that information as shown in the jupyter notebook "shared/Log Analysis.ipynb".


### Code Changes <a name="changes"></a>
All the ROS nodes and useful scripts can be found in "shared/ros_packages/px4_ros_extended"; of course, it is possible 
to work on them.

In order to use the changes during training, one should remember to build the "px4_ros_extended" package every time one 
of the nodes' scripts is modified.

```
cd /src/shared/ros_packages
colcon build --packages-select px4_ros_extended
```

### Speed-up & Useful PX4 Parameters <a name="speed"></a>
In order to speed-up the simulation one can start it with these commands, they are already used in the bash scripts and 
in gazebo_runner.py:
```
PX4_SIM_SPEED_FACTOR=6 HEADLESS=1 make px4_sitl_rtps gazebo
micrortps_agent -t UDP
ros2 run px4_ros_extended ddpg_agent.py -p /use_sim_time:=true
ros2 launch px4_ros_extended env_train.launch.py
```

In order to avoid following the drone 
```
PX4_NO_FOLLOW_MODE=1 make px4_sitl_rtps gazebo
```

## Torch to ONNX <a name="torch2onnx"></a>
The notebook "shared/torch_to_onnx.ipynb" shows how to export the actor NN from a torch model to a onnx model to be used in edge-devices. You will have to import the right model, select the number of state and action dimensions, the model path and the name and path of the onnx model.

## Acknowledgments <a name="acknowledgments"></a>
The author(s) would like to acknowledge the contribution of the student team DRAFT PoliTO of the Politecnico di Torino, for supporting the research activity by providing technical advising and experimental equipment that helped the work with the simulator.

The initial code for the DDPG algorithm has been taken from [this](https://github.com/vy007vikas/PyTorch-ActorCriticRL) 
github repository.

## References <a name="references"></a>
```
@article{
   author = {Alejandro Rodriguez-Ramos and Carlos Sampedro and Hriday Bavle and Paloma de la Puente and Pascual Campoy},
   doi = {10.1007/s10846-018-0891-8},
   issn = {15730409},
   issue = {1-2},
   journal = {Journal of Intelligent and Robotic Systems: Theory and Applications},
   title = {A Deep Reinforcement Learning Strategy for UAV Autonomous Landing on a Moving Platform},
   volume = {93},
   year = {2019},
}
```
