# Running Docker on Raspberry Pi 5: Best Practices & Guide

## Overview

Docker runs excellently on Raspberry Pi 5, providing containerized application deployment for home servers, development, and IoT projects. The Pi 5's improved CPU and memory make it a capable Docker host.

**Key Considerations**:
- Use 64-bit Raspberry Pi OS (Bookworm) for best compatibility
- ARM64 architecture requires ARM-compatible images
- NVMe storage dramatically improves container performance
- 8GB RAM model recommended for multiple containers

## Installation

### Method 1: Official Docker Script (Recommended)

The easiest installation method using Docker's convenience script.

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker using official script
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group (avoid sudo for docker commands)
sudo usermod -aG docker $USER

# Log out and back in, then verify
docker --version
docker run hello-world
```

### Method 2: Manual Repository Installation

For 64-bit Raspberry Pi OS, follow Debian instructions.

```bash
# Install prerequisites
sudo apt-get update
sudo apt-get install ca-certificates curl gnupg

# Add Docker's GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add repository
echo \
  "deb [arch=arm64 signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER
```

### What Gets Installed

| Component | Description |
|-----------|-------------|
| Docker Engine | Core container runtime |
| Docker CLI | Command-line interface |
| Containerd | Container lifecycle management |
| Docker Buildx | Multi-platform build support |
| Docker Compose | Multi-container orchestration |

## Post-Installation Setup

### Enable Memory Cgroup (Important!)

By default, Raspberry Pi OS doesn't enable memory cgroup accounting, causing `docker stats` to show zeros.

```bash
# Edit cmdline.txt (Bookworm location)
sudo nano /boot/firmware/cmdline.txt

# Add to END of the single line (don't create new lines):
cgroup_enable=cpuset cgroup_enable=memory cgroup_memory=1

# Reboot
sudo reboot

# Verify
docker info | grep -i cgroup
```

**Note**: For older Pi OS versions, edit `/boot/cmdline.txt` instead.

### Start Docker on Boot

```bash
sudo systemctl enable docker
sudo systemctl start docker
```

### Verify Installation

```bash
# Check Docker info
docker info

# Run test container
docker run --rm hello-world

# Check compose
docker compose version
```

## Docker Compose

Docker Compose is included with modern Docker installations (as `docker compose` plugin).

### Basic Usage

```bash
# Start services
docker compose up -d

# Stop services
docker compose down

# View logs
docker compose logs -f

# Update containers
docker compose pull
docker compose up -d
```

### Example docker-compose.yml

```yaml
version: "3.8"
services:
  portainer:
    image: portainer/portainer-ce:latest
    container_name: portainer
    restart: unless-stopped
    ports:
      - "9443:9443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - portainer_data:/data

  pihole:
    image: pihole/pihole:latest
    container_name: pihole
    restart: unless-stopped
    ports:
      - "53:53/tcp"
      - "53:53/udp"
      - "80:80/tcp"
    environment:
      TZ: 'America/New_York'
      WEBPASSWORD: 'your_password_here'
    volumes:
      - pihole_data:/etc/pihole
      - dnsmasq_data:/etc/dnsmasq.d

volumes:
  portainer_data:
  pihole_data:
  dnsmasq_data:
```

## Portainer (GUI Management)

Portainer provides a web UI for managing Docker containers.

### Installation

```bash
# Create volume
docker volume create portainer_data

# Run Portainer
docker run -d \
  -p 9443:9443 \
  --name portainer \
  --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v portainer_data:/data \
  portainer/portainer-ce:latest
```

Access at `https://<pi-ip>:9443`

## ARM64 Image Compatibility

### The Challenge

Not all Docker images support ARM64. Running x86-only images will fail.

### Finding Compatible Images

1. **Check Docker Hub tags**: Look for `arm64`, `arm64v8`, or `linux/arm64`
2. **Use multi-arch images**: These auto-select the right architecture
3. **LinuxServer.io images**: Excellent ARM64 support
4. **Official images**: Most official images are multi-arch

