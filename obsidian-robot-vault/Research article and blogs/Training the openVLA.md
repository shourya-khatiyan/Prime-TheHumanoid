here is a complete, step-by-step practice run for our openVLA fine-tuning project. we will follow every phase from start to finish, exactly as we will do it for real.

---

## phase 0: preparation and planning (before we start anything)

this phase happens on our local computer before we even touch the cloud.

### step 0.1: gather all required information

before we launch anything, we need to have these things ready:

| item                     | what we need                            | where to find it                                  |
| :----------------------- | :-------------------------------------- | :------------------------------------------------ |
| cloud provider account   | vast.ai account with payment method     | vast.ai website                                   |
| ssh key pair             | public and private key for secure login | generated on our local machine using `ssh-keygen` |
| openVLA repository url   | https://github.com/openvla/openvla      | github                                            |
| dataset download command | wget command for bridgeData v2          | openVLA documentation                             |
| model name               | "openvla/openvla-7b"                    | hugging face                                      |

### step 0.2: generate ssh key pair (if we dont have one)

on our local terminal, we run:
```bash
ssh-keygen -t rsa -b 4096 -C "our-email@example.com"
```
this creates two files: `~/.ssh/id_rsa` (private key, keep it safe) and `~/.ssh/id_rsa.pub` (public key, we will upload this to vast.ai).

### step 0.3: understand our training parameters

we should write down our chosen parameters somewhere for reference:

| parameter | our value |
| :--- | :--- |
| model | openVLA 7B |
| dataset | bridgeData v2 |
| fine-tuning method | lora |
| lora rank | 32 |
| batch size | 16 |
| learning rate | 5e-4 |
| gradient accumulation | 1 |
| total steps | ~60,000 - 80,000 |

---

## phase 1: launching the cloud instance

this is where we rent our gpu on vast.ai.

### step 1.1: log in to vast.ai

we go to vast.ai in our browser and log in.

### step 1.2: add our ssh public key

we go to account settings and add our public key (the content of `~/.ssh/id_rsa.pub`). this allows us to ssh into any instance we rent.

### step 1.3: search for a suitable instance

we go to the "rent" page and search for instances with:
- gpu: a100 (80gb) or h100
- storage: at least 100 gb
- price: within our budget

### step 1.4: select a template

when we click on an instance, we see a template selection screen. we choose the **pytorch (vast)** template because it comes with cuda and pytorch pre-installed. this saves us time installing basic dependencies.

### step 1.5: launch the instance

we click "rent" and wait for the instance to start. this usually takes 1-3 minutes.

### step 1.6: get the connection details

once the instance is running, vast.ai shows us:
- the ip address
- the ssh port (usually 22 or something else)
- the username (usually `root`)

---

## phase 2: connecting to the instance and basic setup

this is where we first log into our cloud machine.

### step 2.1: ssh into the instance

on our local terminal, we run:
```bash
ssh -i ~/.ssh/id_rsa root@<instance-ip> -p <port>
```
replace `<instance-ip>` and `<port>` with the details from vast.ai.

### step 2.2: verify gpu is working

once logged in, we run:
```bash
nvidia-smi
```
this should show our gpu (a100 or h100) with its memory and utilization. if we see an error, something is wrong with the gpu setup.

### step 2.3: install tmux (if not already installed)

tmux is essential for keeping training running even if our ssh connection drops. we install it:
```bash
apt-get update
apt-get install -y tmux
```

### step 2.4: create a tmux session for our work

we create a tmux session called "openvla":
```bash
tmux new -s openvla
```
now we are inside the tmux session. everything we run here will keep running even if we disconnect.

---

## phase 3: setting up the openVLA codebase

this is where we download the openVLA training code.

### step 3.1: clone the openVLA repository

inside our tmux session, we run:
```bash
git clone https://github.com/openvla/openvla.git
cd openvla
```
this downloads the entire openVLA codebase.

### step 3.2: install python dependencies

we install the required packages:
```bash
pip install -e .
```
this installs openVLA in "editable" mode, meaning any changes we make to the code are immediately available.

we also install additional libraries that openVLA needs:
```bash
pip install transformers peft accelerate datasets torch
```

### step 3.3: verify the installation

we can test that openVLA is installed correctly by running:
```bash
python -c "import openvla; print('openVLA installed successfully')"
```
if we get an error, we need to troubleshoot missing dependencies.

---

## phase 4: downloading the dataset

this is where we get bridgeData v2 onto our instance.

### step 4.1: create a directory for the dataset

inside our openVLA folder, we create a datasets directory:
```bash
mkdir -p datasets/open-x-embodiment/
cd datasets/open-x-embodiment/
```

