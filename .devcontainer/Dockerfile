FROM mcr.microsoft.com/devcontainers/python:2-3.13-bookworm

RUN \
    rm -f /etc/apt/sources.list.d/*yarn* && \
    apt update && \
    apt install -y iptables iproute2 libturbojpeg0-dev ffmpeg libpcap0.8 curl && \
    update-alternatives --set iptables /usr/sbin/iptables-legacy


RUN \
    apt update && \
    apt install -y iptables iproute2 libturbojpeg0-dev ffmpeg libpcap0.8 curl && \
    update-alternatives --set iptables /usr/sbin/iptables-legacy


RUN \
    case "$(uname -m)" in \
    x86_64) go2rtc_suffix="amd64" ;; \
    aarch64) go2rtc_suffix="arm64" ;; \
    *) echo "Unsupported architecture: $(uname -m)" && exit 1 ;; \
    esac \
    && curl -L https://github.com/AlexxIT/go2rtc/releases/download/v1.9.11/go2rtc_linux_${go2rtc_suffix} --output /bin/go2rtc \
    && chmod +x /bin/go2rtc \
    && go2rtc --version


RUN \
    pipx install poetry 
