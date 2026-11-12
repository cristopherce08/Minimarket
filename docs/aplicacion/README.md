# Documentación del Módulo de Aplicación, Escalabilidad y HPA
## Integrante 2 — Servicios Cloud (UTP)

Esta carpeta contiene la documentación técnica, guías operativas, arquitectura de escalabilidad y evidencias del trabajo realizado por el **Integrante 2 (Aplicación y HPA)** para el proyecto **MiniMarket Cloud**.

---

## Contenido de la Documentación

1. **[arquitectura-escalabilidad-hpa.md](arquitectura-escalabilidad-hpa.md):**  
   Detalla el diseño Cloud Native de `ventas-api`, el control de concurrencia y sobreventa con transacciones ACID en PostgreSQL, la configuración del `HorizontalPodAutoscaler` (`autoscaling/v2`) y la resiliencia ante escalado dinámico.

2. **[guia-pruebas-carga-hey.md](guia-pruebas-carga-hey.md):**  
   Manual completo para reproducir las pruebas de estrés con `hey`, explicación de parámetros, monitoreo de métricas con Metrics Server y trazabilidad de autoescalado de 2 a 5 pods.

3. **[guia-sustentacion-integrante2.md](guia-sustentacion-integrante2.md):**  
   Guía de sustentación académica con las preguntas clave de evaluación, comandos en vivo para la demostración en clase y justificación del cumplimiento de la rúbrica (Criterios 2, 3 y 4).
