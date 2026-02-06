# 禁用 Nouveau 开源驱动
````
# 编辑黑名单配置文件（注意文件名不同）
sudo vim /etc/modprobe.d/nouveau-blacklist.conf

# 新增两行：
blacklist nouveau
options nouveau modeset=0


# 红帽系统重建 initramfs 并重启
sudo dracut --force
sudo reboot

# Debian系统重建 initramfs 并重启
apt install -y initramfs-tools
update-initramfs -u

# 验证
lsmod | grep nouveau  # 无输出即成功

````


# 显卡闭源驱动安装
从  https://www.nvidia.cn/drivers/lookup/  下载对应显卡的驱动，最好是run文件。比如：<br>
 https://cn.download.nvidia.com/tesla/575.57.08/NVIDIA-Linux-x86_64-575.57.08.run 
 ````
# 红帽系统
sudo dnf install -y kernel-devel-$(uname -r) kernel-headers gcc make dkms
sudo dnf groupinstall -y "Development Tools"  # 安装开发工具链


# 获取当前内核版本路径（关键！）
KERNEL_PATH=/usr/src/kernels/$(uname -r)


# 安装驱动（示例）
bash NVIDIA-Linux-x86_64-575.57.08.run --kernel-source-path=$KERNEL_PATH



# Debian系统
apt -y install gcc make 
再安装内核头文件：
apt -y install linux-headers-$(uname -r) build-essential libglvnd-dev pkg-config

# Proxmox VE系统
apt -y install gcc make 
apt install -y git build-essential pve-headers-`uname -r` dkms jq unzip vim python3-pip mdevctl

bash NVIDIA-Linux-x86_64-575.57.08.run 

````

# Blackwell开源驱动
只能使用Ubuntu24.03以上版本，无需禁用nouveau，因为nvidia开源驱动就是基于nouveau开发的。
直接运行以下命令
````
apt install -y nvidia-driver-580-open
````