### step 4.2: download bridgeData v2

we use the official wget command:
```bash
wget -r -nH --cut-dirs=4 --reject="index.html*" https://rail.eecs.berkeley.edu/datasets/bridge_release/data/tfds/bridge_dataset/
```
this downloads the entire bridgeData v2 dataset. the dataset is about **21.54 gb**, so this will take some time depending on our internet speed.

### step 4.3: rename the dataset folder

openVLA expects the dataset folder to be named `bridge_orig`:
```bash
mv bridge_dataset bridge_orig
```

### step 4.4: verify the download

we check that the dataset downloaded correctly:
```bash
ls bridge_orig/
```
we should see a folder like `0.1.0/` with `.tfrecord` files inside.

---

## phase 5: downloading the pre-trained model weights

this is where we get the openVLA 7B model from hugging face.

### step 5.1: understand where the model comes from

openVLA provides pre-trained model weights on hugging face at `openvla/openvla-7b`. the training script will automatically download these when we run it.

### step 5.2: (optional) pre-download the model

if we want to download the model separately before training (to avoid download time during training), we can run:
```bash
python -c "from transformers import AutoModelForVision2Seq; AutoModelForVision2Seq.from_pretrained('openvla/openvla-7b')"
```
this downloads the model to the hugging face cache. but we can also let the training script handle this.

---

## phase 6: configuring the training

this is where we set up our hyperparameters.

### step 6.1: understand the training script

the main script for lora fine-tuning is `vla-scripts/finetune.py`. this script handles:
- loading the pre-trained model
- loading the dataset
- applying lora
- running the training loop
- saving checkpoints

### step 6.2: understand the key parameters

here are the important parameters we can set:

| parameter | what it does | our value |
| :--- | :--- | :--- |
| `--vla_path` | path to pre-trained model | "openvla/openvla-7b" |
| `--data_root_dir` | where our dataset is | "./datasets/open-x-embodiment/" |
| `--dataset_name` | which dataset to use | "bridge_orig" |
| `--lora_rank` | rank of lora matrices | 32 |
| `--batch_size` | samples per gpu per step | 16 |
| `--grad_accumulation_steps` | accumulate gradients over steps | 1 |
| `--learning_rate` | learning rate | 5e-4 |
| `--image_aug` | use image augmentation | false (bridgeData already has augmentation) |

### step 6.3: where to set hyperparameters

we set these directly as command-line arguments when we run the script. there is no separate configuration file we need to edit for basic lora fine-tuning.

for more advanced configurations, openVLA uses a centralized `config.py` file, but for our purposes, command-line arguments are sufficient.

---

## phase 7: running the training

this is the main event.

### step 7.1: make sure we are in the right place

we should be in the openVLA directory:
```bash
cd ~/openvla
```

### step 7.2: run the training command

we run the fine-tuning script with our parameters:
```bash
torchrun --standalone --nnodes 1 --nproc-per-node 1 \
  vla-scripts/finetune.py \
  --vla_path "openvla/openvla-7b" \
  --data_root_dir "./datasets/open-x-embodiment/" \
  --dataset_name "bridge_orig" \
  --lora_rank 32 \
  --batch_size 16 \
  --grad_accumulation_steps 1 \
  --learning_rate 5e-4 \
  --image_aug False
```

### step 7.3: what happens during training

during training, we will see:
- **loading messages**: the model and dataset are being loaded
- **progress bars**: showing training steps and loss
- **loss values**: decreasing over time as the model learns
- **checkpoint messages**: periodic saves of the model state

### step 7.4: detach from tmux

once training is running, we can detach from tmux by pressing:
```
ctrl+b, then d
```
this puts us back in the regular terminal. we can now safely close our ssh connection. the training will continue running in the background.

### step 7.5: reattaching to check progress

later, when we want to check on training, we ssh back in and run:
```bash
tmux attach -t openvla
```
we will see the training exactly where we left it.

---

## phase 8: monitoring training progress

this is how we keep an eye on things.

### step 8.1: monitoring via tmux (terminal view)

the simplest way to monitor is to reattach to our tmux session and watch the output:
```bash
tmux attach -t openvla
```
we will see the loss values, step counts, and any error messages in real time.

### step 8.2: monitoring gpu usage

in a separate tmux window (or another ssh session), we can monitor gpu usage:
```bash
watch -n 1 nvidia-smi
```
this shows us gpu memory usage, utilization, and temperature every second.

### step 8.3: graphical monitoring with tensorboard (optional)

