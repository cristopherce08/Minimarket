#!/usr/bin/env bash
# Dimensionamiento fisico y TCO a 3 anios - MiniMarket (on-premise vs nube)
# Uso: ./dimensionamiento_tco.sh      (interactivo)
#      ./dimensionamiento_tco.sh -y   (usa todos los valores por defecto)
export LC_NUMERIC=C
AUTO=0; [ "$1" = "-y" ] && AUTO=1

ask() {  # ask "pregunta" valor_por_defecto
  [ "$AUTO" = 1 ] && { echo "$2"; return; }
  read -r -p "$1 [$2]: " v
  v=${v:-$2}
  [[ $v =~ ^[0-9]+([.][0-9]+)?$ ]] || { echo "  valor invalido, se usa $2" >&2; v=$2; }
  echo "$v"
}
calc() { awk "BEGIN{printf \"%.2f\", $1}"; }

echo "=== Dimensionamiento fisico y TCO a 3 anios - MiniMarket ==="
echo "--- Equipos (supuestos editables) ---"
N_SRV=$(ask "Numero de servidores rack" 3)
W_SRV=$(ask "Consumo promedio por servidor (W)" 350)
N_SW=$(ask "Numero de switches" 2)
W_SW=$(ask "Consumo por switch (W)" 120)
PUE=$(ask "PUE del datacenter (1.4 - 1.6)" 1.5)
echo "--- Costos ---"
TARIFA=$(ask "Tarifa electrica (S/ por kWh)" 0.70)
P_SRV=$(ask "Precio por servidor (S/)" 15000)
P_SW=$(ask "Precio por switch (S/)" 3000)
P_UPS=$(ask "UPS (S/)" 8000)
P_AC=$(ask "Aire acondicionado de precision (S/)" 12000)
P_RACK=$(ask "Rack, cableado e instalacion (S/)" 5000)
MANT=$(ask "Mantenimiento anual (% del CAPEX)" 10)
NUBE=$(ask "Costo mensual del hosting en la nube (S/)" 2500)

IT_W=$(calc "$N_SRV*$W_SRV + $N_SW*$W_SW")
FAC_W=$(calc "$IT_W*$PUE")
BTU=$(calc "$IT_W*3.412")
TON=$(calc "$BTU/12000")
UPS_KVA=$(calc "$IT_W/0.9/1000*1.25")
KWH_ANO=$(calc "$FAC_W/1000*8760")
E3=$(calc "$KWH_ANO*3*$TARIFA")
CAPEX=$(calc "$N_SRV*$P_SRV + $N_SW*$P_SW + $P_UPS + $P_AC + $P_RACK")
M3=$(calc "$CAPEX*$MANT/100*3")
TCO_ON=$(calc "$CAPEX+$E3+$M3")
TCO_NUBE=$(calc "$NUBE*36")
DIF=$(calc "$TCO_ON-$TCO_NUBE")

echo
echo "=============== RESULTADOS ==============="
printf "%-38s %14s\n" "Potencia de equipos (IT)"       "$IT_W W"
printf "%-38s %14s\n" "Potencia total con PUE $PUE"     "$FAC_W W"
printf "%-38s %14s\n" "Carga termica"                   "$BTU BTU/h"
printf "%-38s %14s\n" "Refrigeracion requerida"         "$TON TR"
printf "%-38s %14s\n" "UPS recomendado (margen 25%)"    "$UPS_KVA kVA"
printf "%-38s %14s\n" "Consumo electrico anual"         "$KWH_ANO kWh"
echo "--------------------------------------------"
printf "%-38s %14s\n" "CAPEX inicial (equipos+UPS+AC)"  "S/ $CAPEX"
printf "%-38s %14s\n" "Energia a 3 anios"               "S/ $E3"
printf "%-38s %14s\n" "Mantenimiento a 3 anios"         "S/ $M3"
printf "%-38s %14s\n" "TCO on-premise (3 anios)"        "S/ $TCO_ON"
printf "%-38s %14s\n" "TCO nube (36 meses)"             "S/ $TCO_NUBE"
echo "--------------------------------------------"
if awk "BEGIN{exit !($DIF>0)}"; then
  echo "Conclusion: la NUBE es mas barata en S/ $DIF a 3 anios."
else
  echo "Conclusion: ON-PREMISE es mas barato en S/ $(calc "-1*$DIF") a 3 anios."
fi