# 安装显卡驱动过程：
```
Multiple kernel module types are available for this system. Which would you like to use?
应该选择： NVIDIA Proprietary


WARNING: nvidia-installer was forced to guess the X library path '/usr/lib64' and X module path '/usr/lib64/xorg/modules'; these paths were not queryable from the system.  If X fails to find the NVIDIA X driver module, please install the `pkg-config` utility and
           the X.Org SDK/development package for your distribution and reinstall the driver.
应该选择： OK


Install NVIDIA's 32-bit compatibility libraries?
应该选择： Yes


 WARNING: This NVIDIA driver package includes Vulkan components, but no Vulkan ICD loader was detected on this system. The NVIDIA Vulkan ICD will not function without the loader. Most distributions package the Vulkan loader; try installing the "vulkan-loader",      
           "vulkan-icd-loader", or "libvulkan1" package.
应该选择： OK


Would you like to register the kernel module sources with DKMS? This will allow DKMS to automatically build a new module, if your kernel changes later.
应该选择：Yes


等待进度条跑满，安装完成
Installation of the NVIDIA Accelerated Graphics Driver for Linux-x86_64 (version: 575.57.08) is now complete.
应该选择：OK

````


验证显卡驱动是否安装成功
````
nvidia-smi


Tue Jul 29 15:26:28 2025       
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 575.57.08              Driver Version: 575.57.08      CUDA Version: 12.9     |
|-----------------------------------------+------------------------+----------------------+
| GPU  Name                 Persistence-M | Bus-Id          Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M. |
|                                         |                        |               MIG M. |
|=========================================+========================+======================|
|   0  NVIDIA A2                      Off |   00000000:00:10.0 Off |                    0 |
|  0%   42C    P0             20W /   60W |       0MiB /  15356MiB |     17%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+
                                                                                         
+-----------------------------------------------------------------------------------------+
| Processes:                                                                              |
|  GPU   GI   CI              PID   Type   Process name                        GPU Memory |
|        ID   ID                                                               Usage      |
|=========================================================================================|
|  No running processes found                                                             |
+-----------------------------------------------------------------------------------------+

````


# Docker安装
国内在线安装法
```bash
bash <(curl -sSL https://linuxmirrors.cn/docker.sh)

```
在OpenEuler配套dnf源中已经有了docker，但是版本非常低，只有18.09，无法支持nvidia toolkit，需要采用二进制包安装最新的28版本。<br>
在尝试通过二进制文件安装 Docker 前，请确保主机满足以下要求：​​
64 位系统安装​

Linux 内核版本 3.10 或更高​建议使用您平台可用的最新内核版- 。

iptables 版本 1.4 或更高​用于容器网络管理，若版本过低可能导致错误。

git 版本 1.7 或更高​用于源码管理和依赖获取。

ps 可执行文件​通常由 procps 或类似软件包提供。

XZ Utils 版本 4.9 或更高​用于解压压缩文件。

正确挂载的 cgroupfs 层次结构​单一的全包含 cgroup 挂载点不满足要求（详见 GitHub Issue #2683、#3485、#4568）。

尽可能加强环境安全​配置防火墙、更新内核补丁，避免权限漏洞

。
````
# 环境检查
uname -r
dnf install -y iptables git 


# 下载docker 28的二进制压缩包
 wget https://download.docker.com/linux/static/stable/x86_64/docker-28.3.2.tgz


# 解压
tar zxvf docker-28.3.2.tgz


# 产生一个docker目录，里面有各个二进制文件。
ls docker
containerd  containerd-shim-runc-v2  ctr  docker  dockerd  docker-init  docker-proxy  runc


# 将这些二进制文件全部复制到 /usr/bin目录中，作为linux命令使用
cp ./docker/*  /usr/bin


# 临时启动docker
dockerd


# 验证docker是否可用
docker version


# 将docker注册成系统的service
vim /usr/lib/systemd/system/docker.service


[Unit]
Description=Docker Application Container Engine
Documentation=https://docs.docker.com
After=network-online.target firewalld.service
Wants=network-online.target


[Service]
Type=notify
ExecStart=/usr/bin/dockerd
ExecReload=/bin/kill -s HUP $MAINPID
LimitNOFILE=infinity
LimitNPROC=infinity
TimeoutStartSec=0
Delegate=yes
KillMode=process
Restart=on-failure
StartLimitBurst=3
StartLimitInterval=60s


[Install]
WantedBy=multi-user.target




# 启动docker服务
chmod 644 /usr/lib/systemd/system/docker.service
systemctl daemon-reload
systemctl start docker     # 立即启动服务
systemctl enable docker    # 开机自启


# 验证
systemctl status docker
docker version
docker ps -a

````


# Nvidia container toolkit安装
官网文档地址   https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html 
有外网
Ubuntu24.03安装方法
```
# 下载gpg文件
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

# 编写list文件
vim /etc/apt/sources.list.d/nvidia-container-toolkit.sources
----------------------------------------------------------------
Types: deb
URIs: https://nvidia.github.io/libnvidia-container/stable/deb
Suites: $(ARCH)
Components: -
Signed-By: /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
-------------------------------------------------------------------

```
debian系列安装方法
```
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg   && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list |     sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' |     tee /etc/apt/sources.list.d/nvidia-container-toolkit.list 
apt-get update
apt-get install -y nvidia-container-toolkit
systemctl restart docker

# 自动配置nvidia docker运行时
nvidia-ctk runtime configure --runtime=docker

# 重启docker
systemctl restart docker

# 验证运行时注册
docker info | grep -i runtimes
# 返回 Runtimes: io.containerd.runc.v2 nvidia runc

```
离线安装法：有外网的情况下，红帽系列通过dnf repo下载toolkit
````
# 添加repo
curl -s -L https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo | \
  sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo


# 更新缓存
dnf clean all && dnf makecache


# 安装
export NVIDIA_CONTAINER_TOOLKIT_VERSION=1.17.8-1
sudo dnf install -y \
      nvidia-container-toolkit-${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
      nvidia-container-toolkit-base-${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
      libnvidia-container-tools-${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
      libnvidia-container1-${NVIDIA_CONTAINER_TOOLKIT_VERSION}


# 只下载不安装，可以添加--downloadonly --downloaddir=&lt;目录>
dnf install -y --downloadonly --downloaddir=/opt/resources/toolkit/ \
      nvidia-container-toolkit-${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
      nvidia-container-toolkit-base-${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
      libnvidia-container-tools-${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
      libnvidia-container1-${NVIDIA_CONTAINER_TOOLKIT_VERSION}


# 在线下载内容
libnvidia-container-tools-1.17.8-1.x86_64.rpm
libnvidia-container1-1.17.8-1.x86_64.rpm
nvidia-container-toolkit-1.17.8-1.x86_64.rpm
nvidia-container-toolkit-base-1.17.8-1.x86_64.rpm

````

无外网
````
# 先从外网下载全量包
wget https://github.com/NVIDIA/nvidia-container-toolkit/releases/download/v1.17.8/nvidia-container-toolkit_1.17.8_rpm_x86_64.tar.gz
# 将这个包复制到内网


# 解压
tar zxvf nvidia-container-toolkit_1.17.8_rpm_x86_64.tar.gz


# 安装
cd release-v1.17.8-stable/packages/centos7/x86_64/
dnf install -y libnvidia-container-tools-1.17.8-1.x86_64.rpm   libnvidia-container1-1.17.8-1.x86_64.rpm  nvidia-container-toolkit-1.17.8-1.x86_64.rpm  nvidia-container-toolkit-base-1.17.8-1.x86_64.rpm 

````


# 激活nvidia docker
目前虽然安装了docker和toolkit，但是docker依然无法调用显卡驱动，需要修改runtime为nvidia docker
```bash
# 自动配置runtime为nvidia docker
nvidia-ctk runtime configure --runtime=docker


# 重启docker
systemctl restart docker


# 检验当前runtime是否为nvidia docker
docker info | grep -i runtimes
# 返回 Runtimes: io.containerd.runc.v2 nvidia runc 

````
# 使用cuda容器
如果在宿主机linux系统中安装cuda困难，或者不同项目需要不同版本的cuda。你可以使用cuda容器。
```bash
docker pull nvidia/cuda:12.8.1-cudnn-devel-ubuntu24.04

# 基础容器
docker run --name cu128 -itd --privileged --gpus all -p 11000:11000   nvidia/cuda:12.8.1-cudnn-devel-ubuntu24.04
docker exec -it cu128  bash

# 容器内查看显卡驱动，防止基座异常
nvidia-smi

# apt换源
mv /etc/apt/sources.list.d/cuda.list /etc/apt/sources.list.d/cuda.list.bak
apt update
apt install -y vim
mv /etc/apt/sources.list.d/ubuntu.sources  /etc/apt/sources.list.d/ubuntu.sources.bak
vim /etc/apt/sources.list.d/ubuntu.sources
---------------------------------------------------------
# 清华大学 Ubuntu 24.04 (noble) 镜像源
# 常规软件包更新（使用清华源）
Types: deb
URIs: https://mirrors.tuna.tsinghua.edu.cn/ubuntu
Suites: noble noble-updates noble-backports
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg

# 安全更新（建议保留官方源以确保及时性）
Types: deb
URIs: https://security.ubuntu.com/ubuntu
Suites: noble-security
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg

# 如需源码仓库，可取消以下注释
# Types: deb-src
# URIs: https://mirrors.tuna.tsinghua.edu.cn/ubuntu
# Suites: noble noble-updates noble-backports noble-security
# Components: main restricted universe multiverse
# Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
---------------------------------------------------------------

# 系统包
apt update && apt upgrade -y
apt install -y vim git python3-pip python3-venv curl net-tools wget sudo
apt install -y gcc g++ build-essential cmake ninja-build patchelf
apt install -y libgobject-2.0-0 libpango-1.0-0 libpangoft2-1.0-0 
apt install -y libgl1 libglib2.0-0t64 libsm6 libxext6 libxrender-dev
apt install -y libtbb-dev libssl-dev libcurl4-openssl-dev libaio-dev libgflags-dev zlib1g-dev libfmt-dev libnuma-dev libblis-dev
apt install -y software-properties-common
add-apt-repository -y ppa:ubuntu-toolchain-r/test
apt update
apt install -y --only-upgrade libstdc++6
# 验证libstdc++版本(应包含3.4.32)
strings /usr/lib/x86_64-linux-gnu/libstdc++.so.6 | grep GLIBCXX | tail
apt install -y numactl


# (二选一)安装miniconda
mkdir -p ~/miniconda3
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda3/miniconda.sh
bash ~/miniconda3/miniconda.sh -b -u -p ~/miniconda3
rm ~/miniconda3/miniconda.sh
source ~/miniconda3/bin/activate
conda init --all

# 虚拟环境
mkdir ~/.pip
vim ~/.pip/pip.conf
---------------------------------------
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
--------------------------------------
conda create -n ftllm python=3.12
conda activate ftllm
conda install -y -c conda-forge libstdcxx-ng gcc_impl_linux-64
conda install -y -c nvidia/label/cuda-11.8.0 cuda-runtime  # cuda11.8的动态库

# 安装uv
pip install uv

# 安装cuda 12.8对应版本的pytorch2.8
pip install torch==2.8.0+cu128 torchvision==0.23.0+cu128 torchaudio==2.8.0+cu128 --index-url https://download.pytorch.org/whl/cu128
pip install packaging ninja cpufeature numpy openai
# 验证 torch 版本
python -c "import torch; print(torch.__version__)"
# 验证 torchvision 版本
python -c "import torchvision; print(torchvision.__version__)"

# 继续安装你的项目和环境......
```