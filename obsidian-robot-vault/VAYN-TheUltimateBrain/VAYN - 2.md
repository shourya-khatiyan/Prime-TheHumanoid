# VAYN-2 — Versatile Arbitrated Embodied Nervous-System

## Architecture Documentation: Multi-Engine Zero-Copy

>The requirement to integrate CAD-to-URDF physics parameters into the fast reactor training loop is logged and deferred for our next phase. 

## Architecture Specification
The Multi-Engine Zero-Copy architecture resolves the fatal hardware bottleneck of a monolithic engine: **Streaming Multiprocessor (SM) starvation**.

Instead of forcing a massive Vision-Language-Action (VLA) model and a lightning-fast locomotion policy into one brittle file, we compile them as two distinct NVIDIA TensorRT `.engine` files. Crucially, we load both engines into a **single runtime process**. This allows them to function independently while sharing the exact same physical memory address on the GPU.
### System Flowchart

```
[Camera/Text]                                [Motor Encoders/IMU]
       │                                              │
       ▼                                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 SINGLE HOST PROCESS (C++ / Python)          │
│                                                             │
│  [Thread 1: 5Hz VLA Loop]          [Thread 2: 200Hz Loop]   │
│  Priority: Normal                  Priority: Maximum        │
│  Queue: Default CUDA Stream        Queue: Non-Blocking      │
│         │                                   │               │
│         ▼                                   ▼               │
│  ┌───────────────┐                 ┌────────────────┐       │
│  │ ENGINE 1:     │                 │ ENGINE 2:      │       │
│  │ 7B VLA Model  │                 │ Fast Reactor   │       │
│  │ (INT4 Weights)│                 │ (FP16 Weights) │       │
│  └──────┬────────┘                 └────────┬───────┘       │
│         │                                   │               │
│         │ (Writes Over Data)  (Reads Latest)│               │
│         ▼                                   ▼               │
│  =========================================================  │
│  ||     SHARED VRAM POINTER (The "Latent Register")     ||  │
│  =========================================================  │
│                                                 │           │
└─────────────────────────────────────────────────┼───────────┘
                                                  ▼
                                         [Motor Torques (PWM)]
```

## Core Mechanisms: How It Works

To make this architecture function on a Jetson Orin NX, three specific hardware mechanisms must work together.

  

### 1. Unified Memory Space (Zero-Copy)

In traditional robotics, passing data between two models requires the GPU to send the data back to the CPU, which then sends it back to the GPU for the second model. This causes latency.

  

In this architecture, you manually allocate a specific block of Video RAM (VRAM) using a tool like `cudaMalloc`.

  

- You pass this memory address to **Engine 1** as its _output_ destination.
    
      
    
- You pass this exact same memory address to **Engine 2** as its _input_ source.
    
      
    
- **Result:** The 7B VLA model computes the spatial/semantic plan and overwrites this memory block at 5Hz. The fast reactor reads whatever is currently in that block at 200Hz. The data physically never moves.
    
      
    

### 2. Hardware Preemption via CUDA Streams

The Jetson Orin NX uses the Ampere GPU architecture, which consists of physical calculator cores called **Streaming Multiprocessors (SMs)**. A 7B parameter model will attempt to consume 100% of these SMs to process an image. If the 200Hz locomotion loop needs to run while the VLA model is calculating, a bipedal robot will fall.

  

You solve this using **CUDA Streams**. A stream is simply a queue of tasks for the GPU.

  

- **Engine 1 (VLA):** Runs on the default CUDA stream.
    
      
    
- **Engine 2 (Reactor):** Runs on a custom stream flagged with `cudaStreamNonBlocking` and given high hardware priority.
    
      
    
- **Result (Preemption):** When the 5-millisecond timer hits, the GPU will physically pause the heavy VLA matrix calculations, allocate a few SM cores to instantly compute the fast reactor's locomotion torques, and then resume the VLA calculations.
    
      
    

### 3. Asynchronous Threading & Stale Data Fallback

Because the engines are fully decoupled, a failure in the VLA model (e.g., a corrupted camera frame causing a delay) does not crash the locomotion loop.

  

If Engine 1 takes 400 milliseconds instead of 200 milliseconds to update the Latent Register, Engine 2 simply keeps reading the last known vector. To prevent the robot from executing a stale command indefinitely, you program a **Decay Function** inside the host process: if the Latent Register has not been overwritten recently, Engine 2 automatically blends the stale vector with a default "stand and balance" vector to maintain physical stability.

  

## Implementation Blueprint

To build this, the software must initialize the memory first, then load the engines around it.

  

|**Step**|**Action**|**Technical Execution**|
|---|---|---|
|**1. Compilation**|Export two `.engine` files separately.|`trtexec` is called twice. The VLA is aggressively quantized to INT4. The Reactor is kept in FP16 to ensure high-precision actuator control.|
|**2. Memory Allocation**|Reserve the shared VRAM.|The host process calls `cudaMalloc` to create a `latent_buffer` matching the exact tensor dimensions (e.g., 1 x 4096 floats).|
|**3. Stream Setup**|Configure hardware priority.|Create `stream_fast = cudaStreamCreateWithPriority(..., -1)` (negative numbers indicate higher priority in CUDA).|
|**4. Thread Launch**|Start the asynchronous loops.|Thread A executes Engine 1 at 5Hz on the default stream. Thread B executes Engine 2 at 200Hz on `stream_fast`.|

Are you planning to write the host process that manages these engines in C++ for maximum bare-metal performance, or will you use Python for faster iteration during this phase?