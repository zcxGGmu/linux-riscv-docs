# 1 qemu-host

## 1.0 riscv-gnu-toolchain

```shell
# pre dependencies
sudo apt install autoconf automake autotools-dev curl python3 python3-pip libmpc-dev libmpfr-dev libgmp-dev gawk build-essential bison flex texinfo gperf libtool patchutils bc zlib1g-dev libexpat-dev ninja-build git cmake libglib2.0-dev

# https://github.com/riscv-collab/riscv-gnu-toolchain/releases
# add to ~/.zshrc
export PATH="$PATH:$WS/install/bin"
source ~/.zshrc
riscv64-unknown-linux-gnu-gcc -v
```



## 1.1 qemu build

```shell
export WS=`pwd`

# some dependencies
sudo apt install git gcc g++ wget flex bison bc cpio make pkg-config libglib2.0-dev libfdt-dev libpixman-1-dev zlib1g-dev libncurses-dev libssl-dev ninja-build python3-venv libslirp-dev -y

# qemu build
# wget https://mirrors.aliyun.com/blfs/conglomeration/qemu/qemu-9.0.0.tar.xz
git clone --depth=1 -b ctr_upstream --recurse-submodules -j8 https://github.com/rajnesh-kanwal/qemu.git
cd ./qemu
mkdir build && cd ./build

../configure --enable-kvm --enable-slirp --enable-plugins --enable-virtfs --enable-debug --enable-vnc --enable-werror --enable-vhost-net --target-list="riscv64-softmmu" 

make -j8
cd ../roms/
make opensbi64-generic

qemu-system-riscv64 --version

export QEMU=$WS/qemu/build
```

## 1.2 kernel build

```shell
git clone --depth=1 -b perf-kvm-stat-v3 -j8 https://github.com/zcxGGmu/linux.git
export ARCH=riscv
export CROSS_COMPILE=riscv64-unknown-linux-gnu-
make O=./build defconfig
# make O=./build menuconfig
make O=./build -j8
cd ..

export LINUX=$WS/linux/build/arch/riscv/boot
export KVM=$WS/linux/build/arch/riscv/kvm
```

## 1.3 ubuntu-riscv rootfs

```shell
mkdir rootfs && cd ./rootfs

# build rootfs
# Install pre-reqs
sudo apt install debootstrap qemu qemu-user-static binfmt-support dpkg-cross --no-install-recommends

# Generate minimal bootstrap rootfs
sudo debootstrap --arch=riscv64 --foreign jammy ./temp-rootfs http://ports.ubuntu.com/ubuntu-ports

# chroot to it and finish debootstrap
sudo chroot temp-rootfs /bin/bash

/debootstrap/debootstrap --second-stage

# Add package sources
cat >/etc/apt/sources.list <<EOF
deb http://ports.ubuntu.com/ubuntu-ports jammy main restricted

deb http://ports.ubuntu.com/ubuntu-ports jammy-updates main restricted

deb http://ports.ubuntu.com/ubuntu-ports jammy universe
deb http://ports.ubuntu.com/ubuntu-ports jammy-updates universe

deb http://ports.ubuntu.com/ubuntu-ports jammy multiverse
deb http://ports.ubuntu.com/ubuntu-ports jammy-updates multiverse

deb http://ports.ubuntu.com/ubuntu-ports jammy-backports main restricted universe multiverse

deb http://ports.ubuntu.com/ubuntu-ports jammy-security main restricted
deb http://ports.ubuntu.com/ubuntu-ports jammy-security universe
deb http://ports.ubuntu.com/ubuntu-ports jammy-security multiverse
EOF

# Install essential packages
apt-get update
apt-get install --no-install-recommends -y util-linux haveged openssh-server systemd kmod initramfs-tools conntrack ebtables ethtool iproute2 iptables mount socat ifupdown iputils-ping vim dhcpcd5 neofetch sudo chrony

# Create base config files
mkdir -p /etc/network
cat >>/etc/network/interfaces <<EOF
auto lo
iface lo inet loopback

auto eth0
iface eth0 inet dhcp
EOF

cat >/etc/resolv.conf <<EOF
nameserver 1.1.1.1
nameserver 8.8.8.8
EOF

cat >/etc/fstab <<EOF
LABEL=rootfs	/	ext4	user_xattr,errors=remount-ro	0	1
EOF

echo "Ubuntu-riscv64" > /etc/hostname

# Disable some services on Qemu
ln -s /dev/null /etc/systemd/network/99-default.link
ln -sf /dev/null /etc/systemd/system/serial-getty@hvc0.service

# Set root passwd
echo "root:riscv" | chpasswd

sed -i "s/#PermitRootLogin.*/PermitRootLogin yes/g" /etc/ssh/sshd_config

# Clean APT cache and debootstrap dirs
rm -rf /var/cache/apt/

# Exit chroot
exit
sudo tar -cSf Ubuntu-Jammy-rootfs.tar -C temp-rootfs .
gzip Ubuntu-Jammy-rootfs.tar
rm -rf temp-rootfs
    
# create rootfs.ext4
dd if=/dev/zero of=rootfs.ext4 bs=1G count=100
mkfs.ext4 rootfs.ext4
mkdir ./tmp
sudo mount rootfs.ext4 ./tmp
sudo cp -rp ./temp-rootfs/* ./tmp/
sudo umount ./tmp

# create rootfs_guest.ext4
dd if=/dev/zero of=rootfs_guest.ext4 bs=1G count=10
mkfs.ext4 rootfs_guest.ext4
mkdir ./tmp
sudo mount rootfs_guest.ext4 ./tmp
sudo cp -rp ./temp-rootfs/* ./tmp/
sudo umount ./tmp

export ROOTFS=$WS/rootfs
```