### Verify Image Architecture

```bash
# Check available platforms
docker manifest inspect <image>:<tag>

# Example
docker manifest inspect nginx:latest | grep architecture
```

### Common ARM64-Compatible Images

| Category | Images |
|----------|--------|
| Web/Proxy | nginx, traefik, caddy, nginx-proxy-manager |
| Databases | postgres, mariadb, redis, mongodb |
| Media | jellyfin, plex (limited), navidrome |
| Home Automation | home-assistant, node-red, mosquitto |
| Monitoring | prometheus, grafana, influxdb |
| Utilities | portainer, watchtower, pihole, adguard |

### Building Multi-Arch Images

```bash
# Create builder
docker buildx create --use --name multiarch

# Build for multiple platforms
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t myimage:latest \
  --push .
```

## Performance Optimization

### Storage: Use NVMe

Moving Docker to NVMe storage dramatically improves performance.

| Storage | Read Speed | Write Speed |
|---------|------------|-------------|
| SD Card | ~90 MB/s | ~30 MB/s |
| NVMe (Gen 2) | ~450 MB/s | ~380 MB/s |
| NVMe (Gen 3) | ~850 MB/s | ~720 MB/s |

### Move Docker Data to NVMe

```bash
# Stop Docker
sudo systemctl stop docker

# Move data directory
sudo mv /var/lib/docker /mnt/nvme/docker

# Create symlink
sudo ln -s /mnt/nvme/docker /var/lib/docker

# Start Docker
sudo systemctl start docker
```

### Or Configure Docker Daemon

```bash
# Create/edit daemon.json
sudo nano /etc/docker/daemon.json
```

```json
{
  "data-root": "/mnt/nvme/docker"
}
```

```bash
sudo systemctl restart docker
```

### Resource Limits

Set memory and CPU limits to prevent container runaway.

```yaml
# In docker-compose.yml
services:
  myapp:
    image: myimage
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 1G
        reservations:
          memory: 512M
```

### Use Lightweight Images

| Base Image | Size | Notes |
|------------|------|-------|
| alpine | ~5 MB | Minimal, uses musl libc |
| debian:slim | ~25 MB | Debian minimal |
| ubuntu | ~75 MB | Full Ubuntu |

### Other Optimization Tips

- **Use Pi OS Lite**: No desktop = more resources for containers
- **Disable swap**: Or limit it for better performance
- **Static IP**: Prevents network issues after reboots
- **Adequate power**: Use official 27W PSU

## Security Best Practices

### Run as Non-Root User

```dockerfile
# In Dockerfile
FROM node:18-alpine
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser
```

### Rootless Docker Mode

Run Docker daemon without root privileges.

```bash
# Install rootless extras
sudo apt-get install docker-ce-rootless-extras uidmap

# Setup rootless mode (as regular user, not root)
dockerd-rootless-setuptool.sh install

# Set environment variables
export DOCKER_HOST=unix://$XDG_RUNTIME_DIR/docker.sock
```

### Other Security Practices

| Practice | Implementation |
|----------|----------------|
| Use official images | Verify with Docker Content Trust |
| Pin image versions | Use specific tags, not `latest` |
| Limit capabilities | Use `--cap-drop=ALL` and add only needed |
| Read-only filesystem | Use `--read-only` flag |
| No privileged mode | Avoid `--privileged` unless necessary |
| Network segmentation | Create isolated Docker networks |
| Scan images | Use `docker scout` or Trivy |

### Don't Expose Docker Socket Publicly

```bash
# Bad: exposes daemon to network
docker run -p 2375:2375 ...

# Better: use TLS or SSH tunneling for remote access
```

## Popular Containers for Home Server

### Media

| Container | Description | ARM64 |
|-----------|-------------|-------|
| Jellyfin | Media server (open source) | ✅ |
| Plex | Media server | ✅ (limited HW transcode) |
| Navidrome | Music streaming | ✅ |
| Sonarr/Radarr | Media automation | ✅ |

