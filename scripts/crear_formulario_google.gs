/**
 * Crea en tu Google Drive el formulario de la encuesta de DepaSeguro AQP y su hoja de respuestas.
 *
 * Uso:
 *   1. Entra a https://script.google.com con tu cuenta de Google y crea un proyecto nuevo.
 *   2. Borra el contenido de Código.gs, pega este archivo completo y guarda.
 *   3. Elige la función crearEncuesta y presiona Ejecutar. Acepta los permisos la primera vez.
 *   4. En Ver > Registros aparecen el enlace para responder, el de edición y el de la hoja.
 */
function crearEncuesta() {
  const form = FormApp.create('Encuesta: vivienda estudiantil y estafas de alquiler en Arequipa');
  form.setDescription(
    'Encuesta anónima del proyecto DepaSeguro AQP, curso Lenguajes de Programación, UTP Arequipa. ' +
    'Toma 2 minutos. No pedimos tu nombre ni datos de contacto; las respuestas solo se usan en resumen para el trabajo académico.');
  form.setCollectEmail(false);
  form.setLimitOneResponsePerUser(false);
  form.setProgressBar(false);
  form.setConfirmationMessage('¡Gracias! Antes de pagar un adelanto, visita el inmueble y pide contrato por escrito.');

  const siNo = ['Sí', 'No'];

  form.addListItem().setTitle('Universidad donde estudias')
      .setChoiceValues(['UTP', 'UNSA', 'UCSM', 'UCSP', 'UAP', 'Otra']).setRequired(true);

  form.addMultipleChoiceItem().setTitle('1. ¿Vienes de otra provincia o región?')
      .setChoiceValues(siNo).setRequired(true);
  form.addMultipleChoiceItem().setTitle('2. ¿Buscaste vivienda en Arequipa en el último año?')
      .setChoiceValues(siNo).setRequired(true);
  form.addMultipleChoiceItem().setTitle('3. ¿Dónde encontraste avisos?')
      .setHelpText('Marca el canal que más usaste.')
      .setChoiceValues(['Redes', 'WhatsApp', 'Carteles', 'Otro']).setRequired(true);
  form.addMultipleChoiceItem().setTitle('4. ¿Te pidieron dinero antes de visitar?')
      .setChoiceValues(siNo).setRequired(true);
  form.addMultipleChoiceItem().setTitle('5. ¿Sufriste o conoces un caso de estafa?')
      .setChoiceValues(siNo).setRequired(true);

  const monto = FormApp.createTextValidation()
      .setHelpText('Escribe solo números, por ejemplo 300. Escribe 0 si no hubo pérdida.')
      .requireNumberGreaterThanOrEqualTo(0).build();
  form.addTextItem().setTitle('6. ¿Cuánto dinero se perdió? (S/)')
      .setHelpText('Escribe 0 si no hubo pérdida.')
      .setValidation(monto).setRequired(true);

  form.addMultipleChoiceItem().setTitle('7. ¿Firmaste contrato?')
      .setChoiceValues(siNo).setRequired(true);
  form.addScaleItem().setTitle('8. ¿Usarías un verificador antes de pagar?')
      .setBounds(1, 5).setLabels('Nada probable', 'Muy probable').setRequired(true);
  form.addParagraphTextItem().setTitle('9. ¿Qué información te daría más confianza?')
      .setRequired(false);

  const hoja = SpreadsheetApp.create('Respuestas - Encuesta DepaSeguro AQP');
  form.setDestination(FormApp.DestinationType.SPREADSHEET, hoja.getId());

  Logger.log('Enlace para responder: ' + form.getPublishedUrl());
  Logger.log('Enlace para editar: ' + form.getEditUrl());
  Logger.log('Hoja de respuestas: ' + hoja.getUrl());
}