## 1.4 qemu boot host-riscv64

```sh
$QEMU/qemu-system-riscv64 \
    -M virt \
    -cpu rv64 \
    -m 2048 -nographic \
    -smp 8 \
    -kernel $LINUX/Image \
    -append "root=/dev/vda rw console=ttyS0 loglevel=3 earlycon=sbi" \
    -drive file=$ROOTFS/rootfs.ext4,format=raw,id=hd0,cache=writeback \
    -device virtio-blk-pci,drive=hd0 \
    -netdev user,id=usernet,hostfwd=tcp:127.0.0.1:7722-0.0.0.0:22 \
    -device virtio-net-pci,netdev=usernet \
    -rtc clock=host,base=utc
```

# 2 kvm-guest 

## 2.1 prepare kvm env

```shell
# enter host-riscv64
echo $TERM # find x86-host/TERM
echo 'export TERM=xterm-256color' >> ~/.bashrc
source ~/.bashrc

mkdir repo && cd ./repo

# back to x86 host
cd $WS && mkdir apps
cp -f $LINUX/Image ./apps
cp -f $KVM/kvm.ko ./apps
cp -f $ROOTFS/rootfs_guest.ext4 ./apps
scp -P 7722 -r ./apps root@127.0.0.1:/root/repo

insmod ./apps/kvm.ko
```

## 2.2 boot kvm-riscv-guest

### 1)  qemu boot

```shell
export WS=`pwd`

# some dependencies
apt install git gcc g++ wget flex bison bc cpio make pkg-config libglib2.0-dev libfdt-dev libpixman-1-dev zlib1g-dev libncurses-dev libssl-dev ninja-build python3-venv libslirp-dev -y

# qemu build
# wget https://mirrors.aliyun.com/blfs/conglomeration/qemu/qemu-9.0.0.tar.xz
git clone --depth=1 -b ctr_upstream --recurse-submodules -j8 https://github.com/rajnesh-kanwal/qemu.git
cd ./qemu
mkdir build && cd ./build

../configure --enable-kvm --enable-slirp --enable-plugins --enable-virtfs --enable-debug --enable-vnc --enable-werror --enable-vhost-net --target-list="riscv64-softmmu" 

make -j8
cd ../roms/
make opensbi64-generic

qemu-system-riscv64 --version
```

```shell
export QEMU=$WS/qemu/build
export LINUX=$WS/apps
export ROOTFS=$WS/apps

$QEMU/qemu-system-riscv64 \
    -M virt \
    -cpu rv64 --enable-kvm \
    -m 2048 -nographic \
    -smp 8 \
    -kernel $LINUX/Image \
    -append "root=/dev/vda rw console=ttyS0 loglevel=3 earlycon=sbi" \
    -drive file=$ROOTFS/rootfs_guest.ext4,format=raw,id=hd0,cache=writeback \
    -device virtio-blk-pci,drive=hd0 \
    -virtfs local,path=/root/repo/shared,mount_tag=host0,security_model=passthrough,id=host0 \
    -netdev user,id=usernet,hostfwd=tcp:127.0.0.1:7722-0.0.0.0:22 \
    -device virtio-net-pci,netdev=usernet \
    -rtc clock=host,base=utc
    
# x86
## host
mkdir /home/zq/shared
-virtfs local,path=/home/zq/shared,mount_tag=host0,security_model=passthrough,id=host0 \

## guest
mkdir -p /home/zq/shared
mount -t 9p -o trans=virtio,version=9p2000.L host0 /home/zq/shared
```