### Home Automation

| Container | Description | ARM64 |
|-----------|-------------|-------|
| Home Assistant | Smart home platform | ✅ |
| Node-RED | Flow-based automation | ✅ |
| Mosquitto | MQTT broker | ✅ |
| Zigbee2MQTT | Zigbee bridge | ✅ |

### Network & Security

| Container | Description | ARM64 |
|-----------|-------------|-------|
| Pi-hole | Network ad blocker | ✅ |
| AdGuard Home | Ad blocker alternative | ✅ |
| WireGuard | VPN server | ✅ |
| Nginx Proxy Manager | Reverse proxy | ✅ |

### Utilities

| Container | Description | ARM64 |
|-----------|-------------|-------|
| Portainer | Docker GUI | ✅ |
| Watchtower | Auto-update containers | ✅ |
| Uptime Kuma | Status monitoring | ✅ |
| Nextcloud | Cloud storage | ✅ |

## Podman Alternative

Podman is a daemonless, rootless container engine compatible with Docker.

### Key Differences

| Feature | Docker | Podman |
|---------|--------|--------|
| Architecture | Daemon-based | Daemonless |
| Root required | Yes (default) | No (rootless native) |
| CLI compatibility | Native | Docker-compatible |
| Compose | docker compose | podman-compose |
| Systemd integration | Possible | Native |
| Community/Ecosystem | Larger | Growing |

### When to Use Podman

- **Security priority**: Rootless by design
- **Systemd environments**: Better integration
- **Resource constraints**: No daemon overhead

### When to Use Docker

- **Beginner-friendly**: Larger community, more tutorials
- **Tool ecosystem**: Better IDE integration
- **Compose complexity**: More mature orchestration

### Install Podman

```bash
sudo apt install podman
```

### Migration

Most Docker commands work with Podman:

```bash
# Alias docker to podman
alias docker=podman
```

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `docker stats` shows zeros | Enable cgroups in cmdline.txt |
| Permission denied | Add user to docker group, re-login |
| Image not found | Check ARM64 compatibility |
| Slow performance | Move to NVMe storage |
| Container won't start | Check `docker logs <container>` |
| Network issues | Check firewall, use bridge network |

### Useful Commands

```bash
# View all containers
docker ps -a

# Check container logs
docker logs -f <container>

# Inspect container
docker inspect <container>

# System resource usage
docker system df

# Clean up unused resources
docker system prune -a

# Monitor containers
docker stats
```

### Check System Resources

```bash
# CPU and memory
htop

# Docker-specific
docker stats

# Disk usage
df -h
docker system df
```

## Resources

### Official Documentation
- [Docker on Debian](https://docs.docker.com/engine/install/debian/)
- [Docker on Raspberry Pi OS](https://docs.docker.com/engine/install/raspberry-pi-os/)
- [Docker Rootless Mode](https://docs.docker.com/engine/security/rootless/)
- [Docker Security](https://docs.docker.com/engine/security/)

### Guides & Tutorials
- [Pi My Life Up - Docker](https://pimylifeup.com/raspberry-pi-docker/)
- [Pi My Life Up - Portainer](https://pimylifeup.com/raspberry-pi-portainer/)
- [RaspberryTips - Docker Guide](https://raspberrytips.com/docker-on-raspberry-pi/)

### Container Collections
- [Pi-Hosted](https://github.com/novaspirit/pi-hosted) - Portainer templates
- [LinuxServer.io](https://www.linuxserver.io/) - ARM64 container images
- [Awesome Self-Hosted](https://github.com/awesome-selfhosted/awesome-selfhosted)

### Benchmarks & Performance
- [Pi Benchmarks](https://pibenchmarks.com/)
- [Docker on ARM Research](https://dl.acm.org/doi/10.1145/3603287.3651219)
