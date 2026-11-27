% Base de reglas de DepaSeguro AQP (subconjunto de Prolog).
% Los detectores de Python generan hechos como precio_muy_bajo(i7).
% Estas reglas combinan esos hechos para reconocer patrones de estafa.

% --- Patrones de riesgo -----------------------------------------------------
patron(I, adelanto_fantasma) :- pago_previo(I), sin_contrato(I), sin_documentos(I).
patron(I, adelanto_fantasma) :- pago_previo(I), lenguaje_presion(I).

patron(I, ganga_irreal) :- precio_muy_bajo(I), lenguaje_presion(I).
patron(I, ganga_irreal) :- precio_muy_bajo(I), imagen_clonada(I).
patron(I, ganga_irreal) :- precio_muy_bajo(I), sin_documentos(I).

patron(I, inmueble_clonado) :- imagen_clonada(I), \+ documentos_aprobados(I).

patron(I, contacto_reincidente) :- telefono_lista_negra(I).
patron(I, contacto_reincidente) :- telefono_compartido(I), reportes_multiples(I).

patron(I, ubicacion_dudosa) :- direccion_fuera_distrito(I), sin_documentos(I).
patron(I, ubicacion_dudosa) :- direccion_no_encontrada(I), sin_documentos(I).

patron(I, condiciones_abusivas) :- adelanto_excesivo(I), sin_contrato(I).

patron(I, documento_falso) :- documento_rechazado(I).

% --- Clasificación ------------------------------------------------------------
critico(I) :- reporte_confirmado(I).
critico(I) :- patron(I, contacto_reincidente).
critico(I) :- patron(I, P), patron(I, Q), P \= Q.

requiere_revision(I) :- patron(I, _).
requiere_revision(I) :- reportes_multiples(I).

confiable(I) :- documentos_aprobados(I), arrendador_verificado(I), \+ patron(I, _), \+ reporte_abierto(I).

% --- Recomendaciones para el estudiante -----------------------------------------
recomendacion(I, no_transferir) :- critico(I).
recomendacion(I, no_transferir) :- pago_previo(I).
recomendacion(I, visitar_antes) :- requiere_revision(I).
recomendacion(I, visitar_antes) :- sin_documentos(I).
recomendacion(I, exigir_contrato) :- sin_contrato(I).
recomendacion(I, buscar_alternativas) :- critico(I).
recomendacion(I, continuar_con_visita) :- confiable(I).
