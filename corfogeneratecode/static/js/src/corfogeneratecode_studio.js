/*
        .-"-.
       /|6 6|\
      {/(_0_)\}
       _/ ^ \_
      (/ /^\ \)-'
       ""' '""
*/


function CorfoGenerateXBlock(runtime, element) {

    $(element).find('.save-button-corfogeneratecode').bind('click', function(eventObject) {
        eventObject.preventDefault();
        var handlerUrl = runtime.handlerUrl(element, 'studio_submit');

        var data = {
            'display_name': $(element).find('input[name=display_name]').val(),
            'id_content': $(element).find('input[name=id_content]').val(),
            'content': $(element).find('input[name=content]').val()
        };
        
        if ($.isFunction(runtime.notify)) {
            runtime.notify('save', {state: 'start'});
        }
        $.post(handlerUrl, JSON.stringify(data)).done(function(response) {
            if (response.result == 'success' && $.isFunction(runtime.notify)) {
                runtime.notify('save', {state: 'end'});
            }
            else {
                runtime.notify('error',  {
                    title: 'Error: Falló en Guardar',
                    message: 'Revise los campos si estan correctos.'
                });
            }
        });
    });
    
    $(element).find('.cancel-button-corfogeneratecode').bind('click', function(eventObject) {
        eventObject.preventDefault();
        runtime.notify('cancel', {});
    });

}