> 首先，在宿主机上创建一个共享目录，然后使用QEMU的-virtfs选项将其挂载到虚拟机上。
>
> 在宿主机上创建一个共享目录，例如：
>
> ```shell
> mkdir /root/repo/shared
> ```
>
> 将文件放入此共享目录。启动QEMU时，将共享目录挂载为一个虚拟文件系统，例如：
>
> ```sh
> qemu-system-riscv64 ... -virtfs local,path=/root/repo/shared,mount_tag=host0,security_model=passthrough,id=host0
> ```
>
> 其中，`-virtfs` 选项指定了共享文件夹的参数，`local` 表示共享文件夹是本地文件夹，`path` 指定了共享文件夹的路径，`mount_tag` 指定了共享文件夹在虚拟机中的挂载点，`security_model` 指定了安全模型，`id` 是共享文件夹的标识符。
>
> ---
>
> 在虚拟机内部，挂载共享文件夹，例如：
>
> ```sh
> mkdir -p /root/repo/shared
> mount -t 9p -o trans=virtio,version=9p2000.L host0 /root/repo/shared
> 
> cp /proc/kallsyms /root/repo/shared
> cp /proc/modules /root/repo/shared
> ```
>
> 其中，`-t` 选项指定了文件系统类型，`9p` 是QEMU支持的文件系统类型，`trans` 指定了传输协议，`version` 指定了文件系统版本，`host0` 是共享文件夹的标识符，`/root/repo/shared` 是共享文件夹在虚拟机中的挂载点。此时，`/root/repo/shared` 目录将指向宿主机上的 `/root/repo/shared` 目录，可以在两者之间传输文件。
>
> > `tips`：每次重启QEMU虚拟机都要重新挂载，可以把上述 mount 命令做成开机自启。

### 2) kvmtool boot

首先，需要准备好 libfdt 库，将其添加到工具链所在位置的 sysroot 文件夹中：

```shell
git clone git://git.kernel.org/pub/scm/utils/dtc/dtc.git
cd dtc
export ARCH=riscv
export CROSS_COMPILE=riscv64-linux-gnu-
export CC="${CROSS_COMPILE}gcc -mabi=lp64d -march=rv64gc" # riscv toolchain should be configured with --enable-multilib to support the most common -march/-mabi options if you build it from source code
TRIPLET=$($CC -dumpmachine)
SYSROOT=$($CC -print-sysroot)
make libfdt  -j`nproc`
sudo make NO_PYTHON=1 NO_YAML=1 DESTDIR=$SYSROOT PREFIX=/usr LIBDIR=/usr/lib64/lp64d install-lib install-includes  -j`nproc`
cd ..
# install cross-compiled libfdt library at $SYSROOT/usr/lib64/lp64d directory of cross-compile toolchain
```

编译 kvmtools：

```shell
git clone https://git.kernel.org/pub/scm/linux/kernel/git/will/kvmtool.git
cd kvmtool
export ARCH=riscv
export CROSS_COMPILE=riscv64-linux-gnu-
cd kvmtool
make lkvm-static  -j`nproc`
${CROSS_COMPILE}strip lkvm-static
cd ..
```

## 2.3 ssh with qemu-host

```shell
# 在本地用 tmux 开另一个terminal，不太建议，有一些界面乱码问题

# ssh 连接
    -drive file=$ROOTFS/rootfs.ext4,format=raw,id=hd0 \
    -device virtio-blk-pci,drive=hd0  \
    -netdev user,id=usernet,hostfwd=tcp:127.0.0.1:7722-0.0.0.0:22 \
    -device e1000e,netdev=usernet

ssh -p 7722 root@127.0.0.1
scp -P 7722 root@127.0.0.1:/root/repo/linux/tools/perf/perf .
scp -P 7722 -r ./apps root@127.0.0.1:/root/repo
```



