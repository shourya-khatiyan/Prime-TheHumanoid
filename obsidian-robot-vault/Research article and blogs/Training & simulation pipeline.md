
## Phase 1: Mechanical Design to Digital Twin

Before we write any ml code, our software needs a mathematically perfect understanding of the physical hardware.

**1.Design in CAD**
For our biped, this includes the pelvis, thighs, shins, ankles, and feet. the exact material properties *must be* defined so the software knows the mass of every individual piece.

**2.Export to URDF:** (Unified Robot Description Format)
We cannot load raw CAD files into a physics engine. We must export the assembly into a URDF (or MJCF) file. This XML-based file acts as the robot's "DNA," containing:

- **Links:** The solid body parts (mass, center of mass, inertia tensor).
      
- **Joints:** How the links connect (e.g., a revolute hinge at the knee).
    
- **Collision Meshes:** Simplified geometry so the simulator knows when the foot hits the floor.  

**3.Define Joint and Actuator Limits:**
If we don't constrain the joints, the AI will bend the robot's knees backward. We must hardcode strict limits into the URDF based on human anatomy (e.g., knees only bend 0 to 130 degrees). We also set the peak torque (e.g., 80 Nm for hip motors, 40 Nm for ankles) to match our actual physical motors.


## Phase 2: Generating Reference Motions (Kinematics)
Reinforcement learning (RL) agents learn much faster if they have a target animation to mimic, rather than trying to invent walking from complete randomness.

1. **Motion Capture (MoCap):** We can record human walking using stereo cameras. By passing this video through a pose-estimation framework (like MediaPipe), we extract 3D keypoints of the human skeleton.
    
2. **Inverse Kinematics (IK):** We use mathematical solvers to calculate the specific joint angles (in quaternions) our robot needs to hit to match those human keypoints.
    
3. **Smoothing the Cycle:** Raw mocap data is jerky. We must post-process the data to loop perfectly by matching the mathematical derivatives (velocity and acceleration) of the first and last frames of the walk cycle.


## Phase 3: The Simulation Environment (Isaac Lab)

Training a neural network to walk requires millions of trial-and-error attempts. Doing this in real life would destroy the robot in five minutes. We use **NVIDIA Isaac Lab** to simulate thousands of our robots simultaneously on a single GPU.
### Defining the Observation Space (What the Robot "Feels")

At every fraction of a second, the neural network needs a snapshot of its current state. Our robot will observe:

- **IMU Data:** Base linear velocity, angular velocity, and orientation (is the torso leaning?).  
    
- **Proprioception:** Current joint positions and velocities (where are my legs?).
    
- **Commands:** Target heading and target velocity (where is the user telling me to go?).
    
- **Contact Sensors:** Are the feet currently touching the ground? (We can use cheap Force Sensing Resistors on the physical feet for this).
    
- **Motion Phase:** A smoothly looping cyclic signal (like a clock) that helps the robot synchronize its left-right stepping rhythm.
### Defining the Action Space (What the Robot "Does")

The neural network outputs a desired target position for every single motor.

> Note on Actuator Dynamics:_ The neural network doesn't output raw electrical current. It outputs a position. A low-level PD (Proportional-Derivative) controller uses specific **stiffness and damping** values to calculate the torque required to reach that position.


## Phase 4: Reward Shaping (The Brain's Incentive Structure)

This is the hardest part of RL engineering. The robot learns by maximizing a score. If we write the score poorly, it will cheat. Our reward function must balance several competing goals:

|**Reward / Penalty Type**|**Mathematical Purpose**|**Practical Effect**|
|---|---|---|
|**Progress Reward**|`+` for moving velocity towards the user's commanded target direction.|It actually walks forward instead of standing still.|
|**Alive Term**|`+` massive reward for simply not falling over.|The baseline instinct for balance.|
|**Animation Tracking**|`+` for matching the joint positions/velocities of our MoCap reference data.|Makes the walk look human and natural, rather than robotic or chaotic.|
|**Energy Penalties**|`-` for high torque usage, high joint acceleration, and jerky action rates.|Protects our physical motors from overheating and grinding their own gears.|
|**Posture Penalties**|`-` for the torso rocking left/right, or for feet sliding on the ground while planted.|Ensures a stable, safe gait suitable for carrying an upper body later.|

## Phase 5: Training & Deployment

With the environment set up and rewards defined, we initiate the **Proximal Policy Optimization (PPO)** algorithm.


1. **The Training Loop:** The robot tries to walk, falls, calculates its negative reward, updates its neural network weights, and tries again. At step `0`, it collapses instantly. By step `20,000`, it learns to balance. By step `150,000`, it is consistently following the reference animation.  
    
2. **Domain Randomization:** _Crucial for our project._ Before we consider training finished, we must randomly alter the simulation. We randomize the robot's mass, change ground friction, and apply invisible "pushes" to the robot. If the policy survives this randomized chaos, it is ready for the real world.
      
3. **Sim-to-Real Transfer:** We export the trained neural network (typically to ONNX format). We load this onto our robot's onboard computer (like a Jetson or Raspberry Pi). The network runs inference at ~50Hz, constantly reading the physical sensors and feeding target positions to the motor drivers.