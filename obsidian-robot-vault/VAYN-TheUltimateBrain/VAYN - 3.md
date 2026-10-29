# VAYN-3 — Versatile Arbitrated Embodied Nervous-System

## Architecture Specification: Neuromorphic Tri-System Zero-Copy Pipeline (V3)

## 1. Context and Limitations of V2 Architecture

The V2 Architecture (Multi-Engine Zero-Copy Shared VRAM) successfully solved the inter-process communication latency that plagues standard ROS2 robotics setups. By compiling the 7B Vision-Language-Action (VLA) model and the Fast Reactor as two separate TensorRT engines sharing a single physical GPU memory pointer, it achieved 0ms data transfer latency.

  

However, physical simulation and theoretical hardware mapping reveal two critical bottlenecks when deploying V2 on a single System-on-Chip (SoC) like the Jetson Orin NX:

  

### Limitation A: L2 Cache Thrashing

The Jetson Orin NX uses a unified Ampere architecture where the CPU and GPU share the same memory bandwidth and L2 cache.

  

- When the 5Hz System 2 (7B VLA) triggers a massive attention-layer matrix multiplication, it completely floods the L2 cache.
    
      
    
- When the 200Hz System 1 (Fast Reactor) preempts the VLA via a high-priority CUDA stream, its required data has been flushed out of the L2 cache.
    
      
    
- System 1 is forced to fetch its input data from the much slower main RAM (a "cache miss"), introducing micro-stutters (jitter) into the motor control loop. In bipedal locomotion, jitter causes cumulative balance decay.
    
      
    

### Limitation B: Latent Stagnation (The 200ms Blind Spot)

In V2, System 2 updates the shared memory with a new intent vector every 200 milliseconds.

  

- For the 39 physical frames in between these updates, System 1 reads the exact same static latent vector.
    
      
    
- If the humanoid slips on frame 5, System 1 must calculate corrective motor torques using an "intent" vector that does not know the slip occurred. The semantic plan becomes decoupled from physical reality until System 2 catches up 175 milliseconds later.
    
      
    

## 2. V3 System Overview: Biological Mimicry

To resolve these bottlenecks without requiring off-board server clusters, the V3 architecture introduces a middle layer. It shifts from a dual-system to a tri-system pipeline, mimicking human neurobiology. Instead of passing a static intent directly from the "Cortex" to the "Spinal Cord," V3 routes the intent through a "Cerebellum"—an ultra-fast, continuous-time forward predictive model that actively modifies the semantic plan in real-time before it reaches the motor outputs.

  

## 3. Core Component Breakdown

### System 2: The Cortex (High-Level VLA)

- **Architecture:** 7B-parameter Vision-Language-Action Transformer.
    
      
    
- **Frequency:** 5Hz (updates every 200ms).
    
      
    
- **Precision:** INT4 (quantized via TensorRT-LLM).
    
      
    
- **Function:** Processes raw camera feeds, depth maps, and textual instructions.
    
      
    
- **Output:** Instead of outputting a single static semantic vector ($Z$), it outputs the vector **plus its expected trajectory** over the next 200ms, known as Latent Velocity ($\Delta Z$).
    
      
    

### System 1.5: The Cerebellar Bridge (Latent Extrapolator)

- **Architecture:** Liquid Neural Network (LNN) or a micro State Space Model (e.g., Mamba) containing ~200k parameters.
    
      
    
- **Frequency:** 200Hz (updates every 5ms).
    
      
    
- **Location:** Permanently pinned inside the GPU’s ultra-fast SRAM/L1 Cache.
    
      
    
- **Function:** Acts as an active shared memory buffer. It ingests the static $Z$ and $\Delta Z$ from System 2, alongside the instantaneous joint encoder data (proprioception). It mathematically extrapolates and shifts the latent vector to match current physical reality, outputting an adjusted vector ($Z'$).
    
      
    

### System 1: The Spinal Cord (Visuomotor Reactor)

- **Architecture:** High-speed Multi-Layer Perceptron (MLP).
    
      
    
- **Frequency:** 200Hz (updates every 5ms).
    
      
    
- **Precision:** FP16.
    
      
    
- **Function:** Reads the actively shifting $Z'$ from System 1.5 and translates it directly into raw PWM/torque commands for the physical actuators.
    
      
    

## 4. Architectural Flowchart

Plaintext

```
[Camera / Audio / Text]                      [Instant Proprioception / IMU / Encoders]
          │                                                    │
          ▼                                                    ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                           SINGLE HOST PROCESS (C++ / Python)                     │
│                                                                                  │
│  [ SYSTEM 2: THE CORTEX ]                                                        │
│  Engine: 7B VLA Backbone                                                         │
│  Frequency: 5 Hz (200ms loop)                                                    │
│  Hardware Queue: Default CUDA Stream                                             │
│          │                                                                       │
│          │ Generates intent (Z) & expected trajectory (ΔZ)                       │
│          ▼                                                                       │
│  ==============================================================================  │
│  ||                    SYSTEM 1.5: THE CEREBELLAR BRIDGE                     ||  │
│  ||                                                                          ||  │
│  || Architecture: Liquid Neural Network (LNN) pinned in L1/L2 GPU Cache.     ||  │
│  || Function: Ingests Z, ΔZ, and live proprioception at 200Hz. Alters the    ||  │
│  ||           intent continuously to account for physical perturbations.     ||  │
│  || Output: The Extrapolated Latent State (Z')                               ||  │
│  ==============================================================================  │
│          │                                                                       │
│          │ Z' is passed with zero-copy latency                                   │
│          ▼                                                                       │
│  [ SYSTEM 1: THE SPINAL CORD ]                                                   │
│  Engine: Visuomotor MLP                                                          │
│  Frequency: 200 Hz (5ms loop)                                                    │
│  Hardware Queue: Highest Priority CUDA Stream (Non-Blocking)                     │
│                                                                                  │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │
                                         ▼
                               [ Target Joint Torques ]
```

## 5. Technical Advantages & Edge-Native Features

### Zero-Latency Intent Correction

If the bipedal robot is bumped or slips on a surface, System 1.5 (The Cerebellum) immediately detects the anomaly via the proprioception input. Because it is a continuous-time network, it shifts the latent intent vector ($Z \rightarrow Z'$) to a "recovery" state within 5 milliseconds. System 1 receives this updated intent and adjusts the torques instantly, bypassing the 200ms delay required for the 7B model to visually process the slip.

  

### Elimination of Cache Thrashing

Because System 1.5 is a microscopic model (e.g., LNN), it fits entirely within the GPU's localized SRAM. It never has to compete with the 7B model for main memory bandwidth. When the 200Hz loop preempts the 5Hz loop, System 1.5 and System 1 execute entirely out of the cache, guaranteeing deterministic, jitter-free execution times.

  

### Proprioceptive Backpropagation (Edge Dreaming)

The addition of System 1.5 unlocks an autonomous, on-device learning loop:

  

1. **Error Caching:** During the day, whenever System 1.5 has to aggressively shift $Z'$ away from the original $Z$ to prevent a fall, the system caches the delta (the error in the VLA's prediction).
    
      
    
2. **Nightly LoRA Tuning:** When the robot is docked and inactive, the operating system launches a Low-Rank Adaptation (LoRA) fine-tuning script.
    
      
    
3. **Weight Re-alignment:** It uses the cached physical error deltas to compute gradients and adjust the weights of System 2. The robot literally "dreams" about its balance mistakes, permanently rewiring its high-level reasoning model to avoid the same kinematic errors the next day, entirely on the Jetson Orin NX.