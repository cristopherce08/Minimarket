# Guía de Aprovisionamiento con Multipass y Cloud-init (Criterio 1 UTP)

## 1. Propósito Arquitectónico

Para satisfacer el **Criterio 1 de la Rúbrica de Servicios Cloud (UTP)**, se implementó la automatización de aprovisionamiento de una máquina virtual **Ubuntu 24.04 LTS (ARM64)** utilizando **Canonical Multipass** y **Cloud-init**.

> [!IMPORTANT]
> **Aclaración de Arquitectura:**
> La VM Ubuntu aprovisionada con Multipass es un entorno independiente (Nodo Bastion / Jumpbox de simulación externa) que corre sobre el hypervisor nativo de macOS (`Hypervisor.framework`). No es un nodo del clúster Minikube (que opera en contenedores Docker nativos en el host). Esta separación demuestra segmentación entre la infraestructura de red perimetral y la plataforma de orquestación interna.

---

## 2. Manifiesto Cloud-init (`infra/multipass/cloud-init.yaml`)

El aprovisionamiento automatiza sin intervención manual:
1. **Configuración de Hostname y FQDN:** `minimarket-vm.local`.
2. **Paquetes de Diagnóstico de Red:** `curl`, `wget`, `net-tools`, `iputils-ping`, `dnsutils`, `traceroute`, `tcpdump`, `iperf3`, `jq`, `htop`.
3. **Usuario Administrador:** `cloud-admin` con privilegios `sudo NOPASSWD`.
4. **Archivos de Sistema:** Mensaje de bienvenida (`/etc/motd`) y script de diagnóstico de conectividad (`/home/cloud-admin/test-connectivity.sh`).

---

## 3. Scripts de Automatización

### A. Despliegue de la VM (`infra/multipass/setup-vm.sh`)
```bash
bash infra/multipass/setup-vm.sh
```
*Comando ejecutado internamente:*
```bash
multipass launch \
    --name minimarket-vm \
    --cpus 2 \
    --memory 2G \
    --disk 10G \
    --cloud-init infra/multipass/cloud-init.yaml \
    noble
```

### B. Verificación de la VM (`infra/multipass/verify-vm.sh`)
```bash
bash infra/multipass/verify-vm.sh
```
Verifica:
- Salida de `multipass info minimarket-vm` (Estado `Running`, IPv4 asignada en interfaz puenteada).
- Estado de cloud-init (`cloud-init status` -> `done`).
- Salida de `ip -br addr show` e `ip route`.
- Ping y resolución de nombres hacia el exterior.

---

## 4. Segmentación y Aislamiento de Red

- **Capa Host (macOS Apple Silicon):** Hypervisor nativo administra las interfaces virtuales de Multipass.
- **Subred Multipass:** Opera en una red NAT aislada (ej. `192.168.64.0/24`), separada de la red Docker del host (`172.17.0.0/16`) y de la red de pods de Minikube (`10.244.0.0/16`).
- **Simulación de Tráfico Externo:** Esta VM permite actuar como cliente externo para ejecutar pruebas de estrés contra el Ingress del cluster cuando se integre con la red local del laboratorio.
