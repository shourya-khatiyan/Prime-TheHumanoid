
**Mass Accuracy & Missing Components**

We must be hyper-accurate with the mass of the existing leg components. The RL policy learns to balance based on the Center of Mass (CoM) and inertia tensors. if our simulation weights deviate by more than 5-10% from the real physical parts, the sim to real transfer will fail. Because we have only designed the lower body, we will tackle the missing components by adding a "dummy link" (a simple virtual box) attached to the pelvis in the URDF. We will manually assign this dummy link the estimated combined weight of our future upper body, battery pack, and embedded compute module (like our NVIDIA Jetson Orin NX) so the legs train to carry the final payload from day one.


**Core URDF Requirements**

A URDF (Unified Robot Description Format) is an XML file that breaks our robot down into two main categories. Everything in our CAD must map to these:

|**Component Type**|**What it represents**|**Required Data for URDF**|
|---|---|---|
|**Links**|The solid, physical parts (e.g., thighs, shins, feet).|Mass (kg), Center of Mass (XYZ offset), Inertia Matrix (3x3), Visual Mesh (for looking at it), Collision Mesh (simplified shape for physics).|
|**Joints**|The connections between links (e.g., hips, knees).|Joint type (revolute for motors), Axis of rotation (usually Z-axis), Position limits (min/max radians), Effort limits (peak motor torque).|

**Our CAD to URDF Conversion Workflow**
  

- **Step 1: Isolate and Group Components (Fusion 360)**
    
    We cannot export raw, unorganized bodies. Every moving part must be combined into a single discrete "Component" in Fusion. For example, the entire lower leg assembly (brackets, screws, housing) below the knee must be merged into a single component named `right_shin`.
    
- **Step 2: Assign Physical Materials**
    
    We must apply accurate materials (e.g., Aluminum 6061, PLA plastic, Steel) to every single body in the CAD. Fusion uses this to automatically calculate the exact mass and 3x3 inertia tensors for the URDF.
    
- **Step 3: Define Joint Origins**
    
    We need to create specific "As-Built Joints" in Fusion. The most critical rule: the axis of rotation for every single motor (hip pitch, knee, ankle) must be perfectly aligned with the Z-axis of that joint's local coordinate system, as this is the standard ROS and Isaac Lab expect.  
    
- **Step 4: Automated Export**
    
    Instead of writing the XML manually, we will install the open-source `fusion2urdf` script into Autodesk Fusion. Running this script will automatically parse our assembly, extract the masses/inertias, export STL meshes, and write the base URDF file.  
    
- **Step 5: Post-Processing the XML**
    
    The auto-generated file will not be perfect. We must manually open the URDF code to add our dummy payload link at the pelvis and input the exact maximum torque limits and velocity limits from our specific actuator datasheets to prevent the AI from exceeding physical hardware limits.
