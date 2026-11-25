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

## 4. Diagnóstico y Corrección de Cloud-init (Hardening)

Durante la validación técnica del aprovisionamiento automático, se identificaron y subsanaron los siguientes fallos en Cloud-init:

### A. Causa Raíz 1: Error de Sintaxis YAML en `runcmd` (`Failed to shellify`)
- **Problema:** En el manifiesto YAML original, el primer elemento de `runcmd` se encontraba sin comillas exteriores:
  `echo "MiniMarket Cloud-Init completado exitosamente: $(date)" >> ...`
  Al contener dos puntos seguidos de espacio (`: `), el analizador YAML (PyYAML) lo interpretó como un diccionario clave-valor en lugar de una cadena escalar o lista de argumentos.
- **Efecto:** El módulo `cc_runcmd` falló con `TypeError: Failed to shellify [{'echo ...': '...'} ...]`.
- **Solución:** Se envolvieron todos los comandos de `runcmd` entre comillas simples individuales para forzar la interpretación escalar estricta en YAML.

### B. Causa Raíz 2: Condición de Carrera en `write_files` (`Unknown user 'cloud-admin'`)
- **Problema:** El módulo `cc_write_files` se ejecuta en la etapa temprana `init-network`, antes de que el módulo `cc_users_groups` cree los usuarios personalizados definidos en `users:`. Al asignar `owner: cloud-admin:cloud-admin` al script de diagnóstico, la llamada al sistema `pwd.getpwnam('cloud-admin')` fallaba con `OSError: Unknown user or group`.
- **Efecto:** El archivo `/home/cloud-admin/test-connectivity.sh` no se escribía en disco y Cloud-init marcaba estado `error`.
- **Solución:** Se agregó la directiva `defer: true` a dicho archivo, indicando a Cloud-init que difiera su creación hasta la etapa `modules-final` (`cc_write_files_deferred`), garantizando que el usuario `cloud-admin` ya exista y cuente con su directorio `home`.

### C. Causa Raíz 3: Conversión de Permisos Octales por el Analizador de Multipass
- **Problema:** Multipass en macOS parsea el archivo `--cloud-init` antes de inyectarlo en el disco semilla NoCloud (`/dev/vda`). Al procesar `permissions: '0644'` o `'0755'`, los convertía en enteros decimales (`420` y `493`), lo cual disparaba advertencias en la validación estricta de esquema de Ubuntu (`is not of type 'string'`).
- **Solución:** Se omitió el campo `permissions` en `write_files` (asumiendo el valor por defecto estándar `0644`) y se otorgaron los permisos de ejecución explícitamente mediante `chmod 0755` dentro de `runcmd`.

---

## 5. Segmentación y Aislamiento de Red

- **Capa Host (macOS Apple Silicon):** Hypervisor nativo administra las interfaces virtuales de Multipass.
- **Subred Multipass:** Opera en una red NAT aislada (ej. `192.168.64.0/24`), separada de la red Docker del host (`172.17.0.0/16`) y de la red de pods de Minikube (`10.244.0.0/16`).
- **Simulación de Tráfico Externo:** Esta VM permite actuar como cliente externo para ejecutar pruebas de estrés contra el Ingress del cluster cuando se integre con la red local del laboratorio.
