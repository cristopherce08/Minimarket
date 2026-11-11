# MiniMarket Cloud — Módulo de Datos, Spark y Analítica (Integrante 3)

Este directorio documenta la arquitectura de datos, el procesamiento analítico distribuido con Apache Spark 3.5, el esquema relacional en PostgreSQL 16 y los procedimientos de migración automatizada con Alembic para **MiniMarket Cloud**.

---

## 📚 Índice de Documentación

1. [Arquitectura de Datos y Procesamiento Distribuido](file:///Users/cristopher/Minimarket/docs/datos/arquitectura-spark-postgresql.md)
   - Flujo de datos transaccional a analítico.
   - Modelo relacional y tablas de resultados (`agg_*`).
   - Integración JDBC entre Apache Spark y PostgreSQL 16.
   - Políticas de red Calico para Spark en Kubernetes.

2. [Guía de Migraciones con Alembic](file:///Users/cristopher/Minimarket/docs/datos/guia-migraciones-alembic.md)
   - Migración `001_initial_schema` y `002_agregados_spark`.
   - Procedimiento de ejecución idempotente y seguro.
   - Automatización en Kubernetes mediante Helm Hooks (`post-install`, `post-upgrade`).
   - Verificación y reversibilidad (`downgrade` / `upgrade`).

3. [Guía de Ejecución Spark en Kubernetes y Soporte ARM64](file:///Users/cristopher/Minimarket/docs/datos/guia-spark-k8s-arm64.md)
   - Construcción de imagen Docker multi-arquitectura (`Dockerfile.k8s`).
   - Inclusión del driver JDBC PostgreSQL `postgresql-42.7.3.jar`.
   - Configuración de Driver y 2 Ejecutores reales en Kubernetes.
   - Gestión de Secrets sin credenciales incrustadas.
   - Monitoreo del reparto de particiones y evidencia de ejecución.

4. [Guía de Sustentación para Evaluación (Criterio 3)](file:///Users/cristopher/Minimarket/docs/datos/guia-sustentacion-integrante3.md)
   - Demostración paso a paso frente al docente.
   - Comandos de inspección en vivo.
   - Verificación de la API y el Dashboard Frontend de analítica.