if we want to see training curves graphically, we can use tensorboard. first, we need to install it:
```bash
pip install tensorboard
```
then, we need to configure our training script to log metrics. openVLA's finetune.py may support this with a `--log_dir` parameter. we would run:
```bash
tensorboard --logdir=./logs --port=6006
```
then we would access it via our browser at `http://<instance-ip>:6006`. however, this requires port forwarding setup, which can be complex on vast.ai.

### step 8.4: monitoring with weights & biases (wandb)

wandb is a popular alternative that works through the cloud. we can install it:
```bash
pip install wandb
```
then we would add wandb logging to our training script or use the `--wandb_project` parameter if openVLA supports it. the logs would then be visible on wandb's website, accessible from anywhere.

---

## phase 9: checkpoints and saving

this is how we protect our progress and save our final model.

### step 9.1: how checkpoints work in openVLA

openVLA automatically saves checkpoints during training. the checkpoints are saved with a descriptive name that includes the configuration:
```
openvla-7b+liber...+
```
the checkpoint contains:
- the model weights (lora adapters)
- the optimizer state
- the current step number

### step 9.2: where checkpoints are saved

checkpoints are saved in the current working directory (where we ran the training script). the exact path follows the naming pattern described above.

### step 9.3: how to resume from a checkpoint

if training is interrupted for any reason, we can resume from the latest checkpoint. we add the `--resume_from_checkpoint` parameter to our training command:
```bash
torchrun --standalone --nnodes 1 --nproc-per-node 1 \
  vla-scripts/finetune.py \
  --vla_path "openvla/openvla-7b" \
  --data_root_dir "./datasets/open-x-embodiment/" \
  --dataset_name "bridge_orig" \
  --lora_rank 32 \
  --batch_size 16 \
  --learning_rate 5e-4 \
  --resume_from_checkpoint ./path/to/checkpoint_folder
```
this loads the saved state and continues training from where it left off.

### step 9.4: how far checkpoints save us

checkpoints save us from losing **all progress since the last checkpoint was saved**. if we save every 1000 steps and training crashes at step 1500, we lose only the last 500 steps of progress. if we save every epoch and training crashes in the middle of epoch 5, we resume from the end of epoch 4.

### step 9.5: best practices for checkpoints

we should:
- let the training script save checkpoints automatically
- not delete old checkpoints until training is complete
- keep at least the last 3 checkpoints in case we need to roll back
- save the final model separately after training finishes

---

## phase 10: post-training (after training completes)

this is what we do when training is done.

### step 10.1: verify training completed successfully

we reattach to our tmux session and check that:
- the script finished without errors
- the final loss is reasonable
- the checkpoint files were created

### step 10.2: locate the final model checkpoint

the final checkpoint will be in the directory where we ran training. it will have a name like:
```
openvla-7b+bridge_orig+...
```

### step 10.3: download the trained model to our local machine

we need to get the trained model weights to our local computer. from our local terminal (not ssh), we run:
```bash
scp -i ~/.ssh/id_rsa -P <port> root@<instance-ip>:/path/to/checkpoint/folder ./local/folder/
```
this copies the checkpoint folder from the cloud instance to our local machine.

### step 10.4: (optional) save the model to hugging face

if we want to share or reuse the model later, we can upload it to hugging face:
```bash
huggingface-cli login
huggingface-cli upload our-username/our-model-name ./checkpoint/folder
```

### step 10.5: terminate the instance

this is the most important step for cost control. we go to vast.ai and **terminate** the instance. this stops all billing. if we only stop the instance, we may still pay for storage.

---

## summary: complete phase checklist

| phase | what we do | where |
| :--- | :--- | :--- |
| 0 | prepare ssh key, gather information | local computer |
| 1 | launch instance on vast.ai | vast.ai website |
| 2 | ssh in, install tmux | cloud instance |
| 3 | clone openVLA, install dependencies | cloud instance |
| 4 | download bridgeData v2 dataset | cloud instance |
| 5 | download pre-trained model | cloud instance (auto) |
| 6 | understand hyperparameters | cloud instance |
| 7 | run training in tmux | cloud instance |
| 8 | monitor progress via tmux/tensorboard | cloud instance |
| 9 | let checkpoints save automatically | cloud instance |
| 10 | download model, terminate instance | local computer + vast.ai |

---

## tools summary: where everything lives

| tool | purpose | installed where |
| :--- | :--- | :--- |
| ssh | connect to instance | local computer |
| tmux | keep training running after disconnect | cloud instance |
| git | clone openVLA code | cloud instance |
| pip | install python packages | cloud instance |
| wget | download dataset | cloud instance |
| nvidia-smi | monitor gpu | cloud instance |
| tensorboard/wandb | graphical monitoring | cloud instance (optional) |
| scp | download model to local | local computer |

this is our complete practice run. when we do it for real, we follow these exact same steps in the same order.